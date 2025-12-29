"""Bad movies management endpoints."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Movie, BadMovieSuggestion, Activity, ActionType
from backend.utils.config import get_config

router = APIRouter()


class BadMovieResponse(BaseModel):
    """Single bad movie item."""
    id: int
    movie_id: int
    plex_rating_key: str
    title: str
    year: Optional[int]
    bad_score: float
    imdb_rating: Optional[float]
    rotten_tomatoes_rating: Optional[int]
    reason: Optional[str]
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    poster_url: Optional[str]
    is_ignored: bool
    suggested_at: datetime


class BadMoviesListResponse(BaseModel):
    """List of bad movies."""
    movies: List[BadMovieResponse]
    total: int
    total_size_bytes: int
    has_more: bool


class DeleteMovieRequest(BaseModel):
    """Request to delete a movie."""
    suggestion_id: int
    confirm: bool = False


class IgnoreMovieRequest(BaseModel):
    """Request to ignore a movie from suggestions."""
    suggestion_id: int


class BulkDeleteRequest(BaseModel):
    """Request to delete multiple movies."""
    suggestion_ids: List[int]
    confirm: bool = False


@router.get("", response_model=BadMoviesListResponse)
async def get_bad_movies(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("score", pattern="^(score|rating|size|title)$"),
    include_ignored: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get list of bad movies sorted by worst first."""
    query = select(BadMovieSuggestion, Movie).join(
        Movie, BadMovieSuggestion.movie_id == Movie.id
    )
    
    if not include_ignored:
        query = query.where(
            and_(
                BadMovieSuggestion.is_ignored == False,
                BadMovieSuggestion.is_deleted == False,
            )
        )
    
    # Sort order
    if sort_by == "score":
        query = query.order_by(BadMovieSuggestion.bad_score.desc())
    elif sort_by == "rating":
        query = query.order_by(Movie.imdb_rating.asc().nullsfirst())
    elif sort_by == "size":
        query = query.order_by(Movie.file_size_bytes.desc().nullsfirst())
    else:
        query = query.order_by(Movie.title.asc())
    
    # Get total count using SQL COUNT() - much more efficient than fetching all rows
    count_query = select(func.count(BadMovieSuggestion.id)).where(
        and_(
            BadMovieSuggestion.is_ignored == False,
            BadMovieSuggestion.is_deleted == False,
        )
    )
    total = await db.scalar(count_query) or 0

    # Calculate total size using SQL SUM() - single query instead of fetching all rows
    size_query = select(func.coalesce(func.sum(Movie.file_size_bytes), 0)).join(
        BadMovieSuggestion, BadMovieSuggestion.movie_id == Movie.id
    ).where(
        and_(
            BadMovieSuggestion.is_ignored == False,
            BadMovieSuggestion.is_deleted == False,
        )
    )
    total_size = await db.scalar(size_query) or 0
    
    # Get paginated results
    query = query.offset(offset).limit(limit)
    results = await db.execute(query)
    
    movies = []
    for suggestion, movie in results.all():
        movies.append(BadMovieResponse(
            id=suggestion.id,
            movie_id=movie.id,
            plex_rating_key=movie.plex_rating_key,
            title=movie.title,
            year=movie.year,
            bad_score=suggestion.bad_score,
            imdb_rating=movie.imdb_rating,
            rotten_tomatoes_rating=movie.rotten_tomatoes_rating,
            reason=suggestion.reason,
            file_path=movie.file_path,
            file_size_bytes=movie.file_size_bytes,
            poster_url=None,  # Would come from TMDB
            is_ignored=suggestion.is_ignored,
            suggested_at=suggestion.suggested_at,
        ))
    
    return BadMoviesListResponse(
        movies=movies,
        total=total,
        total_size_bytes=total_size,
        has_more=offset + limit < total,
    )


@router.post("/delete")
async def delete_movie(
    request: DeleteMovieRequest,
    db: AsyncSession = Depends(get_db)
):
    """Delete a movie via Radarr and remove from Plex."""
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Please confirm deletion by setting confirm=true"
        )
    
    config = get_config()
    
    # Get suggestion and movie
    suggestion = await db.get(BadMovieSuggestion, request.suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    movie = await db.get(Movie, suggestion.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    # Check if Radarr is configured
    if not config.radarr.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Radarr is not configured. Cannot delete movies without Radarr."
        )
    
    # Delete via Radarr
    from backend.core.integrations.radarr import RadarrClient
    
    try:
        client = RadarrClient(config.radarr.url, config.radarr.api_key)
        
        # Find movie in Radarr by TMDB ID
        if movie.tmdb_id:
            await client.delete_movie(movie.tmdb_id, delete_files=True, add_exclusion=True)
        
        # Mark as deleted
        suggestion.is_deleted = True
        suggestion.deleted_at = datetime.utcnow()
        
        # Log activity
        activity = Activity(
            action_type=ActionType.MOVIE_DELETED,
            title=f"Deleted: {movie.title}",
            description=f"Deleted {movie.title} ({movie.year}) - Score: {suggestion.bad_score:.1f}",
            movie_id=movie.id,
        )
        db.add(activity)
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Deleted {movie.title} and added to exclusion list"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@router.post("/ignore")
async def ignore_movie(
    request: IgnoreMovieRequest,
    db: AsyncSession = Depends(get_db)
):
    """Ignore a movie from bad movie suggestions (permanent)."""
    suggestion = await db.get(BadMovieSuggestion, request.suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    movie = await db.get(Movie, suggestion.movie_id)
    
    suggestion.is_ignored = True
    
    # Also mark the movie as ignored
    if movie:
        movie.is_ignored = True
    
    # Log activity
    activity = Activity(
        action_type=ActionType.MOVIE_IGNORED,
        title=f"Ignored: {movie.title if movie else 'Unknown'}",
        description=f"Ignored {movie.title if movie else 'Unknown'} from bad movie suggestions",
        movie_id=movie.id if movie else None,
    )
    db.add(activity)
    
    await db.commit()
    
    return {
        "status": "success",
        "message": f"Ignored {movie.title if movie else 'movie'} - will not appear in future suggestions"
    }


@router.post("/bulk-delete")
async def bulk_delete_movies(
    request: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Delete multiple movies at once."""
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Please confirm deletion by setting confirm=true"
        )
    
    config = get_config()
    
    if not config.radarr.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Radarr is not configured. Cannot delete movies without Radarr."
        )
    
    from backend.core.integrations.radarr import RadarrClient
    client = RadarrClient(config.radarr.url, config.radarr.api_key)
    
    deleted = []
    failed = []
    
    for suggestion_id in request.suggestion_ids:
        try:
            suggestion = await db.get(BadMovieSuggestion, suggestion_id)
            if not suggestion:
                failed.append({"id": suggestion_id, "error": "Not found"})
                continue
            
            movie = await db.get(Movie, suggestion.movie_id)
            if not movie:
                failed.append({"id": suggestion_id, "error": "Movie not found"})
                continue
            
            if movie.tmdb_id:
                await client.delete_movie(movie.tmdb_id, delete_files=True, add_exclusion=True)
            
            suggestion.is_deleted = True
            suggestion.deleted_at = datetime.utcnow()
            deleted.append(movie.title)
            
        except Exception as e:
            failed.append({"id": suggestion_id, "error": str(e)})
    
    # Log activity
    if deleted:
        activity = Activity(
            action_type=ActionType.MOVIE_DELETED,
            title=f"Bulk deleted {len(deleted)} movies",
            description=f"Deleted: {', '.join(deleted[:5])}{'...' if len(deleted) > 5 else ''}",
        )
        db.add(activity)
    
    await db.commit()
    
    return {
        "status": "success",
        "deleted": deleted,
        "failed": failed,
        "message": f"Deleted {len(deleted)} movies, {len(failed)} failed"
    }


@router.get("/stats")
async def get_bad_movie_stats(db: AsyncSession = Depends(get_db)):
    """Get bad movie statistics."""
    # Use SQL aggregations for all stats in minimal queries
    total = await db.scalar(
        select(func.count(BadMovieSuggestion.id)).where(
            BadMovieSuggestion.is_deleted == False
        )
    ) or 0

    pending = await db.scalar(
        select(func.count(BadMovieSuggestion.id)).where(
            and_(
                BadMovieSuggestion.is_ignored == False,
                BadMovieSuggestion.is_deleted == False,
            )
        )
    ) or 0

    ignored = await db.scalar(
        select(func.count(BadMovieSuggestion.id)).where(
            BadMovieSuggestion.is_ignored == True
        )
    ) or 0

    deleted = await db.scalar(
        select(func.count(BadMovieSuggestion.id)).where(
            BadMovieSuggestion.is_deleted == True
        )
    ) or 0

    # Calculate potential space savings using SQL SUM() instead of Python sum
    potential_savings = await db.scalar(
        select(func.coalesce(func.sum(Movie.file_size_bytes), 0)).join(
            BadMovieSuggestion, BadMovieSuggestion.movie_id == Movie.id
        ).where(
            and_(
                BadMovieSuggestion.is_ignored == False,
                BadMovieSuggestion.is_deleted == False,
            )
        )
    ) or 0

    return {
        "total": total,
        "pending": pending,
        "ignored": ignored,
        "deleted": deleted,
        "potential_savings_bytes": potential_savings,
    }
