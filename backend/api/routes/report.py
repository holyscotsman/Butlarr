"""Server report generation endpoints."""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import (
    Movie, TVShow, TVEpisode, Issue, Scan, Activity,
    ScanStatus, IssueType, IssueSeverity, AIUsage,
    Recommendation, BadMovieSuggestion, MediaType
)
from backend.utils.config import get_config
from backend.utils.version import VERSION

router = APIRouter()


class LibraryReport(BaseModel):
    """Comprehensive library report."""
    generated_at: datetime
    server_version: str
    
    # Library counts
    total_movies: int
    total_tv_shows: int
    total_episodes: int
    
    # Quality breakdown
    movies_4k_hdr: int
    movies_4k_sdr: int
    movies_1080p: int
    movies_720p_or_lower: int
    
    # Storage
    total_size_gb: float
    movies_size_gb: float
    tv_size_gb: float
    
    # Issues summary
    total_issues: int
    critical_issues: int
    warning_issues: int
    info_issues: int
    issues_by_type: Dict[str, int]
    
    # AI analysis
    bad_movies_found: int
    recommendations_pending: int
    ai_cost_this_month: float
    
    # Scan history
    last_scan_date: Optional[datetime]
    last_scan_status: Optional[str]
    scans_this_month: int
    
    # Services
    services_configured: Dict[str, bool]


@router.get("/full", response_model=LibraryReport)
async def generate_full_report(db: AsyncSession = Depends(get_db)):
    """Generate comprehensive library report."""
    config = get_config()
    
    # Movie counts
    total_movies = await db.scalar(select(func.count(Movie.id))) or 0
    total_tv_shows = await db.scalar(select(func.count(TVShow.id))) or 0
    total_episodes = await db.scalar(select(func.count(TVEpisode.id))) or 0
    
    # Quality breakdown
    movies_4k_hdr = await db.scalar(
        select(func.count(Movie.id)).where(
            Movie.resolution == "4k", Movie.is_hdr == True
        )
    ) or 0
    movies_4k_sdr = await db.scalar(
        select(func.count(Movie.id)).where(
            Movie.resolution == "4k", Movie.is_hdr == False
        )
    ) or 0
    movies_1080p = await db.scalar(
        select(func.count(Movie.id)).where(Movie.resolution == "1080")
    ) or 0
    movies_720p_or_lower = await db.scalar(
        select(func.count(Movie.id)).where(
            Movie.resolution.in_(["720", "480", "sd"])
        )
    ) or 0
    
    # Storage
    movies_size = await db.scalar(
        select(func.sum(Movie.file_size_bytes))
    ) or 0
    movies_size_gb = movies_size / (1024**3)
    
    # Issues
    total_issues = await db.scalar(
        select(func.count(Issue.id)).where(Issue.is_resolved == False)
    ) or 0
    critical_issues = await db.scalar(
        select(func.count(Issue.id)).where(
            Issue.is_resolved == False,
            Issue.severity == IssueSeverity.CRITICAL
        )
    ) or 0
    warning_issues = await db.scalar(
        select(func.count(Issue.id)).where(
            Issue.is_resolved == False,
            Issue.severity == IssueSeverity.WARNING
        )
    ) or 0
    info_issues = await db.scalar(
        select(func.count(Issue.id)).where(
            Issue.is_resolved == False,
            Issue.severity == IssueSeverity.INFO
        )
    ) or 0
    
    # Issues by type
    issues_type_result = await db.execute(
        select(Issue.issue_type, func.count(Issue.id))
        .where(Issue.is_resolved == False)
        .group_by(Issue.issue_type)
    )
    issues_by_type = {row[0].value: row[1] for row in issues_type_result.all()}
    
    # AI stats
    bad_movies = await db.scalar(
        select(func.count(BadMovieSuggestion.id)).where(
            BadMovieSuggestion.is_ignored == False,
            BadMovieSuggestion.is_deleted == False
        )
    ) or 0
    
    recs_pending = await db.scalar(
        select(func.count(Recommendation.id)).where(
            Recommendation.is_ignored == False,
            Recommendation.is_requested == False,
            Recommendation.is_added == False
        )
    ) or 0
    
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ai_cost = await db.scalar(
        select(func.sum(AIUsage.cost_usd)).where(AIUsage.created_at >= start_of_month)
    ) or 0.0
    
    # Scan history
    last_scan = await db.scalar(
        select(Scan).order_by(Scan.created_at.desc()).limit(1)
    )
    scans_month = await db.scalar(
        select(func.count(Scan.id)).where(Scan.created_at >= start_of_month)
    ) or 0
    
    return LibraryReport(
        generated_at=datetime.utcnow(),
        server_version=VERSION,
        
        total_movies=total_movies,
        total_tv_shows=total_tv_shows,
        total_episodes=total_episodes,
        
        movies_4k_hdr=movies_4k_hdr,
        movies_4k_sdr=movies_4k_sdr,
        movies_1080p=movies_1080p,
        movies_720p_or_lower=movies_720p_or_lower,
        
        total_size_gb=round(movies_size_gb, 2),
        movies_size_gb=round(movies_size_gb, 2),
        tv_size_gb=0.0,  # Would need TV file tracking
        
        total_issues=total_issues,
        critical_issues=critical_issues,
        warning_issues=warning_issues,
        info_issues=info_issues,
        issues_by_type=issues_by_type,
        
        bad_movies_found=bad_movies,
        recommendations_pending=recs_pending,
        ai_cost_this_month=round(ai_cost, 4),
        
        last_scan_date=last_scan.completed_at if last_scan else None,
        last_scan_status=last_scan.status.value if last_scan else None,
        scans_this_month=scans_month,
        
        services_configured={
            "plex": config.plex.is_configured,
            "radarr": config.radarr.is_configured,
            "sonarr": config.sonarr.is_configured,
            "overseerr": config.overseerr.is_configured,
            "tautulli": config.tautulli.is_configured,
            "filebot": config.filebot.is_configured,
            "anthropic": config.ai.has_anthropic,
            "openai": config.ai.has_openai,
        },
    )


@router.get("/text")
async def generate_text_report(db: AsyncSession = Depends(get_db)):
    """Generate a human-readable text report."""
    report = await generate_full_report(db)
    
    lines = [
        "=" * 60,
        "BUTLARR LIBRARY REPORT",
        f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "=" * 60,
        "",
        "📚 LIBRARY OVERVIEW",
        "-" * 40,
        f"  Movies:      {report.total_movies:,}",
        f"  TV Shows:    {report.total_tv_shows:,}",
        f"  Episodes:    {report.total_episodes:,}",
        "",
        "🎬 MOVIE QUALITY BREAKDOWN",
        "-" * 40,
        f"  4K HDR:      {report.movies_4k_hdr:,}",
        f"  4K SDR:      {report.movies_4k_sdr:,}",
        f"  1080p:       {report.movies_1080p:,}",
        f"  720p/Lower:  {report.movies_720p_or_lower:,}",
        "",
        "💾 STORAGE",
        "-" * 40,
        f"  Total Size:  {report.total_size_gb:,.2f} GB",
        f"  Movies:      {report.movies_size_gb:,.2f} GB",
        "",
        "⚠️ ISSUES SUMMARY",
        "-" * 40,
        f"  Total Open:  {report.total_issues}",
        f"  Critical:    {report.critical_issues}",
        f"  Warnings:    {report.warning_issues}",
        f"  Info:        {report.info_issues}",
        "",
    ]
    
    if report.issues_by_type:
        lines.append("  By Type:")
        for issue_type, count in sorted(report.issues_by_type.items(), key=lambda x: -x[1]):
            lines.append(f"    - {issue_type.replace('_', ' ').title()}: {count}")
        lines.append("")
    
    lines.extend([
        "🤖 AI ANALYSIS",
        "-" * 40,
        f"  Bad Movies Found:      {report.bad_movies_found}",
        f"  Recommendations:       {report.recommendations_pending}",
        f"  AI Cost This Month:    ${report.ai_cost_this_month:.4f}",
        "",
        "📊 SCAN HISTORY",
        "-" * 40,
        f"  Last Scan:     {report.last_scan_date.strftime('%Y-%m-%d %H:%M') if report.last_scan_date else 'Never'}",
        f"  Last Status:   {report.last_scan_status or 'N/A'}",
        f"  Scans/Month:   {report.scans_this_month}",
        "",
        "🔗 SERVICES",
        "-" * 40,
    ])
    
    for service, configured in report.services_configured.items():
        status = "✅ Connected" if configured else "❌ Not configured"
        lines.append(f"  {service.title():12} {status}")
    
    lines.extend([
        "",
        "=" * 60,
        "End of Report",
        "=" * 60,
    ])
    
    return {"report": "\n".join(lines)}


@router.get("/summary")
async def get_report_summary(db: AsyncSession = Depends(get_db)):
    """Get a quick summary for the dashboard."""
    config = get_config()
    
    movies = await db.scalar(select(func.count(Movie.id))) or 0
    shows = await db.scalar(select(func.count(TVShow.id))) or 0
    issues = await db.scalar(
        select(func.count(Issue.id)).where(Issue.is_resolved == False)
    ) or 0
    critical = await db.scalar(
        select(func.count(Issue.id)).where(
            Issue.is_resolved == False,
            Issue.severity == IssueSeverity.CRITICAL
        )
    ) or 0
    
    return {
        "movies": movies,
        "tv_shows": shows,
        "open_issues": issues,
        "critical_issues": critical,
        "ai_enabled": config.ai.enabled and (config.ai.has_anthropic or config.ai.has_openai),
        "plex_connected": config.plex.is_configured,
    }
