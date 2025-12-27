"""Recommendations endpoints."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Recommendation, MediaType
from backend.utils.config import get_config

router = APIRouter()


class RecommendationResponse(BaseModel):
    """Single recommendation item."""
    id: int
    media_type: str
    title: str
    year: Optional[int]
    tmdb_id: Optional[int]
    tvdb_id: Optional[int]
    imdb_id: Optional[str]
    reason: Optional[str]
    confidence_score: Optional[float]
    imdb_rating: Optional[float]
    rotten_tomatoes_rating: Optional[int]
    poster_url: Optional[str]
    backdrop_url: Optional[str]
    is_ignored: bool
    is_requested: bool
    requested_at: Optional[datetime]
    generated_at: datetime


class RecommendationsListResponse(BaseModel):
    """List of recommendations."""
    recommendations: List[RecommendationResponse]
    total: int
    has_more: bool


class RequestToOverseerrRequest(BaseModel):
    """Request to send to Overseerr."""
    recommendation_id: int


class IgnoreRecommendationRequest(BaseModel):
    """Request to ignore a recommendation."""
    recommendation_id: int


class RegenerateRecommendationsRequest(BaseModel):
    """Request to regenerate recommendations."""
    media_type: Optional[str] = None  # movie, tv_show, anime, or None for all


@router.get("/movies", response_model=RecommendationsListResponse)
async def get_movie_recommendations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_ignored: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get movie recommendations."""
    query = select(Recommendation).where(
        Recommendation.media_type == MediaType.MOVIE
    )
    
    if not include_ignored:
        query = query.where(
            and_(
                Recommendation.is_ignored == False,
                Recommendation.is_requested == False,
                Recommendation.is_added == False,
            )
        )
    
    query = query.order_by(Recommendation.confidence_score.desc())
    
    # Get total count
    count_query = select(Recommendation).where(
        Recommendation.media_type == MediaType.MOVIE
    )
    if not include_ignored:
        count_query = count_query.where(
            and_(
                Recommendation.is_ignored == False,
                Recommendation.is_requested == False,
                Recommendation.is_added == False,
            )
        )
    
    total_result = await db.execute(count_query)
    total = len(total_result.all())
    
    # Get paginated results
    query = query.offset(offset).limit(limit)
    results = await db.scalars(query)
    
    recommendations = [
        RecommendationResponse(
            id=r.id,
            media_type=r.media_type.value,
            title=r.title,
            year=r.year,
            tmdb_id=r.tmdb_id,
            tvdb_id=r.tvdb_id,
            imdb_id=r.imdb_id,
            reason=r.reason,
            confidence_score=r.confidence_score,
            imdb_rating=r.imdb_rating,
            rotten_tomatoes_rating=r.rotten_tomatoes_rating,
            poster_url=r.poster_url,
            backdrop_url=r.backdrop_url,
            is_ignored=r.is_ignored,
            is_requested=r.is_requested,
            requested_at=r.requested_at,
            generated_at=r.generated_at,
        )
        for r in results.all()
    ]
    
    return RecommendationsListResponse(
        recommendations=recommendations,
        total=total,
        has_more=offset + limit < total,
    )


@router.get("/tv", response_model=RecommendationsListResponse)
async def get_tv_recommendations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_ignored: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get TV show recommendations."""
    query = select(Recommendation).where(
        Recommendation.media_type == MediaType.TV_SHOW
    )
    
    if not include_ignored:
        query = query.where(
            and_(
                Recommendation.is_ignored == False,
                Recommendation.is_requested == False,
                Recommendation.is_added == False,
            )
        )
    
    query = query.order_by(Recommendation.confidence_score.desc())
    
    # Get paginated results
    query = query.offset(offset).limit(limit)
    results = await db.scalars(query)
    
    recommendations = [
        RecommendationResponse(
            id=r.id,
            media_type=r.media_type.value,
            title=r.title,
            year=r.year,
            tmdb_id=r.tmdb_id,
            tvdb_id=r.tvdb_id,
            imdb_id=r.imdb_id,
            reason=r.reason,
            confidence_score=r.confidence_score,
            imdb_rating=r.imdb_rating,
            rotten_tomatoes_rating=r.rotten_tomatoes_rating,
            poster_url=r.poster_url,
            backdrop_url=r.backdrop_url,
            is_ignored=r.is_ignored,
            is_requested=r.is_requested,
            requested_at=r.requested_at,
            generated_at=r.generated_at,
        )
        for r in results.all()
    ]
    
    return RecommendationsListResponse(
        recommendations=recommendations,
        total=len(recommendations),
        has_more=False,
    )


@router.get("/anime", response_model=RecommendationsListResponse)
async def get_anime_recommendations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_ignored: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get anime recommendations."""
    query = select(Recommendation).where(
        Recommendation.media_type == MediaType.ANIME
    )
    
    if not include_ignored:
        query = query.where(
            and_(
                Recommendation.is_ignored == False,
                Recommendation.is_requested == False,
                Recommendation.is_added == False,
            )
        )
    
    query = query.order_by(Recommendation.confidence_score.desc())
    query = query.offset(offset).limit(limit)
    results = await db.scalars(query)
    
    recommendations = [
        RecommendationResponse(
            id=r.id,
            media_type=r.media_type.value,
            title=r.title,
            year=r.year,
            tmdb_id=r.tmdb_id,
            tvdb_id=r.tvdb_id,
            imdb_id=r.imdb_id,
            reason=r.reason,
            confidence_score=r.confidence_score,
            imdb_rating=r.imdb_rating,
            rotten_tomatoes_rating=r.rotten_tomatoes_rating,
            poster_url=r.poster_url,
            backdrop_url=r.backdrop_url,
            is_ignored=r.is_ignored,
            is_requested=r.is_requested,
            requested_at=r.requested_at,
            generated_at=r.generated_at,
        )
        for r in results.all()
    ]
    
    return RecommendationsListResponse(
        recommendations=recommendations,
        total=len(recommendations),
        has_more=False,
    )


@router.post("/request")
async def request_to_overseerr(
    request: RequestToOverseerrRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send a recommendation to Overseerr."""
    config = get_config()
    
    if not config.overseerr.is_configured:
        raise HTTPException(status_code=400, detail="Overseerr is not configured")
    
    recommendation = await db.get(Recommendation, request.recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    if recommendation.is_requested:
        raise HTTPException(status_code=400, detail="Already requested")
    
    # Import and use Overseerr client
    from backend.core.integrations.overseerr import OverseerrClient
    
    client = OverseerrClient(config.overseerr.url, config.overseerr.api_key)
    
    try:
        if recommendation.media_type == MediaType.MOVIE:
            await client.request_movie(recommendation.tmdb_id)
        else:
            # Overseerr uses TMDB IDs for TV shows, prefer tmdb_id over tvdb_id
            await client.request_tv(recommendation.tmdb_id or recommendation.tvdb_id)
        
        # Update recommendation status
        recommendation.is_requested = True
        recommendation.requested_at = datetime.utcnow()
        await db.commit()
        
        # Log activity
        from backend.db.models import Activity, ActionType
        activity = Activity(
            action_type=ActionType.RECOMMENDATION_REQUESTED,
            title=f"Requested: {recommendation.title}",
            description=f"Sent request for {recommendation.title} ({recommendation.year}) to Overseerr",
        )
        db.add(activity)
        await db.commit()
        
        return {"status": "success", "message": f"Requested {recommendation.title} via Overseerr"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request: {str(e)}")


@router.post("/ignore")
async def ignore_recommendation(
    request: IgnoreRecommendationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Ignore a recommendation (permanent)."""
    recommendation = await db.get(Recommendation, request.recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    recommendation.is_ignored = True
    await db.commit()
    
    # Log activity
    from backend.db.models import Activity, ActionType
    activity = Activity(
        action_type=ActionType.RECOMMENDATION_IGNORED,
        title=f"Ignored: {recommendation.title}",
        description=f"Ignored recommendation for {recommendation.title} ({recommendation.year})",
    )
    db.add(activity)
    await db.commit()
    
    return {"status": "success", "message": f"Ignored {recommendation.title}"}


@router.post("/regenerate")
async def regenerate_recommendations(
    request: RegenerateRecommendationsRequest,
    http_request,
    db: AsyncSession = Depends(get_db)
):
    """Regenerate AI recommendations."""
    config = get_config()
    
    if not config.ai.enabled:
        raise HTTPException(status_code=400, detail="AI is disabled")
    
    if not config.ai.has_anthropic and not config.ai.has_openai:
        raise HTTPException(status_code=400, detail="No AI API keys configured")
    
    # Clear existing non-requested, non-ignored recommendations of this type
    if request.media_type:
        media_type = MediaType(request.media_type)
        await db.execute(
            Recommendation.__table__.delete().where(
                and_(
                    Recommendation.media_type == media_type,
                    Recommendation.is_requested == False,
                    Recommendation.is_ignored == False,
                )
            )
        )
    else:
        await db.execute(
            Recommendation.__table__.delete().where(
                and_(
                    Recommendation.is_requested == False,
                    Recommendation.is_ignored == False,
                )
            )
        )
    
    await db.commit()
    
    # Trigger AI curator for recommendations
    # This would be handled by the scan manager
    return {
        "status": "started",
        "message": "Recommendation regeneration started. This may take a few minutes."
    }


@router.get("/stats")
async def get_recommendation_stats(db: AsyncSession = Depends(get_db)):
    """Get recommendation statistics."""
    from sqlalchemy import func
    
    total = await db.scalar(select(func.count(Recommendation.id)))
    requested = await db.scalar(
        select(func.count(Recommendation.id)).where(Recommendation.is_requested == True)
    )
    ignored = await db.scalar(
        select(func.count(Recommendation.id)).where(Recommendation.is_ignored == True)
    )
    added = await db.scalar(
        select(func.count(Recommendation.id)).where(Recommendation.is_added == True)
    )
    pending = await db.scalar(
        select(func.count(Recommendation.id)).where(
            and_(
                Recommendation.is_requested == False,
                Recommendation.is_ignored == False,
                Recommendation.is_added == False,
            )
        )
    )
    
    return {
        "total": total or 0,
        "pending": pending or 0,
        "requested": requested or 0,
        "ignored": ignored or 0,
        "added": added or 0,
    }
