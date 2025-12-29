"""
Embedded AI Management Endpoints.

This module handles downloading, managing, and checking the status of
the embedded AI model (Qwen 2.5 1.5B). The model runs locally without
requiring any external API keys or services.

The model file is ~1GB and is downloaded from Hugging Face on first use
or when explicitly requested by the user.
"""

import os
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import structlog

from backend.utils.constants import PATHS

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/embedded-ai", tags=["embedded-ai"])

# Model information
MODEL_INFO = {
    "name": "Qwen 2.5 1.5B Instruct",
    "filename": "qwen2.5-1.5b-instruct.Q4_K_M.gguf",
    "size_bytes": 1_100_000_000,  # ~1.1 GB
    "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    "description": "Compact but capable local AI model for library analysis and chat",
}

# Download state tracking
_download_state = {
    "in_progress": False,
    "progress_percent": 0,
    "downloaded_bytes": 0,
    "total_bytes": 0,
    "error": None,
    "status": "idle",
}


class ModelStatus(BaseModel):
    """Embedded AI model status."""
    installed: bool
    model_name: str
    model_size_bytes: int
    model_path: str
    download_available: bool
    download_in_progress: bool
    download_progress_percent: float
    download_error: Optional[str]
    status: str


class DownloadProgress(BaseModel):
    """Download progress information."""
    in_progress: bool
    progress_percent: float
    downloaded_bytes: int
    total_bytes: int
    status: str
    error: Optional[str]


@router.get("/status", response_model=ModelStatus)
async def get_model_status():
    """
    Get the status of the embedded AI model.

    Returns whether the model is installed, its size, and download status.
    """
    model_path = PATHS.embedded_model_path()
    installed = model_path.exists()

    actual_size = 0
    if installed:
        actual_size = model_path.stat().st_size

    return ModelStatus(
        installed=installed,
        model_name=MODEL_INFO["name"],
        model_size_bytes=actual_size if installed else MODEL_INFO["size_bytes"],
        model_path=str(model_path),
        download_available=not installed and not _download_state["in_progress"],
        download_in_progress=_download_state["in_progress"],
        download_progress_percent=_download_state["progress_percent"],
        download_error=_download_state["error"],
        status=_download_state["status"] if _download_state["in_progress"] else ("ready" if installed else "not_installed"),
    )


@router.get("/download/progress", response_model=DownloadProgress)
async def get_download_progress():
    """Get current download progress."""
    return DownloadProgress(
        in_progress=_download_state["in_progress"],
        progress_percent=_download_state["progress_percent"],
        downloaded_bytes=_download_state["downloaded_bytes"],
        total_bytes=_download_state["total_bytes"],
        status=_download_state["status"],
        error=_download_state["error"],
    )


@router.post("/download/start")
async def start_model_download(background_tasks: BackgroundTasks):
    """
    Start downloading the embedded AI model.

    The download runs in the background. Use /download/progress to monitor.
    The model is ~1.1GB and may take several minutes depending on connection speed.
    """
    global _download_state

    if _download_state["in_progress"]:
        raise HTTPException(status_code=409, detail="Download already in progress")

    model_path = PATHS.embedded_model_path()
    if model_path.exists():
        raise HTTPException(status_code=400, detail="Model already installed")

    # Reset state and start download
    _download_state = {
        "in_progress": True,
        "progress_percent": 0,
        "downloaded_bytes": 0,
        "total_bytes": MODEL_INFO["size_bytes"],
        "error": None,
        "status": "starting",
    }

    background_tasks.add_task(_download_model)

    return {
        "status": "started",
        "message": "Model download started. This may take several minutes.",
        "model_size_mb": MODEL_INFO["size_bytes"] // (1024 * 1024),
    }


@router.post("/download/cancel")
async def cancel_model_download():
    """Cancel an in-progress download."""
    global _download_state

    if not _download_state["in_progress"]:
        raise HTTPException(status_code=400, detail="No download in progress")

    _download_state["status"] = "cancelling"
    # The download task will check this and stop

    return {"status": "cancelling", "message": "Download cancellation requested"}


@router.delete("/model")
async def delete_model():
    """
    Delete the installed model.

    This frees up disk space (~1.1GB). The model can be re-downloaded later.
    """
    model_path = PATHS.embedded_model_path()

    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model not installed")

    try:
        model_path.unlink()
        logger.info("Embedded AI model deleted", path=str(model_path))
        return {"status": "deleted", "message": "Model deleted successfully"}
    except Exception as e:
        logger.error("Failed to delete model", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


async def _download_model():
    """Background task to download the model file."""
    global _download_state

    import httpx

    model_path = PATHS.embedded_model_path()
    model_dir = model_path.parent
    temp_path = model_path.with_suffix(".tmp")

    try:
        # Ensure directory exists
        model_dir.mkdir(parents=True, exist_ok=True)

        _download_state["status"] = "connecting"
        logger.info("Starting embedded AI model download", url=MODEL_INFO["url"])

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=300.0)) as client:
            async with client.stream("GET", MODEL_INFO["url"], follow_redirects=True) as response:
                response.raise_for_status()

                total = int(response.headers.get("content-length", MODEL_INFO["size_bytes"]))
                _download_state["total_bytes"] = total
                _download_state["status"] = "downloading"

                downloaded = 0

                with open(temp_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):  # 1MB chunks
                        # Check for cancellation
                        if _download_state["status"] == "cancelling":
                            logger.info("Download cancelled by user")
                            _download_state["status"] = "cancelled"
                            _download_state["in_progress"] = False
                            if temp_path.exists():
                                temp_path.unlink()
                            return

                        f.write(chunk)
                        downloaded += len(chunk)
                        _download_state["downloaded_bytes"] = downloaded
                        _download_state["progress_percent"] = (downloaded / total) * 100

        # Move temp file to final location
        _download_state["status"] = "finalizing"
        temp_path.rename(model_path)

        _download_state["status"] = "complete"
        _download_state["progress_percent"] = 100
        _download_state["in_progress"] = False

        logger.info("Embedded AI model download complete", path=str(model_path))

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error: {e.response.status_code}"
        logger.error("Model download failed", error=error_msg)
        _download_state["error"] = error_msg
        _download_state["status"] = "error"
        _download_state["in_progress"] = False
        if temp_path.exists():
            temp_path.unlink()

    except Exception as e:
        error_msg = str(e)
        logger.error("Model download failed", error=error_msg)
        _download_state["error"] = error_msg
        _download_state["status"] = "error"
        _download_state["in_progress"] = False
        if temp_path.exists():
            temp_path.unlink()


@router.post("/test")
async def test_embedded_ai():
    """
    Test the embedded AI with a simple prompt.

    Returns a sample response to verify the model is working correctly.
    """
    model_path = PATHS.embedded_model_path()

    if not model_path.exists():
        raise HTTPException(status_code=400, detail="Model not installed. Download it first.")

    try:
        from backend.core.ai.provider import EmbeddedAI

        ai = EmbeddedAI(str(model_path))
        result = await ai.generate(
            prompt="Say 'Hello! Embedded AI is working correctly.' and nothing else.",
            max_tokens=50,
            temperature=0.1,
        )

        return {
            "success": True,
            "response": result["content"],
            "tokens_used": result["total_tokens"],
            "model": result["model"],
        }

    except Exception as e:
        logger.error("Embedded AI test failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
