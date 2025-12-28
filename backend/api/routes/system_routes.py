"""System routes - Updates, logs, health checks."""

import os
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import structlog

from backend.utils.version import VERSION, BUILD_DATE
from backend.utils.constants import TIMEOUTS, PATHS

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


class UpdateStatus(BaseModel):
    available: bool
    current_version: str
    latest_commit: Optional[str] = None
    update_in_progress: bool = False
    last_check: Optional[str] = None
    message: Optional[str] = None


class SystemInfo(BaseModel):
    version: str
    build_date: str
    uptime_seconds: int
    ai_providers: list
    embedded_ai_available: bool
    embedded_ai_model: Optional[str] = None
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    auto_update_enabled: bool


# Global state for update tracking
_update_state = {
    "in_progress": False,
    "last_check": None,
    "latest_commit": None,
}
_start_time = datetime.utcnow()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    """Get system information."""
    from backend.utils.config import get_config
    config = get_config()
    
    # Get git info
    git_commit = None
    git_branch = None
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd="/app"
        ).decode().strip()
        git_branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd="/app"
        ).decode().strip()
    except:
        pass
    
    # Check AI providers
    ai_providers = []
    if config.ai.anthropic_api_key:
        ai_providers.append("anthropic")
    if config.ai.openai_api_key:
        ai_providers.append("openai")
    if config.ai.ollama_url:
        ai_providers.append("ollama")
    
    # Check embedded AI - using centralized path constant
    embedded_model_path = PATHS.embedded_model_path()
    embedded_available = embedded_model_path.exists()
    if embedded_available:
        ai_providers.append("embedded")
    
    uptime = (datetime.utcnow() - _start_time).total_seconds()
    
    return SystemInfo(
        version=VERSION,
        build_date=BUILD_DATE,
        uptime_seconds=int(uptime),
        ai_providers=ai_providers,
        embedded_ai_available=embedded_available,
        embedded_ai_model="qwen2.5-1.5b-instruct" if embedded_available else None,
        git_commit=git_commit,
        git_branch=git_branch,
        auto_update_enabled=os.environ.get("AUTO_UPDATE", "true").lower() == "true",
    )


@router.get("/update/check", response_model=UpdateStatus)
async def check_for_updates():
    """Check if updates are available from GitHub."""
    if _update_state["in_progress"]:
        return UpdateStatus(
            available=False,
            current_version=VERSION,
            update_in_progress=True,
            message="Update already in progress",
        )

    # Check if .git directory exists (Docker images may not include it)
    git_dir = PATHS.git_dir()
    if not git_dir.exists():
        # No git directory - suggest using Docker image updates instead
        _update_state["last_check"] = datetime.utcnow().isoformat()
        return UpdateStatus(
            available=False,
            current_version=VERSION,
            update_in_progress=False,
            last_check=_update_state["last_check"],
            message="Updates managed via Docker. Restart container with AUTO_UPDATE=true to auto-update, or pull latest image.",
        )

    try:
        # Fetch latest from remote
        result = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=str(PATHS.APP_ROOT),
            capture_output=True,
            timeout=TIMEOUTS.GIT_FETCH,
        )

        # Get current branch
        app_root = str(PATHS.APP_ROOT)
        try:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=app_root,
                stderr=subprocess.DEVNULL,
            ).decode().strip()
        except:
            branch = "main"

        # Get local and remote commits
        local = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=app_root
        ).decode().strip()

        try:
            remote = subprocess.check_output(
                ["git", "rev-parse", f"origin/{branch}"],
                cwd=app_root
            ).decode().strip()
        except:
            # Fallback to origin/main
            remote = subprocess.check_output(
                ["git", "rev-parse", "origin/main"],
                cwd=app_root
            ).decode().strip()

        _update_state["last_check"] = datetime.utcnow().isoformat()
        _update_state["latest_commit"] = remote[:8]

        available = local != remote

        return UpdateStatus(
            available=available,
            current_version=VERSION,
            latest_commit=remote[:8],
            update_in_progress=False,
            last_check=_update_state["last_check"],
            message="Update available!" if available else "Already up to date",
        )
    except subprocess.TimeoutExpired:
        return UpdateStatus(
            available=False,
            current_version=VERSION,
            update_in_progress=False,
            message="Update check timed out. Try again later.",
        )
    except Exception as e:
        logger.error("Failed to check for updates", error=str(e))
        return UpdateStatus(
            available=False,
            current_version=VERSION,
            update_in_progress=False,
            message="Updates managed via Docker. Restart container to check for updates.",
        )


async def _perform_update():
    """Background task to perform the update."""
    global _update_state
    
    try:
        logger.info("Starting update process")
        
        # Pull latest code
        app_root = str(PATHS.APP_ROOT)
        subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=app_root,
            check=True,
            capture_output=True,
            timeout=TIMEOUTS.GIT_PULL,
        )

        # Install any new Python dependencies
        subprocess.run(
            ["pip", "install", "-r", "requirements.txt", "--quiet", "--break-system-packages"],
            cwd=app_root,
            check=True,
            capture_output=True,
            timeout=TIMEOUTS.PIP_INSTALL,
        )
        
        logger.info("Update completed successfully")
        _update_state["in_progress"] = False
        
        # Note: The application should be restarted to apply changes
        # This could be done via a restart endpoint or manually
        
    except Exception as e:
        logger.error("Update failed", error=str(e))
        _update_state["in_progress"] = False
        raise


@router.post("/update/apply")
async def apply_update(background_tasks: BackgroundTasks):
    """Apply available updates. Requires app restart after completion."""
    if _update_state["in_progress"]:
        raise HTTPException(status_code=409, detail="Update already in progress")
    
    # Check if updates are available first
    check = await check_for_updates()
    if not check.available:
        raise HTTPException(status_code=400, detail="No updates available")
    
    _update_state["in_progress"] = True
    background_tasks.add_task(_perform_update)
    
    return {
        "status": "started",
        "message": "Update started. Restart the container when complete to apply changes.",
    }


@router.get("/logs")
async def get_logs(lines: int = 100):
    """Get recent application logs."""
    log_file = PATHS.log_file()
    
    if not log_file.exists():
        return {"logs": [], "message": "No log file found"}
    
    try:
        with open(log_file, "r") as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return {"logs": [line.strip() for line in recent]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")


@router.get("/logs/download")
async def download_logs():
    """Download full log file."""
    from fastapi.responses import FileResponse

    log_file = PATHS.log_file()
    
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")
    
    return FileResponse(
        path=str(log_file),
        filename=f"butlarr-logs-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.log",
        media_type="text/plain",
    )


@router.post("/restart")
async def request_restart():
    """Request application restart (container must support this)."""
    # This creates a file that the entrypoint can watch for
    restart_file = PATHS.restart_file()
    restart_file.parent.mkdir(parents=True, exist_ok=True)
    restart_file.touch()
    
    return {
        "status": "requested",
        "message": "Restart requested. If running in Docker with restart policy, stop and start the container.",
    }
