"""Storage optimization endpoints."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Movie, MediaFile, Issue, IssueType

router = APIRouter()


class StorageOverview(BaseModel):
    """Storage overview statistics."""
    total_size_bytes: int
    movies_size_bytes: int
    tv_size_bytes: int
    oversized_count: int
    oversized_excess_bytes: int
    undersized_count: int
    duplicates_count: int
    duplicates_waste_bytes: int
    total_reclaimable_bytes: int


class OversizedFile(BaseModel):
    """Oversized file item."""
    id: int
    title: str
    year: Optional[int]
    file_path: Optional[str]
    file_size_bytes: int
    expected_max_bytes: int
    excess_bytes: int
    resolution: Optional[str]


class UndersizedFile(BaseModel):
    """Undersized file item."""
    id: int
    title: str
    year: Optional[int]
    file_path: Optional[str]
    file_size_bytes: int
    expected_min_bytes: int
    resolution: Optional[str]


class DuplicateGroup(BaseModel):
    """Group of duplicate files."""
    movie_id: int
    title: str
    year: Optional[int]
    files: List[dict]
    recommended_keep_id: int
    potential_savings_bytes: int


@router.get("/overview", response_model=StorageOverview)
async def get_storage_overview(db: AsyncSession = Depends(get_db)):
    """Get storage overview and potential savings."""
    # Calculate total movie size
    movies_size = await db.scalar(
        select(func.sum(Movie.file_size_bytes))
    ) or 0
    
    # Get oversized issues
    oversized = await db.execute(
        select(Issue).where(
            and_(
                Issue.issue_type == IssueType.OVERSIZED_FILE,
                Issue.is_resolved == False,
            )
        )
    )
    oversized_list = oversized.scalars().all()
    oversized_excess = sum(
        (i.details or {}).get("excess_bytes", 0) for i in oversized_list
    )
    
    # Get undersized count
    undersized_count = await db.scalar(
        select(func.count(Issue.id)).where(
            and_(
                Issue.issue_type == IssueType.UNDERSIZED_FILE,
                Issue.is_resolved == False,
            )
        )
    ) or 0
    
    # Get duplicates
    duplicates = await db.execute(
        select(MediaFile).where(MediaFile.is_duplicate == True)
    )
    duplicate_list = duplicates.scalars().all()
    duplicates_waste = sum(f.file_size_bytes or 0 for f in duplicate_list)
    
    return StorageOverview(
        total_size_bytes=movies_size,
        movies_size_bytes=movies_size,
        tv_size_bytes=0,
        oversized_count=len(oversized_list),
        oversized_excess_bytes=oversized_excess,
        undersized_count=undersized_count,
        duplicates_count=len(duplicate_list),
        duplicates_waste_bytes=duplicates_waste,
        total_reclaimable_bytes=oversized_excess + duplicates_waste,
    )


@router.get("/oversized", response_model=List[OversizedFile])
async def get_oversized_files(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get list of oversized files."""
    issues = await db.execute(
        select(Issue, Movie).join(
            Movie, Issue.movie_id == Movie.id
        ).where(
            and_(
                Issue.issue_type == IssueType.OVERSIZED_FILE,
                Issue.is_resolved == False,
            )
        ).order_by(
            (Movie.file_size_bytes - (Issue.details["expected_max_bytes"].as_integer())).desc()
        ).limit(limit)
    )
    
    result = []
    for issue, movie in issues.all():
        details = issue.details or {}
        result.append(OversizedFile(
            id=issue.id,
            title=movie.title,
            year=movie.year,
            file_path=movie.file_path,
            file_size_bytes=movie.file_size_bytes or 0,
            expected_max_bytes=details.get("expected_max_bytes", 0),
            excess_bytes=details.get("excess_bytes", 0),
            resolution=movie.resolution,
        ))
    
    return result


@router.get("/undersized", response_model=List[UndersizedFile])
async def get_undersized_files(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get list of undersized (potentially poor quality) files."""
    issues = await db.execute(
        select(Issue, Movie).join(
            Movie, Issue.movie_id == Movie.id
        ).where(
            and_(
                Issue.issue_type == IssueType.UNDERSIZED_FILE,
                Issue.is_resolved == False,
            )
        ).limit(limit)
    )
    
    result = []
    for issue, movie in issues.all():
        details = issue.details or {}
        result.append(UndersizedFile(
            id=issue.id,
            title=movie.title,
            year=movie.year,
            file_path=movie.file_path,
            file_size_bytes=movie.file_size_bytes or 0,
            expected_min_bytes=details.get("expected_min_bytes", 0),
            resolution=movie.resolution,
        ))
    
    return result


@router.get("/duplicates")
async def get_duplicates(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Get list of duplicate file groups."""
    # Find movies with multiple files
    from sqlalchemy import func as sqlfunc
    
    duplicates_query = select(
        MediaFile.movie_id,
        sqlfunc.count(MediaFile.id).label("file_count")
    ).where(
        MediaFile.movie_id.isnot(None)
    ).group_by(
        MediaFile.movie_id
    ).having(
        sqlfunc.count(MediaFile.id) > 1
    ).limit(limit)
    
    result = await db.execute(duplicates_query)
    movie_ids = [r[0] for r in result.all()]
    
    groups = []
    for movie_id in movie_ids:
        movie = await db.get(Movie, movie_id)
        if not movie:
            continue
        
        files = await db.execute(
            select(MediaFile).where(MediaFile.movie_id == movie_id)
        )
        file_list = files.scalars().all()
        
        # Find recommended file (highest quality score)
        recommended = max(file_list, key=lambda f: f.quality_score or 0)
        
        # Calculate savings
        total_size = sum(f.file_size_bytes or 0 for f in file_list)
        keep_size = recommended.file_size_bytes or 0
        
        groups.append({
            "movie_id": movie_id,
            "title": movie.title,
            "year": movie.year,
            "files": [
                {
                    "id": f.id,
                    "file_path": f.file_path,
                    "file_size_bytes": f.file_size_bytes,
                    "resolution": f.resolution,
                    "video_codec": f.video_codec,
                    "quality_score": f.quality_score,
                    "is_recommended": f.id == recommended.id,
                }
                for f in file_list
            ],
            "recommended_keep_id": recommended.id,
            "potential_savings_bytes": total_size - keep_size,
        })
    
    return {"groups": groups, "total": len(groups)}


@router.post("/duplicates/{movie_id}/keep/{file_id}")
async def keep_duplicate_version(
    movie_id: int,
    file_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Keep one version and delete others."""
    # Get all files for this movie
    files = await db.execute(
        select(MediaFile).where(MediaFile.movie_id == movie_id)
    )
    file_list = files.scalars().all()
    
    keep_file = None
    delete_files = []
    
    for f in file_list:
        if f.id == file_id:
            keep_file = f
        else:
            delete_files.append(f)
    
    if not keep_file:
        raise HTTPException(status_code=404, detail="File to keep not found")
    
    # Mark others as deleted (actual deletion would be handled separately)
    for f in delete_files:
        f.is_duplicate = True
    
    await db.commit()
    
    return {
        "status": "success",
        "kept": keep_file.file_path,
        "marked_for_deletion": len(delete_files),
    }