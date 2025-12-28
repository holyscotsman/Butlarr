"""
Butlarr Configuration Management
Handles all application settings and environment variables
"""

import os
import json
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class PlexConfig(BaseModel):
    """Plex server configuration."""
    url: str = ""
    token: str = ""
    
    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.token)


class RadarrConfig(BaseModel):
    """Radarr configuration."""
    url: str = ""
    api_key: str = ""
    
    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.api_key)


class SonarrConfig(BaseModel):
    """Sonarr configuration."""
    url: str = ""
    api_key: str = ""
    
    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.api_key)


class BazarrConfig(BaseModel):
    """Bazarr configuration."""
    url: str = ""
    api_key: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.api_key)


class OverseerrConfig(BaseModel):
    """Overseerr configuration."""
    url: str = ""
    api_key: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.api_key)


class TautulliConfig(BaseModel):
    """Tautulli configuration."""
    url: str = ""
    api_key: str = ""
    enabled: bool = False  # Disabled by default for privacy
    
    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.api_key)


class FileBotConfig(BaseModel):
    """FileBot Node configuration."""
    url: str = ""
    username: str = ""
    password: str = ""
    
    @property
    def is_configured(self) -> bool:
        return bool(self.url)


class AIConfig(BaseModel):
    """AI provider configuration."""
    enabled: bool = True
    
    # Anthropic
    anthropic_api_key: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    
    # Ollama (local)
    ollama_url: str = "http://host.docker.internal:11434"
    
    # Assistant Chat settings
    assistant_enabled: bool = True
    assistant_provider: str = "best_available"
    assistant_model: str = "auto"
    
    # AI Curator settings
    curator_enabled: bool = True
    curator_provider: str = "best_available"
    curator_model: str = "auto"
    
    # Cost controls
    monthly_budget_limit: float = 10.00
    per_scan_alert_threshold: float = 0.10
    show_cost_estimate_before_scan: bool = True
    use_batch_api: bool = False
    
    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)
    
    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)


class MediaPaths(BaseModel):
    """Media folder paths configuration."""
    root: str = "/media"
    movies: str = "/media/Movies"
    tv: str = "/media/TV"
    anime: str = "/media/Anime"
    anime18: str = "/media/Anime18"
    cartoons: str = "/media/Cartoons"
    game_shows: str = "/media/Game Shows"
    music: str = "/media/Music"
    books: str = "/media/Books"
    home_videos: str = "/media/Home Videos"


class ScanConfig(BaseModel):
    """Scan configuration settings."""
    max_concurrent_files: int = 4
    adaptive_concurrency: bool = True
    
    scheduled_scan_enabled: bool = False
    scheduled_scan_cron: str = "0 3 * * 0"
    
    audio_sync_threshold_ms: int = 40
    integrity_check_mode: str = "full"
    
    file_size_thresholds: Dict[str, Dict[str, float]] = {
        "4k_hdr": {"min": 8.0, "max": 25.0},
        "4k_sdr": {"min": 6.0, "max": 20.0},
        "1080p": {"min": 2.0, "max": 10.0},
        "720p": {"min": 1.0, "max": 5.0},
        "480p": {"min": 0.5, "max": 2.0},
    }
    
    max_file_size_alert_gb: float = 40.0


class BadMovieCriteria(BaseModel):
    """Criteria for identifying bad movies."""
    imdb_threshold: float = 5.0
    rotten_tomatoes_threshold: int = 30
    require_both_ratings_bad: bool = True
    protect_cult_classics: bool = True
    protect_overseerr_requested: bool = True
    protect_watched_recently_days: int = 0


class Settings(BaseSettings):
    """Main application settings from environment."""
    app_name: str = "Butlarr"
    app_version: str = "2512.0.3"
    app_env: str = "production"
    debug: bool = False
    
    database_url: str = "sqlite+aiosqlite:///./data/butlarr.db"
    
    data_dir: Path = Path("/app/data")
    log_dir: Path = Path("/app/data/logs")
    cache_dir: Path = Path("/app/data/cache")
    
    # Service configurations (from environment)
    plex_url: str = ""
    plex_token: str = ""
    radarr_url: str = ""
    radarr_api_key: str = ""
    sonarr_url: str = ""
    sonarr_api_key: str = ""
    bazarr_url: str = ""
    bazarr_api_key: str = ""
    overseerr_url: str = ""
    overseerr_api_key: str = ""
    tautulli_url: str = ""
    tautulli_api_key: str = ""
    filebot_url: str = ""
    filebot_user: str = ""
    filebot_pass: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ollama_url: str = "http://host.docker.internal:11434"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class AppConfig(BaseModel):
    """Complete application configuration (stored in JSON)."""
    setup_complete: bool = False
    
    plex: PlexConfig = PlexConfig()
    radarr: RadarrConfig = RadarrConfig()
    sonarr: SonarrConfig = SonarrConfig()
    bazarr: BazarrConfig = BazarrConfig()
    overseerr: OverseerrConfig = OverseerrConfig()
    tautulli: TautulliConfig = TautulliConfig()
    filebot: FileBotConfig = FileBotConfig()
    
    ai: AIConfig = AIConfig()
    media_paths: MediaPaths = MediaPaths()
    scan: ScanConfig = ScanConfig()
    bad_movie_criteria: BadMovieCriteria = BadMovieCriteria()
    
    ignored_bad_movies: List[str] = []
    ignored_recommendations: List[str] = []


# Thread-safe singleton
_settings_instance: Optional[Settings] = None
_settings_lock = threading.Lock()

_config_instance: Optional[AppConfig] = None
_config_lock = threading.Lock()


def get_settings() -> Settings:
    """Get cached application settings from environment (thread-safe)."""
    global _settings_instance
    
    if _settings_instance is None:
        with _settings_lock:
            if _settings_instance is None:
                _settings_instance = Settings()
    
    return _settings_instance


def get_config_path() -> Path:
    """Get path to config file."""
    settings = get_settings()
    return settings.data_dir / "config.json"


def load_config() -> AppConfig:
    """Load application configuration from file."""
    config_path = get_config_path()
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
            return AppConfig(**data)
        except Exception:
            pass
    
    # Return default config with environment values applied
    settings = get_settings()
    config = AppConfig()
    
    # Apply environment values
    config.plex.url = settings.plex_url
    config.plex.token = settings.plex_token
    config.radarr.url = settings.radarr_url
    config.radarr.api_key = settings.radarr_api_key
    config.sonarr.url = settings.sonarr_url
    config.sonarr.api_key = settings.sonarr_api_key
    config.overseerr.url = settings.overseerr_url
    config.overseerr.api_key = settings.overseerr_api_key
    config.tautulli.url = settings.tautulli_url
    config.tautulli.api_key = settings.tautulli_api_key
    config.filebot.url = settings.filebot_url
    config.filebot.username = settings.filebot_user
    config.filebot.password = settings.filebot_pass
    config.ai.anthropic_api_key = settings.anthropic_api_key
    config.ai.openai_api_key = settings.openai_api_key
    config.ai.ollama_url = settings.ollama_url
    
    return config


def save_config(config: AppConfig) -> None:
    """Save application configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config.model_dump(), f, indent=2, default=str)


def get_config() -> AppConfig:
    """Get current application configuration (thread-safe)."""
    global _config_instance
    
    if _config_instance is None:
        with _config_lock:
            if _config_instance is None:
                _config_instance = load_config()
    
    return _config_instance


def update_config(updates: Dict[str, Any]) -> AppConfig:
    """Update configuration with new values (thread-safe)."""
    global _config_instance
    
    with _config_lock:
        config = get_config()
        
        config_dict = config.model_dump()
        _deep_merge(config_dict, updates)
        
        _config_instance = AppConfig(**config_dict)
        save_config(_config_instance)
        
    return _config_instance


def reload_config() -> AppConfig:
    """Force reload configuration from disk."""
    global _config_instance
    
    with _config_lock:
        _config_instance = load_config()
    
    return _config_instance


def _deep_merge(base: dict, updates: dict) -> None:
    """Deep merge updates into base dict."""
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
