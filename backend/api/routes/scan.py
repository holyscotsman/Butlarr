"""Scan management endpoints."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Scan, ScanStatus
from backend.utils.config import get_config

router = APIRouter()


class ScanStartRequest(BaseModel):
    """Request to start a new scan."""
    phases: Optional[List[int]] = None  # Specific phases to run, None = all
    skip_ai_curator: bool = False


class ScanProgressResponse(BaseModel):
    """Current scan progress."""
    id: int
    status: str
    current_phase: int
    total_phases: int
    phase_name: str
    progress_percent: float
    current_item: Optional[str]
    items_processed: int
    items_total: int
    elapsed_seconds: int
    estimated_remaining_seconds: Optional[int]
    ai_cost_usd: float


class ScanHistoryItem(BaseModel):
    """Scan history item."""
    id: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    elapsed_seconds: Optional[int]
    movies_scanned: int
    tv_shows_scanned: int
    issues_found: int
    ai_cost_usd: float


class CostEstimateResponse(BaseModel):
    """AI cost estimate for scan."""
    estimated_cost_usd: float
    estimated_tokens: int
    model_to_use: str
    warning: Optional[str] = None


@router.post("/start")
async def start_scan(
    request: ScanStartRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Start a new library scan."""
    scan_manager = http_request.app.state.scan_manager
    
    # Check if scan is already running
    if scan_manager.is_running:
        raise HTTPException(status_code=409, detail="A scan is already in progress")
    
    # Create scan record
    scan = Scan(
        status=ScanStatus.PENDING,
        total_phases=17,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    
    # Start scan in background
    await scan_manager.start_scan(
        scan_id=scan.id,
        phases=request.phases,
        skip_ai_curator=request.skip_ai_curator,
    )
    
    return {
        "status": "started",
        "scan_id": scan.id,
        "message": "Scan started successfully"
    }


@router.post("/stop")
async def stop_scan(http_request: Request):
    """Stop the current scan."""
    scan_manager = http_request.app.state.scan_manager
    
    if not scan_manager.is_running:
        raise HTTPException(status_code=400, detail="No scan is currently running")
    
    await scan_manager.stop_scan()
    
    return {"status": "stopped", "message": "Scan stopped"}


@router.post("/pause")
async def pause_scan(http_request: Request):
    """Pause the current scan."""
    scan_manager = http_request.app.state.scan_manager
    
    if not scan_manager.is_running:
        raise HTTPException(status_code=400, detail="No scan is currently running")
    
    await scan_manager.pause_scan()
    
    return {"status": "paused", "message": "Scan paused"}


@router.post("/resume")
async def resume_scan(http_request: Request):
    """Resume a paused scan."""
    scan_manager = http_request.app.state.scan_manager
    
    if not scan_manager.is_paused:
        raise HTTPException(status_code=400, detail="No scan is currently paused")
    
    await scan_manager.resume_scan()
    
    return {"status": "resumed", "message": "Scan resumed"}


@router.get("/progress", response_model=ScanProgressResponse)
async def get_scan_progress(
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get current scan progress."""
    scan_manager = http_request.app.state.scan_manager
    
    if not scan_manager.current_scan_id:
        # Get most recent scan
        scan = await db.scalar(
            select(Scan).order_by(Scan.created_at.desc()).limit(1)
        )
        if not scan:
            raise HTTPException(status_code=404, detail="No scan found")
    else:
        scan = await db.get(Scan, scan_manager.current_scan_id)
    
    return ScanProgressResponse(
        id=scan.id,
        status=scan.status.value,
        current_phase=scan.current_phase or 0,
        total_phases=scan.total_phases,
        phase_name=scan.phase_name or "Initializing",
        progress_percent=scan.progress_percent or 0.0,
        current_item=scan.current_item,
        items_processed=scan.items_processed or 0,
        items_total=scan.items_total or 0,
        elapsed_seconds=scan.elapsed_seconds or 0,
        estimated_remaining_seconds=scan.estimated_remaining_seconds,
        ai_cost_usd=scan.ai_cost_usd or 0.0,
    )


@router.get("/history", response_model=List[ScanHistoryItem])
async def get_scan_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get scan history."""
    scans = await db.scalars(
        select(Scan).order_by(Scan.created_at.desc()).limit(limit)
    )
    
    return [
        ScanHistoryItem(
            id=s.id,
            status=s.status.value,
            started_at=s.started_at,
            completed_at=s.completed_at,
            elapsed_seconds=s.elapsed_seconds,
            movies_scanned=s.movies_scanned or 0,
            tv_shows_scanned=s.tv_shows_scanned or 0,
            issues_found=s.issues_found or 0,
            ai_cost_usd=s.ai_cost_usd or 0.0,
        )
        for s in scans.all()
    ]


@router.get("/estimate-cost", response_model=CostEstimateResponse)
async def estimate_scan_cost(db: AsyncSession = Depends(get_db)):
    """Estimate AI cost for a full scan."""
    from backend.db.models import Movie, TVShow
    from sqlalchemy import func
    
    config = get_config()
    
    # Count items
    movie_count = await db.scalar(select(func.count(Movie.id))) or 0
    tv_show_count = await db.scalar(select(func.count(TVShow.id))) or 0
    
    # Estimate tokens (rough calculation)
    # ~100 tokens per movie metadata, ~150 per TV show
    estimated_input_tokens = (movie_count * 100) + (tv_show_count * 150)
    estimated_output_tokens = 5000  # Recommendations + bad movie suggestions
    
    # Get model pricing
    model = config.ai.curator_model
    if model == "auto" or model == "claude-sonnet-4-5":
        price_per_1m_input = 3.0
        price_per_1m_output = 15.0
        model_name = "Claude Sonnet 4.5"
    elif model == "claude-opus-4-5":
        price_per_1m_input = 5.0
        price_per_1m_output = 25.0
        model_name = "Claude Opus 4.5"
    elif model == "gpt-5-mini":
        price_per_1m_input = 0.25
        price_per_1m_output = 2.0
        model_name = "GPT-5 Mini"
    else:
        price_per_1m_input = 3.0
        price_per_1m_output = 15.0
        model_name = "Default (Sonnet)"
    
    estimated_cost = (
        (estimated_input_tokens / 1_000_000) * price_per_1m_input +
        (estimated_output_tokens / 1_000_000) * price_per_1m_output
    )
    
    warning = None
    if estimated_cost > config.ai.per_scan_alert_threshold:
        warning = f"Estimated cost (${estimated_cost:.2f}) exceeds your alert threshold (${config.ai.per_scan_alert_threshold:.2f})"
    
    return CostEstimateResponse(
        estimated_cost_usd=round(estimated_cost, 4),
        estimated_tokens=estimated_input_tokens + estimated_output_tokens,
        model_to_use=model_name,
        warning=warning,
    )


@router.get("/phases")
async def get_scan_phases():
    """Get list of all scan phases."""
    return {
        "phases": [
            {"id": 1, "name": "Library Sync", "description": "Quick scan from Plex - gather all movies/shows"},
            {"id": 2, "name": "AI Curation", "description": "Send to AI Curator for recommendations & removals"},
            {"id": 3, "name": "Service Sync", "description": "Cross-reference Plex ↔ Radarr ↔ Sonarr"},
            {"id": 4, "name": "Overseerr Sync", "description": "Mark requested items as protected"},
            {"id": 5, "name": "Collection Analysis", "description": "Identify incomplete collections"},
            {"id": 6, "name": "Movie Organization", "description": "FileBot rename/organize movies"},
            {"id": 7, "name": "TV Organization", "description": "Sonarr rename/organize per show"},
            {"id": 8, "name": "Movie Deep Scan", "description": "Duplicates, naming, folder structure, subtitles"},
            {"id": 9, "name": "TV Deep Scan", "description": "Duplicates, season folders, naming"},
            {"id": 10, "name": "Other Media Scan", "description": "Scan non-movie/TV folders"},
            {"id": 11, "name": "Movie Integrity", "description": "Full decode, corruption, audio sync"},
            {"id": 12, "name": "TV Integrity", "description": "Full decode, corruption, audio sync"},
            {"id": 13, "name": "Language Validation", "description": "Audio language matches content origin"},
            {"id": 14, "name": "Movie HDR/Subtitle", "description": "HDR metadata, subtitle timing"},
            {"id": 15, "name": "TV HDR/Subtitle", "description": "HDR metadata, subtitle timing"},
            {"id": 16, "name": "Storage Analysis", "description": "File sizes, duplicates, space optimization"},
            {"id": 17, "name": "Codec Analysis", "description": "Identify outdated codecs for modernization"},
        ]
    }
