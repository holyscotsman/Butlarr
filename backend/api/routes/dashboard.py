"""Dashboard endpoints."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import (
    Movie, TVShow, TVEpisode, Issue, Scan, Activity,
    ScanStatus, IssueType, IssueSeverity, AIUsage
)
from backend.utils.config import get_config

router = APIRouter()


class LibraryStats(BaseModel):
    """Library statistics."""
    total_movies: int
    total_tv_shows: int
    total_episodes: int
    total_collections: int
    bad_movies_count: int
    issues_count: int
    duplicates_count: int


class StorageStats(BaseModel):
    """Storage statistics."""
    total_size_bytes: int
    movies_size_bytes: int
    tv_size_bytes: int
    potential_savings_bytes: int


class AIStats(BaseModel):
    """AI usage statistics."""
    enabled: bool
    monthly_usage_usd: float
    monthly_budget_usd: float
    tokens_used_this_month: int


class RecentActivity(BaseModel):
    """Recent activity item."""
    id: int
    action_type: str
    title: str
    description: Optional[str]
    created_at: datetime


class ScanInfo(BaseModel):
    """Current/last scan information."""
    is_running: bool
    status: Optional[str]
    current_phase: Optional[int]
    total_phases: int
    phase_name: Optional[str]
    progress_percent: float
    current_item: Optional[str]
    elapsed_seconds: Optional[int]
    estimated_remaining_seconds: Optional[int]
    last_completed_at: Optional[datetime]


class ServiceStatus(BaseModel):
    """Service connection status."""
    name: str
    connected: bool
    last_checked: Optional[datetime]


class DashboardResponse(BaseModel):
    """Complete dashboard data."""
    library: LibraryStats
    storage: StorageStats
    ai: AIStats
    scan: ScanInfo
    services: List[ServiceStatus]
    recent_activity: List[RecentActivity]
    issues_by_type: Dict[str, int]
    issues_by_severity: Dict[str, int]


@router.get("", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Get complete dashboard data."""
    config = get_config()
    
    # Library stats
    movie_count = await db.scalar(select(func.count(Movie.id)))
    tv_show_count = await db.scalar(select(func.count(TVShow.id)))
    episode_count = await db.scalar(select(func.count(TVEpisode.id)))
    bad_movies = await db.scalar(
        select(func.count(Movie.id)).where(Movie.is_bad_movie == True)
    )
    
    # Issues count
    open_issues = await db.scalar(
        select(func.count(Issue.id)).where(Issue.is_resolved == False)
    )
    
    # Duplicates count (simplified - movies with is_duplicate files)
    duplicates = 0  # Will be calculated during scan
    
    library_stats = LibraryStats(
        total_movies=movie_count or 0,
        total_tv_shows=tv_show_count or 0,
        total_episodes=episode_count or 0,
        total_collections=0,  # Will be populated from scan
        bad_movies_count=bad_movies or 0,
        issues_count=open_issues or 0,
        duplicates_count=duplicates,
    )
    
    # Storage stats
    movies_size = await db.scalar(
        select(func.sum(Movie.file_size_bytes))
    ) or 0
    
    storage_stats = StorageStats(
        total_size_bytes=movies_size,
        movies_size_bytes=movies_size,
        tv_size_bytes=0,  # Will be calculated
        potential_savings_bytes=0,  # Will be calculated
    )
    
    # AI stats
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_cost = await db.scalar(
        select(func.sum(AIUsage.cost_usd)).where(AIUsage.created_at >= start_of_month)
    ) or 0.0
    monthly_tokens = await db.scalar(
        select(func.sum(AIUsage.total_tokens)).where(AIUsage.created_at >= start_of_month)
    ) or 0
    
    ai_stats = AIStats(
        enabled=config.ai.enabled,
        monthly_usage_usd=monthly_cost,
        monthly_budget_usd=config.ai.monthly_budget_limit,
        tokens_used_this_month=monthly_tokens,
    )
    
    # Scan info
    latest_scan = await db.scalar(
        select(Scan).order_by(Scan.created_at.desc()).limit(1)
    )
    
    scan_info = ScanInfo(
        is_running=latest_scan.status == ScanStatus.RUNNING if latest_scan else False,
        status=latest_scan.status.value if latest_scan else None,
        current_phase=latest_scan.current_phase if latest_scan else None,
        total_phases=17,
        phase_name=latest_scan.phase_name if latest_scan else None,
        progress_percent=latest_scan.progress_percent if latest_scan else 0.0,
        current_item=latest_scan.current_item if latest_scan else None,
        elapsed_seconds=latest_scan.elapsed_seconds if latest_scan else None,
        estimated_remaining_seconds=latest_scan.estimated_remaining_seconds if latest_scan else None,
        last_completed_at=latest_scan.completed_at if latest_scan and latest_scan.status == ScanStatus.COMPLETED else None,
    )
    
    # Service status
    services = [
        ServiceStatus(name="Plex", connected=config.plex.is_configured, last_checked=None),
        ServiceStatus(name="Radarr", connected=config.radarr.is_configured, last_checked=None),
        ServiceStatus(name="Sonarr", connected=config.sonarr.is_configured, last_checked=None),
        ServiceStatus(name="Overseerr", connected=config.overseerr.is_configured, last_checked=None),
        ServiceStatus(name="Tautulli", connected=config.tautulli.is_configured, last_checked=None),
        ServiceStatus(name="FileBot", connected=config.filebot.is_configured, last_checked=None),
    ]
    
    # Recent activity
    recent = await db.scalars(
        select(Activity).order_by(Activity.created_at.desc()).limit(10)
    )
    recent_activity = [
        RecentActivity(
            id=a.id,
            action_type=a.action_type.value,
            title=a.title,
            description=a.description,
            created_at=a.created_at,
        )
        for a in recent.all()
    ]
    
    # Issues breakdown
    issues_by_type_result = await db.execute(
        select(Issue.issue_type, func.count(Issue.id))
        .where(Issue.is_resolved == False)
        .group_by(Issue.issue_type)
    )
    issues_by_type = {row[0].value: row[1] for row in issues_by_type_result.all()}
    
    issues_by_severity_result = await db.execute(
        select(Issue.severity, func.count(Issue.id))
        .where(Issue.is_resolved == False)
        .group_by(Issue.severity)
    )
    issues_by_severity = {row[0].value: row[1] for row in issues_by_severity_result.all()}
    
    return DashboardResponse(
        library=library_stats,
        storage=storage_stats,
        ai=ai_stats,
        scan=scan_info,
        services=services,
        recent_activity=recent_activity,
        issues_by_type=issues_by_type,
        issues_by_severity=issues_by_severity,
    )


@router.get("/quick-stats")
async def get_quick_stats(db: AsyncSession = Depends(get_db)):
    """Get quick stats for dashboard header."""
    movie_count = await db.scalar(select(func.count(Movie.id)))
    tv_show_count = await db.scalar(select(func.count(TVShow.id)))
    issues_count = await db.scalar(
        select(func.count(Issue.id)).where(Issue.is_resolved == False)
    )
    
    return {
        "movies": movie_count or 0,
        "tv_shows": tv_show_count or 0,
        "open_issues": issues_count or 0,
    }
