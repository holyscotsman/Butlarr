"""Settings management endpoints."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.utils.config import get_config, update_config, AppConfig
from backend.utils.constants import API

router = APIRouter()


class ServiceConfig(BaseModel):
    """Service configuration update."""
    url: Optional[str] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class AISettingsUpdate(BaseModel):
    """AI settings update."""
    enabled: Optional[bool] = None
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_url: Optional[str] = None
    assistant_enabled: Optional[bool] = None
    assistant_provider: Optional[str] = None
    assistant_model: Optional[str] = None
    curator_enabled: Optional[bool] = None
    curator_provider: Optional[str] = None
    curator_model: Optional[str] = None
    monthly_budget_limit: Optional[float] = None
    per_scan_alert_threshold: Optional[float] = None
    show_cost_estimate_before_scan: Optional[bool] = None
    use_batch_api: Optional[bool] = None


class ScanSettingsUpdate(BaseModel):
    """Scan settings update."""
    max_concurrent_files: Optional[int] = None
    adaptive_concurrency: Optional[bool] = None
    scheduled_scan_enabled: Optional[bool] = None
    scheduled_scan_cron: Optional[str] = None
    audio_sync_threshold_ms: Optional[int] = None
    integrity_check_mode: Optional[str] = None
    max_file_size_alert_gb: Optional[float] = None


class BadMovieCriteriaUpdate(BaseModel):
    """Bad movie criteria update."""
    imdb_threshold: Optional[float] = None
    rotten_tomatoes_threshold: Optional[int] = None
    require_both_ratings_bad: Optional[bool] = None
    protect_cult_classics: Optional[bool] = None
    protect_overseerr_requested: Optional[bool] = None
    protect_watched_recently_days: Optional[int] = None


def _mask_sensitive(value: str) -> str:
    """Mask a sensitive value if it exists, otherwise return empty string."""
    return API.MASK_VALUE if value else ""


@router.get("")
async def get_settings():
    """
    Get all settings with sensitive data masked.

    Sensitive fields (tokens, API keys, passwords) are replaced with '***'
    to prevent exposure. When saving, any field that is still '***' will
    be skipped to preserve the original value.
    """
    config = get_config()

    return {
        "plex": {
            "url": config.plex.url,
            "token": _mask_sensitive(config.plex.token),
            "is_configured": config.plex.is_configured,
        },
        "radarr": {
            "url": config.radarr.url,
            "api_key": _mask_sensitive(config.radarr.api_key),
            "is_configured": config.radarr.is_configured,
        },
        "sonarr": {
            "url": config.sonarr.url,
            "api_key": _mask_sensitive(config.sonarr.api_key),
            "is_configured": config.sonarr.is_configured,
        },
        # Bazarr was missing from the response - added for completeness
        "bazarr": {
            "url": config.bazarr.url,
            "api_key": _mask_sensitive(config.bazarr.api_key),
            "is_configured": config.bazarr.is_configured,
        },
        "overseerr": {
            "url": config.overseerr.url,
            "api_key": _mask_sensitive(config.overseerr.api_key),
            "is_configured": config.overseerr.is_configured,
        },
        "tautulli": {
            "url": config.tautulli.url,
            "api_key": _mask_sensitive(config.tautulli.api_key),
            "is_configured": config.tautulli.is_configured,
        },
        "filebot": {
            "url": config.filebot.url,
            "username": config.filebot.username,
            "password": _mask_sensitive(config.filebot.password),
            "is_configured": config.filebot.is_configured,
        },
        "ai": {
            "enabled": config.ai.enabled,
            "anthropic_api_key": _mask_sensitive(config.ai.anthropic_api_key),
            "openai_api_key": _mask_sensitive(config.ai.openai_api_key),
            "has_anthropic": config.ai.has_anthropic,
            "has_openai": config.ai.has_openai,
            "ollama_url": config.ai.ollama_url,
            "assistant_enabled": config.ai.assistant_enabled,
            "assistant_provider": config.ai.assistant_provider,
            "assistant_model": config.ai.assistant_model,
            "curator_enabled": config.ai.curator_enabled,
            "curator_provider": config.ai.curator_provider,
            "curator_model": config.ai.curator_model,
            "monthly_budget_limit": config.ai.monthly_budget_limit,
            "per_scan_alert_threshold": config.ai.per_scan_alert_threshold,
            "show_cost_estimate_before_scan": config.ai.show_cost_estimate_before_scan,
            "use_batch_api": config.ai.use_batch_api,
        },
        "scan": {
            "max_concurrent_files": config.scan.max_concurrent_files,
            "adaptive_concurrency": config.scan.adaptive_concurrency,
            "scheduled_scan_enabled": config.scan.scheduled_scan_enabled,
            "scheduled_scan_cron": config.scan.scheduled_scan_cron,
            "audio_sync_threshold_ms": config.scan.audio_sync_threshold_ms,
            "integrity_check_mode": config.scan.integrity_check_mode,
            "max_file_size_alert_gb": config.scan.max_file_size_alert_gb,
        },
        "bad_movie_criteria": {
            "imdb_threshold": config.bad_movie_criteria.imdb_threshold,
            "rotten_tomatoes_threshold": config.bad_movie_criteria.rotten_tomatoes_threshold,
            "require_both_ratings_bad": config.bad_movie_criteria.require_both_ratings_bad,
            "protect_cult_classics": config.bad_movie_criteria.protect_cult_classics,
            "protect_overseerr_requested": config.bad_movie_criteria.protect_overseerr_requested,
            "protect_watched_recently_days": config.bad_movie_criteria.protect_watched_recently_days,
        },
        "media_paths": config.media_paths.model_dump(),
    }


@router.put("")
async def update_all_settings(settings_data: Dict[str, Any]):
    """
    Bulk update all settings at once.

    This endpoint handles the full settings object from the frontend.
    Sensitive fields that are still masked (***) will be skipped to
    preserve their original values - this prevents the mask from being
    saved as the actual credential.

    Args:
        settings_data: Dictionary containing all settings sections

    Returns:
        Success status and message
    """
    updates = {}

    # Process each section, filtering out masked sensitive values
    # This mapping defines which fields in each section are sensitive
    sensitive_fields = {
        "plex": ["token"],
        "radarr": ["api_key"],
        "sonarr": ["api_key"],
        "bazarr": ["api_key"],
        "overseerr": ["api_key"],
        "tautulli": ["api_key"],
        "filebot": ["password"],
        "ai": ["anthropic_api_key", "openai_api_key"],
    }

    for section, data in settings_data.items():
        if not isinstance(data, dict):
            continue

        # Skip read-only computed fields
        if section in ["is_configured", "has_anthropic", "has_openai"]:
            continue

        section_updates = {}
        section_sensitive = sensitive_fields.get(section, [])

        for key, value in data.items():
            # Skip read-only computed fields
            if key in ["is_configured", "has_anthropic", "has_openai"]:
                continue

            # For sensitive fields, skip if value is the mask placeholder
            if key in section_sensitive:
                if value == API.MASK_VALUE:
                    continue  # Don't overwrite with mask

            section_updates[key] = value

        if section_updates:
            updates[section] = section_updates

    if updates:
        update_config(updates)

    return {"status": "success", "message": "All settings updated successfully"}


@router.put("/plex")
async def update_plex_settings(config_update: ServiceConfig):
    """Update Plex settings."""
    updates = {}
    if config_update.url is not None:
        updates["url"] = config_update.url
    if config_update.token is not None:
        updates["token"] = config_update.token
    
    if updates:
        update_config({"plex": updates})
    
    return {"status": "success", "message": "Plex settings updated"}


@router.put("/radarr")
async def update_radarr_settings(config_update: ServiceConfig):
    """Update Radarr settings."""
    updates = {}
    if config_update.url is not None:
        updates["url"] = config_update.url
    if config_update.api_key is not None:
        updates["api_key"] = config_update.api_key
    
    if updates:
        update_config({"radarr": updates})
    
    return {"status": "success", "message": "Radarr settings updated"}


@router.put("/sonarr")
async def update_sonarr_settings(config_update: ServiceConfig):
    """Update Sonarr settings."""
    updates = {}
    if config_update.url is not None:
        updates["url"] = config_update.url
    if config_update.api_key is not None:
        updates["api_key"] = config_update.api_key
    
    if updates:
        update_config({"sonarr": updates})
    
    return {"status": "success", "message": "Sonarr settings updated"}


@router.put("/overseerr")
async def update_overseerr_settings(config_update: ServiceConfig):
    """Update Overseerr settings."""
    updates = {}
    if config_update.url is not None:
        updates["url"] = config_update.url
    if config_update.api_key is not None:
        updates["api_key"] = config_update.api_key
    
    if updates:
        update_config({"overseerr": updates})
    
    return {"status": "success", "message": "Overseerr settings updated"}


@router.put("/tautulli")
async def update_tautulli_settings(config_update: ServiceConfig):
    """Update Tautulli settings."""
    updates = {}
    if config_update.url is not None:
        updates["url"] = config_update.url
    if config_update.api_key is not None:
        updates["api_key"] = config_update.api_key
    
    if updates:
        update_config({"tautulli": updates})
    
    return {"status": "success", "message": "Tautulli settings updated"}


@router.put("/filebot")
async def update_filebot_settings(config_update: ServiceConfig):
    """Update FileBot settings."""
    updates = {}
    if config_update.url is not None:
        updates["url"] = config_update.url
    if config_update.username is not None:
        updates["username"] = config_update.username
    if config_update.password is not None:
        updates["password"] = config_update.password
    
    if updates:
        update_config({"filebot": updates})
    
    return {"status": "success", "message": "FileBot settings updated"}


@router.put("/ai")
async def update_ai_settings(settings_update: AISettingsUpdate):
    """Update AI settings."""
    updates = settings_update.model_dump(exclude_none=True)
    
    if updates:
        update_config({"ai": updates})
    
    return {"status": "success", "message": "AI settings updated"}


@router.put("/scan")
async def update_scan_settings(settings_update: ScanSettingsUpdate):
    """Update scan settings."""
    updates = settings_update.model_dump(exclude_none=True)
    
    if updates:
        update_config({"scan": updates})
    
    return {"status": "success", "message": "Scan settings updated"}


@router.put("/bad-movie-criteria")
async def update_bad_movie_criteria(criteria_update: BadMovieCriteriaUpdate):
    """Update bad movie criteria."""
    updates = criteria_update.model_dump(exclude_none=True)
    
    if updates:
        update_config({"bad_movie_criteria": updates})
    
    return {"status": "success", "message": "Bad movie criteria updated"}


@router.get("/ai/models")
async def get_available_ai_models():
    """Get list of available AI models."""
    config = get_config()
    
    models = {
        "assistant": [],
        "curator": [],
    }
    
    # Always add "best available" option
    models["assistant"].append({
        "id": "auto",
        "name": "Best Available",
        "provider": "auto",
        "description": "Automatically selects the best available model",
    })
    models["curator"].append({
        "id": "auto",
        "name": "Best Available",
        "provider": "auto",
        "description": "Automatically selects the best available model",
    })
    
    # Anthropic models
    if config.ai.has_anthropic:
        models["assistant"].extend([
            {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5", "provider": "anthropic", "cost": "$1/$5 per 1M tokens"},
            {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5", "provider": "anthropic", "cost": "$3/$15 per 1M tokens"},
        ])
        models["curator"].extend([
            {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5", "provider": "anthropic", "cost": "$3/$15 per 1M tokens", "recommended": True},
            {"id": "claude-opus-4-5", "name": "Claude Opus 4.5", "provider": "anthropic", "cost": "$5/$25 per 1M tokens"},
        ])
    
    # OpenAI models
    if config.ai.has_openai:
        models["assistant"].extend([
            {"id": "gpt-5-nano", "name": "GPT-5 Nano", "provider": "openai", "cost": "$0.05/$0.40 per 1M tokens"},
            {"id": "gpt-5-mini", "name": "GPT-5 Mini", "provider": "openai", "cost": "$0.25/$2 per 1M tokens"},
        ])
        models["curator"].extend([
            {"id": "gpt-5-mini", "name": "GPT-5 Mini", "provider": "openai", "cost": "$0.25/$2 per 1M tokens"},
            {"id": "gpt-5", "name": "GPT-5", "provider": "openai", "cost": "$1.25/$10 per 1M tokens"},
            {"id": "o3", "name": "o3 Reasoning", "provider": "openai", "cost": "$0.40/$1.60 per 1M tokens"},
        ])
    
    # Ollama (local)
    models["assistant"].append({
        "id": "ollama",
        "name": "Ollama (Local)",
        "provider": "ollama",
        "cost": "Free",
        "description": "Requires Ollama running locally",
    })
    
    return models


@router.post("/test-service/{service}")
async def test_service_connection(service: str):
    """Test connection to a specific service."""
    config = get_config()
    
    service_map = {
        "plex": ("plex", config.plex),
        "radarr": ("radarr", config.radarr),
        "sonarr": ("sonarr", config.sonarr),
        "overseerr": ("overseerr", config.overseerr),
        "tautulli": ("tautulli", config.tautulli),
        "filebot": ("filebot", config.filebot),
    }
    
    if service not in service_map:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    
    service_name, service_config = service_map[service]
    
    if not service_config.is_configured:
        return {"success": False, "message": f"{service_name.title()} is not configured"}
    
    # Import and test
    try:
        if service == "plex":
            from backend.core.integrations.plex import PlexClient
            client = PlexClient(service_config.url, service_config.token)
            await client.get_server_info()
        elif service == "radarr":
            from backend.core.integrations.radarr import RadarrClient
            client = RadarrClient(service_config.url, service_config.api_key)
            await client.get_system_status()
        elif service == "sonarr":
            from backend.core.integrations.sonarr import SonarrClient
            client = SonarrClient(service_config.url, service_config.api_key)
            await client.get_system_status()
        elif service == "overseerr":
            from backend.core.integrations.overseerr import OverseerrClient
            client = OverseerrClient(service_config.url, service_config.api_key)
            await client.get_status()
        elif service == "tautulli":
            from backend.core.integrations.tautulli import TautulliClient
            client = TautulliClient(service_config.url, service_config.api_key)
            await client.get_server_info()
        elif service == "filebot":
            from backend.core.integrations.filebot import FileBotClient
            client = FileBotClient(service_config.url, service_config.username, service_config.password)
            await client.get_status()
        
        return {"success": True, "message": f"Connected to {service_name.title()}"}
    
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}
