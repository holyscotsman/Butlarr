"""Activity log endpoints."""

from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Activity, ActionType

router = APIRouter()


class ActivityItem(BaseModel):
    """Single activity item."""
    id: int
    action_type: str
    title: str
    description: Optional[str]
    details: Optional[dict]
    created_at: datetime


class ActivityListResponse(BaseModel):
    """List of activities."""
    activities: List[ActivityItem]
    total: int
    has_more: bool


@router.get("", response_model=ActivityListResponse)
async def get_activity(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action_type: Optional[str] = None,
    days: Optional[int] = Query(None, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get activity log."""
    query = select(Activity)
    
    if action_type:
        query = query.where(Activity.action_type == ActionType(action_type))
    
    if days:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.where(Activity.created_at >= cutoff)
    
    query = query.order_by(Activity.created_at.desc())
    
    # Get total count
    from sqlalchemy import func
    count_query = select(func.count(Activity.id))
    if action_type:
        count_query = count_query.where(Activity.action_type == ActionType(action_type))
    if days:
        cutoff = datetime.utcnow() - timedelta(days=days)
        count_query = count_query.where(Activity.created_at >= cutoff)
    
    total = await db.scalar(count_query) or 0
    
    # Get paginated results
    query = query.offset(offset).limit(limit)
    results = await db.scalars(query)
    
    activities = [
        ActivityItem(
            id=a.id,
            action_type=a.action_type.value,
            title=a.title,
            description=a.description,
            details=a.details,
            created_at=a.created_at,
        )
        for a in results.all()
    ]
    
    return ActivityListResponse(
        activities=activities,
        total=total,
        has_more=offset + limit < total,
    )


@router.get("/types")
async def get_action_types():
    """Get all action types."""
    return {
        "types": [
            {"value": t.value, "label": t.value.replace("_", " ").title()}
            for t in ActionType
        ]
    }


@router.get("/recent")
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get most recent activity for dashboard."""
    results = await db.scalars(
        select(Activity)
        .order_by(Activity.created_at.desc())
        .limit(limit)
    )
    
    return [
        {
            "id": a.id,
            "action_type": a.action_type.value,
            "title": a.title,
            "created_at": a.created_at.isoformat(),
        }
        for a in results.all()
    ]


@router.delete("/clear")
async def clear_activity(
    before_days: int = Query(30, ge=1),
    db: AsyncSession = Depends(get_db)
):
    """Clear activity older than specified days."""
    cutoff = datetime.utcnow() - timedelta(days=before_days)
    
    from sqlalchemy import delete
    result = await db.execute(
        delete(Activity).where(Activity.created_at < cutoff)
    )
    
    await db.commit()
    
    return {
        "status": "success",
        "deleted": result.rowcount,
        "message": f"Deleted {result.rowcount} activities older than {before_days} days"
    }
