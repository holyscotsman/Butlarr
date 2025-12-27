"""API Routes package."""

from . import (
    scan,
    settings,
    issues,
    recommendations,
    bad_movies,
    dashboard,
    activity,
    health,
    report,
    websocket_routes,
    system_routes,
)

__all__ = [
    "scan",
    "settings",
    "issues",
    "recommendations",
    "bad_movies",
    "dashboard",
    "activity",
    "health",
    "report",
    "websocket_routes",
    "system_routes",
]
