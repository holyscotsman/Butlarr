"""Movies library management endpoints."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Movie, MediaFile, Activity, ActionType
from backend.utils.config import get_config

router = APIRouter()


class MovieResponse(BaseModel):
    """Movie item for library view."""
    id: int
    plex_rating_key: str
    title: str
    year: Optional[int]
    sort_title: Optional[str]

    # Ratings
    imdb_id: Optional[str]
    tmdb_id: Optional[int]
    imdb_rating: Optional[float]
    rotten_tomatoes_rating: Optional[int]

    # Technical info
    resolution: Optional[str]
    video_codec: Optional[str]
    audio_codec: Optional[str]
    is_hdr: bool
    hdr_type: Optional[str]
    duration_minutes: Optional[int]

    # File info
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    container: Optional[str]

    # Metadata
    genres: Optional[List[str]]
    studio: Optional[str]
    content_rating: Optional[str]

    # Status
    is_bad_movie: bool
    is_ignored: bool
    has_duplicates: bool
    duplicate_count: int

    # Timestamps
    added_at: Optional[datetime]
    last_scanned: Optional[datetime]


class MovieListResponse(BaseModel):
    """List of movies with pagination."""
    movies: List[MovieResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    total_size_bytes: int


class DeleteMovieRequest(BaseModel):
    """Request to delete a movie."""
    movie_id: int
    delete_files: bool = True
    add_exclusion: bool = True


class SyncResponse(BaseModel):
    """Response from sync operation."""
    status: str
    movies_added: int
    movies_updated: int
    movies_removed: int
    last_sync: datetime


@router.get("", response_model=MovieListResponse)
async def get_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    search: Optional[str] = None,
    sort_by: str = Query("title", pattern="^(title|year|rating|size|added|resolution)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    resolution: Optional[str] = None,
    min_rating: Optional[float] = None,
    max_rating: Optional[float] = None,
    has_duplicates: Optional[bool] = None,
    is_hdr: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all movies with pagination and filtering."""

    # Base query
    query = select(Movie)
    count_query = select(func.count(Movie.id))

    # Search filter
    if search:
        search_filter = or_(
            Movie.title.ilike(f"%{search}%"),
            Movie.original_title.ilike(f"%{search}%"),
            Movie.imdb_id.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Resolution filter
    if resolution:
        query = query.where(Movie.resolution == resolution)
        count_query = count_query.where(Movie.resolution == resolution)

    # Rating filter
    if min_rating is not None:
        query = query.where(Movie.imdb_rating >= min_rating)
        count_query = count_query.where(Movie.imdb_rating >= min_rating)
    if max_rating is not None:
        query = query.where(Movie.imdb_rating <= max_rating)
        count_query = count_query.where(Movie.imdb_rating <= max_rating)

    # HDR filter
    if is_hdr is not None:
        query = query.where(Movie.is_hdr == is_hdr)
        count_query = count_query.where(Movie.is_hdr == is_hdr)

    # Sorting
    sort_column = {
        "title": Movie.sort_title if sort_order == "asc" else Movie.title,
        "year": Movie.year,
        "rating": Movie.imdb_rating,
        "size": Movie.file_size_bytes,
        "added": Movie.added_at,
        "resolution": Movie.resolution,
    }.get(sort_by, Movie.sort_title)

    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())

    # Get total count
    total = await db.scalar(count_query) or 0
    total_pages = (total + page_size - 1) // page_size

    # Get total size
    size_query = select(func.coalesce(func.sum(Movie.file_size_bytes), 0))
    if search:
        size_query = size_query.where(search_filter)
    total_size = await db.scalar(size_query) or 0

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    movies = result.scalars().all()

    # Get duplicate counts for all movies in one query
    movie_ids = [m.id for m in movies]
    dup_query = select(
        MediaFile.movie_id,
        func.count(MediaFile.id).label('count')
    ).where(
        MediaFile.movie_id.in_(movie_ids)
    ).group_by(MediaFile.movie_id)

    dup_result = await db.execute(dup_query)
    dup_counts = {row.movie_id: row.count for row in dup_result.all()}

    # Build response
    movie_responses = []
    for movie in movies:
        file_count = dup_counts.get(movie.id, 1)
        has_dups = file_count > 1

        # Filter by duplicates if requested
        if has_duplicates is not None:
            if has_duplicates and not has_dups:
                continue
            if not has_duplicates and has_dups:
                continue

        movie_responses.append(MovieResponse(
            id=movie.id,
            plex_rating_key=movie.plex_rating_key,
            title=movie.title,
            year=movie.year,
            sort_title=movie.sort_title,
            imdb_id=movie.imdb_id,
            tmdb_id=movie.tmdb_id,
            imdb_rating=movie.imdb_rating,
            rotten_tomatoes_rating=movie.rotten_tomatoes_rating,
            resolution=movie.resolution,
            video_codec=movie.video_codec,
            audio_codec=movie.audio_codec,
            is_hdr=movie.is_hdr or False,
            hdr_type=movie.hdr_type,
            duration_minutes=movie.duration_ms // 60000 if movie.duration_ms else None,
            file_path=movie.file_path,
            file_size_bytes=movie.file_size_bytes,
            container=movie.container,
            genres=movie.genres or [],
            studio=movie.studio,
            content_rating=movie.content_rating,
            is_bad_movie=movie.is_bad_movie or False,
            is_ignored=movie.is_ignored or False,
            has_duplicates=has_dups,
            duplicate_count=file_count - 1 if has_dups else 0,
            added_at=movie.added_at,
            last_scanned=movie.last_scanned,
        ))

    return MovieListResponse(
        movies=movie_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        total_size_bytes=total_size,
    )


@router.get("/stats")
async def get_movie_stats(db: AsyncSession = Depends(get_db)):
    """Get movie library statistics."""
    total = await db.scalar(select(func.count(Movie.id))) or 0
    total_size = await db.scalar(
        select(func.coalesce(func.sum(Movie.file_size_bytes), 0))
    ) or 0

    # Resolution breakdown
    res_query = select(
        Movie.resolution,
        func.count(Movie.id).label('count')
    ).group_by(Movie.resolution)
    res_result = await db.execute(res_query)
    resolutions = {row.resolution or "Unknown": row.count for row in res_result.all()}

    # HDR count
    hdr_count = await db.scalar(
        select(func.count(Movie.id)).where(Movie.is_hdr == True)
    ) or 0

    # Duplicates count
    dup_subquery = select(
        MediaFile.movie_id
    ).group_by(MediaFile.movie_id).having(func.count(MediaFile.id) > 1)
    dup_count = await db.scalar(
        select(func.count()).select_from(dup_subquery.subquery())
    ) or 0

    # Average rating
    avg_rating = await db.scalar(
        select(func.avg(Movie.imdb_rating)).where(Movie.imdb_rating.isnot(None))
    )

    return {
        "total_movies": total,
        "total_size_bytes": total_size,
        "resolutions": resolutions,
        "hdr_count": hdr_count,
        "duplicate_movies": dup_count,
        "average_rating": round(avg_rating, 1) if avg_rating else None,
    }


@router.delete("/{movie_id}")
async def delete_movie(
    movie_id: int,
    delete_files: bool = True,
    add_exclusion: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Delete a movie via Radarr."""
    config = get_config()

    movie = await db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if not config.radarr.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Radarr is not configured. Cannot delete movies without Radarr."
        )

    from backend.core.integrations.radarr import RadarrClient

    try:
        client = RadarrClient(config.radarr.url, config.radarr.api_key)

        if movie.tmdb_id:
            await client.delete_movie(
                movie.tmdb_id,
                delete_files=delete_files,
                add_exclusion=add_exclusion
            )

        # Log activity
        activity = Activity(
            action_type=ActionType.MOVIE_DELETED,
            title=f"Deleted: {movie.title}",
            description=f"Deleted {movie.title} ({movie.year}) from library",
            movie_id=movie.id,
        )
        db.add(activity)

        # Remove from our database
        await db.delete(movie)
        await db.commit()

        return {
            "status": "success",
            "message": f"Deleted {movie.title}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@router.post("/sync")
async def sync_movies(db: AsyncSession = Depends(get_db)):
    """Sync movies from Plex to database."""
    config = get_config()

    if not config.plex.is_configured:
        raise HTTPException(status_code=400, detail="Plex is not configured")

    from backend.core.integrations.plex import PlexClient

    try:
        client = PlexClient(config.plex.url, config.plex.token)
        plex_movies = await client.get_all_movies()

        added = 0
        updated = 0

        # Get existing movies by plex_rating_key
        existing_keys = set()
        result = await db.execute(select(Movie.plex_rating_key))
        for row in result.scalars().all():
            existing_keys.add(row)

        for pm in plex_movies:
            rating_key = str(pm.get("ratingKey"))

            if rating_key in existing_keys:
                # Update existing
                movie = await db.scalar(
                    select(Movie).where(Movie.plex_rating_key == rating_key)
                )
                if movie:
                    movie.title = pm.get("title", movie.title)
                    movie.year = pm.get("year")
                    movie.summary = pm.get("summary")
                    movie.duration_ms = pm.get("duration")
                    movie.last_scanned = datetime.utcnow()
                    updated += 1
            else:
                # Add new
                movie = Movie(
                    plex_rating_key=rating_key,
                    title=pm.get("title", "Unknown"),
                    year=pm.get("year"),
                    summary=pm.get("summary"),
                    duration_ms=pm.get("duration"),
                    added_at=datetime.utcnow(),
                    last_scanned=datetime.utcnow(),
                )
                db.add(movie)
                added += 1

        await db.commit()

        return SyncResponse(
            status="success",
            movies_added=added,
            movies_updated=updated,
            movies_removed=0,
            last_sync=datetime.utcnow(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/{movie_id}")
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    """Get single movie details."""
    movie = await db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Get all files for this movie
    files_result = await db.execute(
        select(MediaFile).where(MediaFile.movie_id == movie_id)
    )
    files = files_result.scalars().all()

    return {
        "id": movie.id,
        "plex_rating_key": movie.plex_rating_key,
        "title": movie.title,
        "year": movie.year,
        "summary": movie.summary,
        "imdb_id": movie.imdb_id,
        "tmdb_id": movie.tmdb_id,
        "imdb_rating": movie.imdb_rating,
        "rotten_tomatoes_rating": movie.rotten_tomatoes_rating,
        "resolution": movie.resolution,
        "video_codec": movie.video_codec,
        "audio_codec": movie.audio_codec,
        "is_hdr": movie.is_hdr,
        "hdr_type": movie.hdr_type,
        "duration_minutes": movie.duration_ms // 60000 if movie.duration_ms else None,
        "file_path": movie.file_path,
        "file_size_bytes": movie.file_size_bytes,
        "genres": movie.genres or [],
        "studio": movie.studio,
        "content_rating": movie.content_rating,
        "tagline": movie.tagline,
        "files": [
            {
                "id": f.id,
                "file_path": f.file_path,
                "file_size_bytes": f.file_size_bytes,
                "resolution": f.resolution,
                "video_codec": f.video_codec,
                "is_primary": f.is_primary,
                "quality_score": f.quality_score,
            }
            for f in files
        ],
        "added_at": movie.added_at,
        "last_scanned": movie.last_scanned,
    }
