"""
Centralized version management for Butlarr.

This module provides a single source of truth for the application version.
The version is read from the VERSION file at the project root.

Usage:
    from backend.utils.version import VERSION, BUILD_DATE

Note: All version strings throughout the codebase should import from here
rather than hardcoding values. This ensures consistency across:
- API responses
- Logging
- System info endpoints
- Frontend display (via API)
"""

import os
from pathlib import Path
from datetime import datetime

# Determine the project root directory
# In Docker: /app, in development: parent of backend directory
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# Try to read version from VERSION file
_VERSION_FILE = _PROJECT_ROOT / "VERSION"

def _read_version() -> str:
    """Read version from VERSION file, with fallback."""
    try:
        if _VERSION_FILE.exists():
            return _VERSION_FILE.read_text().strip()
    except Exception:
        pass

    # Fallback for Docker where path might differ
    docker_version_file = Path("/app/VERSION")
    try:
        if docker_version_file.exists():
            return docker_version_file.read_text().strip()
    except Exception:
        pass

    # Last resort fallback
    return "2512.1.3"


# Public API - single source of truth for version
VERSION = _read_version()

# Build date - can be set via environment variable during Docker build
# Format: YYYY-MM-DD
BUILD_DATE = os.environ.get("BUILD_DATE", datetime.now().strftime("%Y-%m-%d"))


def get_version_info() -> dict:
    """
    Get complete version information dictionary.

    Returns:
        dict with version, build_date, and source information
    """
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "version_file": str(_VERSION_FILE) if _VERSION_FILE.exists() else None,
    }
