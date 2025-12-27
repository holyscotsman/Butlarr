"""Issues management endpoints."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Issue, Movie, TVShow, IssueType, IssueSeverity

router = APIRouter()


class IssueResponse(BaseModel):
    """Single issue item."""
    id: int
    issue_type: str
    severity: str
    title: str
    description: Optional[str]
    file_path: Optional[str]
    media_title: Optional[str]
    media_type: Optional[str]
    can_auto_fix: bool
    auto_fix_action: Optional[str]
    detected_at: datetime
    is_resolved: bool
    resolved_at: Optional[datetime]


class IssuesListResponse(BaseModel):
    """List of issues."""
    issues: List[IssueResponse]
    total: int
    by_severity: dict
    by_type: dict
    has_more: bool


class ResolveIssueRequest(BaseModel):
    """Request to resolve an issue."""
    issue_id: int
    resolution_notes: Optional[str] = None


class AutoFixRequest(BaseModel):
    """Request to auto-fix an issue."""
    issue_id: int


@router.get("", response_model=IssuesListResponse)
async def get_issues(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    severity: Optional[str] = Query(None, pattern="^(info|warning|error|critical)$"),
    issue_type: Optional[str] = None,
    include_resolved: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get list of issues."""
    query = select(Issue)
    
    if not include_resolved:
        query = query.where(Issue.is_resolved == False)
    
    if severity:
        query = query.where(Issue.severity == IssueSeverity(severity))
    
    if issue_type:
        query = query.where(Issue.issue_type == IssueType(issue_type))
    
    # Order by severity (critical first), then by date
    query = query.order_by(
        Issue.severity.desc(),
        Issue.detected_at.desc()
    )
    
    # Get counts
    count_query = select(Issue)
    if not include_resolved:
        count_query = count_query.where(Issue.is_resolved == False)
    count_result = await db.execute(count_query)
    total = len(count_result.all())
    
    # Get severity breakdown
    from sqlalchemy import func
    severity_query = select(Issue.severity, func.count(Issue.id)).where(
        Issue.is_resolved == False
    ).group_by(Issue.severity)
    severity_result = await db.execute(severity_query)
    by_severity = {r[0].value: r[1] for r in severity_result.all()}
    
    # Get type breakdown
    type_query = select(Issue.issue_type, func.count(Issue.id)).where(
        Issue.is_resolved == False
    ).group_by(Issue.issue_type)
    type_result = await db.execute(type_query)
    by_type = {r[0].value: r[1] for r in type_result.all()}
    
    # Get paginated results
    query = query.offset(offset).limit(limit)
    results = await db.scalars(query)
    
    issues = []
    for issue in results.all():
        # Get associated media info
        media_title = None
        media_type = None
        
        if issue.movie_id:
            movie = await db.get(Movie, issue.movie_id)
            if movie:
                media_title = movie.title
                media_type = "movie"
        elif issue.tv_show_id:
            show = await db.get(TVShow, issue.tv_show_id)
            if show:
                media_title = show.title
                media_type = "tv_show"
        
        issues.append(IssueResponse(
            id=issue.id,
            issue_type=issue.issue_type.value,
            severity=issue.severity.value,
            title=issue.title,
            description=issue.description,
            file_path=issue.file_path,
            media_title=media_title,
            media_type=media_type,
            can_auto_fix=issue.can_auto_fix,
            auto_fix_action=issue.auto_fix_action,
            detected_at=issue.detected_at,
            is_resolved=issue.is_resolved,
            resolved_at=issue.resolved_at,
        ))
    
    return IssuesListResponse(
        issues=issues,
        total=total,
        by_severity=by_severity,
        by_type=by_type,
        has_more=offset + limit < total,
    )


@router.get("/types")
async def get_issue_types():
    """Get all issue types with descriptions."""
    return {
        "types": [
            {"value": "corrupt_file", "label": "Corrupt File", "description": "File is corrupted or unplayable"},
            {"value": "audio_sync", "label": "Audio Sync", "description": "Audio is out of sync with video"},
            {"value": "missing_audio", "label": "Missing Audio", "description": "No audio track found"},
            {"value": "missing_subtitle", "label": "Missing Subtitle", "description": "No subtitles available"},
            {"value": "subtitle_timing", "label": "Subtitle Timing", "description": "Subtitles are out of sync"},
            {"value": "hdr_metadata", "label": "HDR Metadata", "description": "HDR metadata issues"},
            {"value": "wrong_language", "label": "Wrong Language", "description": "Audio language doesn't match expected"},
            {"value": "oversized_file", "label": "Oversized File", "description": "File is larger than expected"},
            {"value": "undersized_file", "label": "Undersized File", "description": "File is smaller than expected (may be poor quality)"},
            {"value": "duplicate_file", "label": "Duplicate File", "description": "Multiple versions of the same content"},
            {"value": "bad_naming", "label": "Bad Naming", "description": "File or folder naming doesn't follow conventions"},
            {"value": "missing_collection", "label": "Incomplete Collection", "description": "Missing movies from a collection"},
            {"value": "outdated_codec", "label": "Outdated Codec", "description": "Uses old codec that could be modernized"},
            {"value": "low_quality", "label": "Low Quality", "description": "Resolution or bitrate below expectations"},
        ]
    }


@router.post("/resolve")
async def resolve_issue(
    request: ResolveIssueRequest,
    db: AsyncSession = Depends(get_db)
):
    """Mark an issue as resolved."""
    issue = await db.get(Issue, request.issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    issue.is_resolved = True
    issue.resolved_at = datetime.utcnow()
    issue.resolution_notes = request.resolution_notes
    
    from backend.db.models import Activity, ActionType
    activity = Activity(
        action_type=ActionType.ISSUE_RESOLVED,
        title=f"Resolved: {issue.title}",
        description=request.resolution_notes,
    )
    db.add(activity)
    
    await db.commit()
    
    return {"status": "success", "message": "Issue marked as resolved"}


@router.post("/auto-fix")
async def auto_fix_issue(
    request: AutoFixRequest,
    db: AsyncSession = Depends(get_db)
):
    """Attempt to auto-fix an issue."""
    issue = await db.get(Issue, request.issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    if not issue.can_auto_fix:
        raise HTTPException(status_code=400, detail="This issue cannot be auto-fixed")
    
    # Implement auto-fix logic based on issue type
    # This would delegate to specific handlers
    
    return {"status": "started", "message": "Auto-fix initiated"}


@router.post("/bulk-resolve")
async def bulk_resolve_issues(
    issue_ids: List[int],
    db: AsyncSession = Depends(get_db)
):
    """Resolve multiple issues at once."""
    resolved = 0
    
    for issue_id in issue_ids:
        issue = await db.get(Issue, issue_id)
        if issue and not issue.is_resolved:
            issue.is_resolved = True
            issue.resolved_at = datetime.utcnow()
            resolved += 1
    
    await db.commit()
    
    return {
        "status": "success",
        "resolved": resolved,
        "message": f"Resolved {resolved} issues"
    }


@router.get("/stats")
async def get_issue_stats(db: AsyncSession = Depends(get_db)):
    """Get issue statistics."""
    from sqlalchemy import func
    
    total_open = await db.scalar(
        select(func.count(Issue.id)).where(Issue.is_resolved == False)
    )
    
    critical = await db.scalar(
        select(func.count(Issue.id)).where(
            and_(
                Issue.is_resolved == False,
                Issue.severity == IssueSeverity.CRITICAL,
            )
        )
    )
    
    auto_fixable = await db.scalar(
        select(func.count(Issue.id)).where(
            and_(
                Issue.is_resolved == False,
                Issue.can_auto_fix == True,
            )
        )
    )
    
    resolved_today = await db.scalar(
        select(func.count(Issue.id)).where(
            and_(
                Issue.is_resolved == True,
                Issue.resolved_at >= datetime.utcnow().replace(hour=0, minute=0, second=0),
            )
        )
    )
    
    return {
        "total_open": total_open or 0,
        "critical": critical or 0,
        "auto_fixable": auto_fixable or 0,
        "resolved_today": resolved_today or 0,
    }
