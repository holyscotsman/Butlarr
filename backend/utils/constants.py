"""
Centralized constants for Butlarr.

This module contains all magic numbers and configuration values
that are used across the application. Having them in one place:
- Makes it easy to adjust values
- Documents what each value is for
- Prevents duplication and inconsistency

Usage:
    from backend.utils.constants import TIMEOUTS, PATHS
"""

from pathlib import Path
import os


# ============================================================================
# Timeout Configuration (in seconds)
# ============================================================================

class TIMEOUTS:
    """
    HTTP and subprocess timeout values.

    All timeouts are in seconds unless otherwise noted.
    """

    # HTTP client timeouts for external service connections
    HTTP_DEFAULT = 10.0          # Default timeout for most HTTP requests
    HTTP_QUICK = 5.0             # Quick health checks
    HTTP_EXTENDED = 30.0         # Operations that may take longer (file transfers)

    # Git operations
    GIT_FETCH = 30               # git fetch from remote
    GIT_PULL = 120               # git pull (may need to download files)

    # Dependency installation
    PIP_INSTALL = 300            # pip install (may download large packages)

    # Scan operations
    SCAN_FILE = 60               # Timeout per file during scanning
    SCAN_BATCH = 600             # Timeout for entire batch operation

    # AI operations
    AI_INFERENCE_LOCAL = 120     # Local model inference (can be slow)
    AI_INFERENCE_CLOUD = 60      # Cloud API calls

    # WebSocket
    WS_HEARTBEAT = 30            # Heartbeat interval


# ============================================================================
# Path Configuration
# ============================================================================

class PATHS:
    """
    Standard file and directory paths.

    These can be overridden by environment variables or config.
    The values here are defaults that work in the Docker container.
    """

    # Base directories - can be overridden by DATA_DIR env var
    APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
    DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))

    # Subdirectories under DATA_DIR
    @classmethod
    def logs_dir(cls) -> Path:
        return cls.DATA_DIR / "logs"

    @classmethod
    def cache_dir(cls) -> Path:
        return cls.DATA_DIR / "cache"

    @classmethod
    def models_dir(cls) -> Path:
        return cls.DATA_DIR / "models"

    @classmethod
    def config_file(cls) -> Path:
        return cls.DATA_DIR / "config.json"

    @classmethod
    def log_file(cls) -> Path:
        return cls.logs_dir() / "butlarr.log"

    @classmethod
    def database_file(cls) -> Path:
        return cls.DATA_DIR / "butlarr.db"

    # Embedded AI model path
    EMBEDDED_MODEL_FILENAME = "qwen2.5-1.5b-instruct.Q4_K_M.gguf"

    @classmethod
    def embedded_model_path(cls) -> Path:
        return cls.models_dir() / cls.EMBEDDED_MODEL_FILENAME

    # Git directory (may not exist in Docker images)
    @classmethod
    def git_dir(cls) -> Path:
        return cls.APP_ROOT / ".git"

    # Restart request file (used by entrypoint.sh)
    @classmethod
    def restart_file(cls) -> Path:
        return cls.DATA_DIR / ".restart_requested"


# ============================================================================
# API Configuration
# ============================================================================

class API:
    """
    API-related constants.
    """

    # Sensitive field masking
    MASK_VALUE = "***"

    # Pagination defaults
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 500

    # Activity log defaults
    DEFAULT_ACTIVITY_DAYS = 7
    DEFAULT_ACTIVITY_LIMIT = 100


# ============================================================================
# Scan Configuration
# ============================================================================

class SCAN:
    """
    Media scanning constants.
    """

    # Valid phase numbers for the 17-phase scan
    VALID_PHASES = set(range(1, 18))

    # Default concurrency
    DEFAULT_CONCURRENT_FILES = 4
    MAX_CONCURRENT_FILES = 16

    # File size thresholds (in GB) for quality detection
    SIZE_THRESHOLDS = {
        "4k_hdr": {"min": 8.0, "max": 25.0},
        "4k_sdr": {"min": 6.0, "max": 20.0},
        "1080p": {"min": 2.0, "max": 10.0},
        "720p": {"min": 1.0, "max": 5.0},
        "480p": {"min": 0.5, "max": 2.0},
    }


# ============================================================================
# WebSocket Configuration
# ============================================================================

class WEBSOCKET:
    """
    WebSocket connection constants.
    """

    MAX_RECONNECT_ATTEMPTS = 10
    RECONNECT_DELAY_MS = 1000
    HEARTBEAT_INTERVAL_MS = 30000
