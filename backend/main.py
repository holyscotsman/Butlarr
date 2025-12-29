"""Butlarr - AI-Powered Plex Library Manager."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog

from backend.db.database import init_db
from backend.utils.config import get_config
from backend.utils.logging import setup_logging
from backend.core.websocket_manager import WebSocketManager
from backend.core.scanner.manager import ScanManager
from backend.utils.version import VERSION

# Import routes
from backend.api.routes import (
    scan,
    settings,
    setup,
    issues,
    recommendations,
    bad_movies,
    dashboard,
    activity,
    health,
    report,
    websocket_routes,
    system_routes,
    ai_chat,
    storage,
    embedded_ai,
)

# Setup logging first
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Butlarr", version=VERSION)
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize WebSocket manager
    app.state.ws_manager = WebSocketManager()
    
    # Initialize scan manager
    app.state.scan_manager = ScanManager(app.state.ws_manager)
    
    # Load configuration
    config = get_config()
    logger.info("Configuration loaded", 
                plex_configured=config.plex.is_configured,
                ai_enabled=config.ai.enabled)
    
    yield
    
    # Cleanup
    logger.info("Shutting down Butlarr")


# Create FastAPI app
app = FastAPI(
    title="Butlarr",
    description="AI-Powered Plex Library Manager",
    version=VERSION,
    lifespan=lifespan,
)

# CORS middleware - Configure allowed origins from environment or use permissive defaults
# For Docker deployments, we allow all origins since the app is typically accessed
# via various IPs (localhost, LAN IP, Docker network IP, etc.)
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else []

# If CORS_ORIGINS env var is set to "*", allow all origins
allow_all_origins = os.environ.get("CORS_ORIGINS") == "*" or not CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(scan.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(setup.router, prefix="/api/setup")
app.include_router(issues.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(bad_movies.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(activity.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(ai_chat.router, prefix="/api")
app.include_router(system_routes.router, prefix="/api")
app.include_router(storage.router, prefix="/api/storage")
app.include_router(embedded_ai.router, prefix="/api")
app.include_router(websocket_routes.router, prefix="/ws")


# Health check at root /api level
@app.get("/api/health")
async def root_health_check():
    """Health check endpoint."""
    from datetime import datetime
    return {
        "status": "healthy",
        "version": VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Serve frontend static files
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """Serve frontend SPA."""
        if path.startswith("api/") or path.startswith("ws/"):
            return {"detail": "Not found"}
        
        file_path = frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        return FileResponse(str(frontend_dist / "index.html"))
else:
    logger.warning("Frontend dist not found", path=str(frontend_dist))
    
    @app.get("/")
    async def root():
        return {
            "message": "Butlarr API",
            "version": VERSION,
            "docs": "/docs",
            "note": "Frontend not built. Run: cd frontend && npm install && npm run build"
        }
