"""Setup wizard endpoints."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.utils.config import get_config, update_config, AppConfig
from backend.core.integrations.plex import PlexClient
from backend.core.integrations.radarr import RadarrClient
from backend.core.integrations.sonarr import SonarrClient
from backend.core.integrations.overseerr import OverseerrClient
from backend.core.integrations.tautulli import TautulliClient
from backend.core.integrations.filebot import FileBotClient
from backend.core.ai.provider import AIProvider

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ServiceTestRequest(BaseModel):
    """Request to test a service connection."""
    url: str
    token: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class ServiceTestResponse(BaseModel):
    """Response from service connection test."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class PlexSetupRequest(BaseModel):
    """Plex setup configuration."""
    url: str = Field(..., description="Plex server URL (e.g., http://192.168.1.100:32400)")
    token: str = Field(..., description="Plex authentication token")


class RadarrSetupRequest(BaseModel):
    """Radarr setup configuration."""
    url: str = Field(..., description="Radarr URL (e.g., http://192.168.1.100:7878)")
    api_key: str = Field(..., description="Radarr API key")


class SonarrSetupRequest(BaseModel):
    """Sonarr setup configuration."""
    url: str = Field(..., description="Sonarr URL (e.g., http://192.168.1.100:8989)")
    api_key: str = Field(..., description="Sonarr API key")


class BazarrSetupRequest(BaseModel):
    """Bazarr setup configuration."""
    url: str = Field(..., description="Bazarr URL (e.g., http://192.168.1.100:6767)")
    api_key: str = Field(..., description="Bazarr API key")


class OverseerrSetupRequest(BaseModel):
    """Overseerr setup configuration."""
    url: str = Field(..., description="Overseerr URL")
    api_key: str = Field(..., description="Overseerr API key")


class TautulliSetupRequest(BaseModel):
    """Tautulli setup configuration."""
    url: str = Field(..., description="Tautulli URL")
    api_key: str = Field(..., description="Tautulli API key")


class FileBotSetupRequest(BaseModel):
    """FileBot Node setup configuration."""
    url: str = Field(..., description="FileBot Node URL (e.g., http://192.168.1.100:5452)")
    username: Optional[str] = Field(None, description="FileBot username (if auth enabled)")
    password: Optional[str] = Field(None, description="FileBot password (if auth enabled)")


class AISetupRequest(BaseModel):
    """AI provider setup configuration."""
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_url: Optional[str] = None


class SetupStatusResponse(BaseModel):
    """Current setup status."""
    setup_complete: bool
    plex_configured: bool
    radarr_configured: bool
    sonarr_configured: bool
    overseerr_configured: bool
    tautulli_configured: bool
    filebot_configured: bool
    ai_configured: bool


class CompleteSetupRequest(BaseModel):
    """Request to mark setup as complete."""
    confirm: bool = True


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """Get current setup status."""
    config = get_config()
    
    return SetupStatusResponse(
        setup_complete=config.setup_complete,
        plex_configured=config.plex.is_configured,
        radarr_configured=config.radarr.is_configured,
        sonarr_configured=config.sonarr.is_configured,
        overseerr_configured=config.overseerr.is_configured,
        tautulli_configured=config.tautulli.is_configured,
        filebot_configured=config.filebot.is_configured,
        ai_configured=config.ai.has_anthropic or config.ai.has_openai,
    )


@router.post("/test/plex", response_model=ServiceTestResponse)
async def test_plex_connection(request: PlexSetupRequest):
    """Test Plex server connection."""
    try:
        client = PlexClient(request.url, request.token)
        info = await client.get_server_info()
        
        return ServiceTestResponse(
            success=True,
            message=f"Connected to {info.get('friendlyName', 'Plex Server')}",
            details={
                "server_name": info.get("friendlyName"),
                "version": info.get("version"),
                "platform": info.get("platform"),
            }
        )
    except Exception as e:
        return ServiceTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.post("/configure/plex")
async def configure_plex(request: PlexSetupRequest):
    """Save Plex configuration."""
    # Test connection first
    test_result = await test_plex_connection(request)
    if not test_result.success:
        raise HTTPException(status_code=400, detail=test_result.message)
    
    # Save configuration
    update_config({
        "plex": {
            "url": request.url,
            "token": request.token,
        }
    })
    
    return {"status": "success", "message": "Plex configured successfully"}


@router.post("/test/radarr", response_model=ServiceTestResponse)
async def test_radarr_connection(request: RadarrSetupRequest):
    """Test Radarr connection."""
    try:
        client = RadarrClient(request.url, request.api_key)
        info = await client.get_system_status()
        
        return ServiceTestResponse(
            success=True,
            message=f"Connected to Radarr v{info.get('version', 'unknown')}",
            details={
                "version": info.get("version"),
                "movie_count": await client.get_movie_count(),
            }
        )
    except Exception as e:
        return ServiceTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.post("/configure/radarr")
async def configure_radarr(request: RadarrSetupRequest):
    """Save Radarr configuration."""
    test_result = await test_radarr_connection(request)
    if not test_result.success:
        raise HTTPException(status_code=400, detail=test_result.message)
    
    update_config({
        "radarr": {
            "url": request.url,
            "api_key": request.api_key,
        }
    })
    
    return {"status": "success", "message": "Radarr configured successfully"}


@router.post("/test/sonarr", response_model=ServiceTestResponse)
async def test_sonarr_connection(request: SonarrSetupRequest):
    """Test Sonarr connection."""
    try:
        client = SonarrClient(request.url, request.api_key)
        info = await client.get_system_status()
        
        return ServiceTestResponse(
            success=True,
            message=f"Connected to Sonarr v{info.get('version', 'unknown')}",
            details={
                "version": info.get("version"),
                "series_count": await client.get_series_count(),
            }
        )
    except Exception as e:
        return ServiceTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.post("/configure/sonarr")
async def configure_sonarr(request: SonarrSetupRequest):
    """Save Sonarr configuration."""
    test_result = await test_sonarr_connection(request)
    if not test_result.success:
        raise HTTPException(status_code=400, detail=test_result.message)
    
    update_config({
        "sonarr": {
            "url": request.url,
            "api_key": request.api_key,
        }
    })
    
    return {"status": "success", "message": "Sonarr configured successfully"}


@router.post("/test/bazarr", response_model=ServiceTestResponse)
async def test_bazarr_connection(request: BazarrSetupRequest):
    """Test Bazarr connection."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Bazarr API endpoint to get system status
            headers = {"X-API-KEY": request.api_key}
            url = request.url.rstrip("/")
            response = await client.get(f"{url}/api/system/status", headers=headers)
            response.raise_for_status()
            info = response.json()

            return ServiceTestResponse(
                success=True,
                message=f"Connected to Bazarr v{info.get('data', {}).get('bazarr_version', 'unknown')}",
                details={
                    "version": info.get("data", {}).get("bazarr_version"),
                }
            )
    except Exception as e:
        return ServiceTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.post("/configure/bazarr")
async def configure_bazarr(request: BazarrSetupRequest):
    """Save Bazarr configuration."""
    test_result = await test_bazarr_connection(request)
    if not test_result.success:
        raise HTTPException(status_code=400, detail=test_result.message)

    update_config({
        "bazarr": {
            "url": request.url,
            "api_key": request.api_key,
        }
    })

    return {"status": "success", "message": "Bazarr configured successfully"}


@router.post("/test/overseerr", response_model=ServiceTestResponse)
async def test_overseerr_connection(request: OverseerrSetupRequest):
    """Test Overseerr connection."""
    try:
        client = OverseerrClient(request.url, request.api_key)
        info = await client.get_status()
        
        return ServiceTestResponse(
            success=True,
            message="Connected to Overseerr",
            details={
                "version": info.get("version"),
            }
        )
    except Exception as e:
        return ServiceTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.post("/configure/overseerr")
async def configure_overseerr(request: OverseerrSetupRequest):
    """Save Overseerr configuration."""
    test_result = await test_overseerr_connection(request)
    if not test_result.success:
        raise HTTPException(status_code=400, detail=test_result.message)
    
    update_config({
        "overseerr": {
            "url": request.url,
            "api_key": request.api_key,
        }
    })
    
    return {"status": "success", "message": "Overseerr configured successfully"}


@router.post("/test/tautulli", response_model=ServiceTestResponse)
async def test_tautulli_connection(request: TautulliSetupRequest):
    """Test Tautulli connection."""
    try:
        client = TautulliClient(request.url, request.api_key)
        info = await client.get_server_info()
        
        return ServiceTestResponse(
            success=True,
            message="Connected to Tautulli",
            details={
                "version": info.get("tautulli_version"),
            }
        )
    except Exception as e:
        return ServiceTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.post("/configure/tautulli")
async def configure_tautulli(request: TautulliSetupRequest):
    """Save Tautulli configuration."""
    test_result = await test_tautulli_connection(request)
    if not test_result.success:
        raise HTTPException(status_code=400, detail=test_result.message)
    
    update_config({
        "tautulli": {
            "url": request.url,
            "api_key": request.api_key,
        }
    })
    
    return {"status": "success", "message": "Tautulli configured successfully"}


@router.post("/test/filebot", response_model=ServiceTestResponse)
async def test_filebot_connection(request: FileBotSetupRequest):
    """Test FileBot Node connection."""
    try:
        client = FileBotClient(request.url, request.username, request.password)
        info = await client.get_status()
        
        return ServiceTestResponse(
            success=True,
            message="Connected to FileBot Node",
            details={
                "filebot_version": info.get("filebot_version"),
                "license_status": info.get("license_status"),
            }
        )
    except Exception as e:
        return ServiceTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.post("/configure/filebot")
async def configure_filebot(request: FileBotSetupRequest):
    """Save FileBot Node configuration."""
    test_result = await test_filebot_connection(request)
    if not test_result.success:
        raise HTTPException(status_code=400, detail=test_result.message)
    
    update_config({
        "filebot": {
            "url": request.url,
            "username": request.username or "",
            "password": request.password or "",
        }
    })
    
    return {"status": "success", "message": "FileBot configured successfully"}


@router.post("/test/ai", response_model=ServiceTestResponse)
async def test_ai_connection(request: AISetupRequest):
    """Test AI provider connections."""
    results = {}
    
    if request.anthropic_api_key:
        try:
            provider = AIProvider(anthropic_api_key=request.anthropic_api_key)
            await provider.test_anthropic()
            results["anthropic"] = "Connected"
        except Exception as e:
            results["anthropic"] = f"Failed: {str(e)}"
    
    if request.openai_api_key:
        try:
            provider = AIProvider(openai_api_key=request.openai_api_key)
            await provider.test_openai()
            results["openai"] = "Connected"
        except Exception as e:
            results["openai"] = f"Failed: {str(e)}"
    
    if request.ollama_url:
        try:
            provider = AIProvider(ollama_url=request.ollama_url)
            models = await provider.test_ollama()
            results["ollama"] = f"Connected ({len(models)} models available)"
        except Exception as e:
            results["ollama"] = f"Failed: {str(e)}"
    
    success = any("Connected" in str(v) for v in results.values())
    
    return ServiceTestResponse(
        success=success,
        message="AI provider test complete" if success else "No AI providers connected",
        details=results
    )


@router.post("/configure/ai")
async def configure_ai(request: AISetupRequest):
    """Save AI configuration."""
    update_config({
        "ai": {
            "anthropic_api_key": request.anthropic_api_key or "",
            "openai_api_key": request.openai_api_key or "",
            "ollama_url": request.ollama_url or "http://host.docker.internal:11434",
        }
    })
    
    return {"status": "success", "message": "AI configuration saved"}


@router.post("/complete")
async def complete_setup(request: CompleteSetupRequest):
    """Mark setup as complete."""
    config = get_config()
    
    # Verify Plex is configured (required)
    if not config.plex.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Plex must be configured before completing setup"
        )
    
    update_config({"setup_complete": True})
    
    return {"status": "success", "message": "Setup complete! Redirecting to dashboard..."}


@router.get("/config")
async def get_current_config():
    """Get current configuration (with sensitive data masked)."""
    config = get_config()
    
    return {
        "setup_complete": config.setup_complete,
        "plex": {
            "url": config.plex.url,
            "token": "***" if config.plex.token else "",
            "is_configured": config.plex.is_configured,
        },
        "radarr": {
            "url": config.radarr.url,
            "api_key": "***" if config.radarr.api_key else "",
            "is_configured": config.radarr.is_configured,
        },
        "sonarr": {
            "url": config.sonarr.url,
            "api_key": "***" if config.sonarr.api_key else "",
            "is_configured": config.sonarr.is_configured,
        },
        "overseerr": {
            "url": config.overseerr.url,
            "api_key": "***" if config.overseerr.api_key else "",
            "is_configured": config.overseerr.is_configured,
        },
        "tautulli": {
            "url": config.tautulli.url,
            "api_key": "***" if config.tautulli.api_key else "",
            "is_configured": config.tautulli.is_configured,
        },
        "filebot": {
            "url": config.filebot.url,
            "is_configured": config.filebot.is_configured,
        },
        "ai": {
            "enabled": config.ai.enabled,
            "has_anthropic": config.ai.has_anthropic,
            "has_openai": config.ai.has_openai,
            "ollama_url": config.ai.ollama_url,
        },
    }
