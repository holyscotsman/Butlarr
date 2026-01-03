"""
Butlarr Database Management
Handles database initialization, sessions, and migrations
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event, text

from backend.db.models import Base
from backend.utils.config import get_settings

import structlog

logger = structlog.get_logger(__name__)

# Database engine and session factory (initialized lazily)
_engine = None
_async_session_factory = None
_lock = asyncio.Lock()


def get_db_path() -> Path:
    """Get the path to the SQLite database file."""
    settings = get_settings()
    return settings.data_dir / "butlarr.db"


def get_database_url() -> str:
    """Get the database URL."""
    db_path = get_db_path()
    return f"sqlite+aiosqlite:///{db_path}"


async def get_engine():
    """Get or create the database engine (thread-safe)."""
    global _engine
    
    async with _lock:
        if _engine is None:
            _engine = create_async_engine(
                get_database_url(),
                echo=False,
                future=True,
                pool_pre_ping=True,
                connect_args={"check_same_thread": False}
            )
            
            # Enable WAL mode for better concurrent access
            @event.listens_for(_engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=-64000")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.close()
            
            logger.info("Database engine created", url=get_database_url())
    
    return _engine


async def get_session_factory():
    """Get or create the async session factory (thread-safe)."""
    global _async_session_factory
    
    async with _lock:
        if _async_session_factory is None:
            engine = await get_engine()
            _async_session_factory = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            logger.info("Session factory created")
    
    return _async_session_factory


async def init_db() -> None:
    """Initialize the database, creating tables if they don't exist."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = await get_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run migrations to add any missing columns
    await _run_migrations(engine)

    logger.info("Database initialized", path=str(db_path))


async def _run_migrations(engine) -> None:
    """Add missing columns to existing tables (SQLite-compatible migrations)."""
    migrations = [
        # Movie watch tracking columns (v2512.1.5)
        ("movies", "is_watched", "BOOLEAN DEFAULT 0"),
        ("movies", "last_watched_at", "DATETIME"),
        ("movies", "watch_count", "INTEGER DEFAULT 0"),
    ]

    async with engine.begin() as conn:
        for table, column, column_def in migrations:
            try:
                # Check if column exists
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM pragma_table_info('{table}') WHERE name = '{column}'")
                )
                exists = result.scalar() > 0

                if not exists:
                    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}"))
                    logger.info("Added migration column", table=table, column=column)
            except Exception as e:
                # Column might already exist or table doesn't exist yet
                logger.debug("Migration skipped", table=table, column=column, reason=str(e))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database sessions.
    
    IMPORTANT: This does NOT auto-commit. Routes must explicitly call:
    - await db.commit() to save changes
    - await db.rollback() to discard changes
    """
    session_factory = await get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions (for use outside of FastAPI routes).
    """
    session_factory = await get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Close the database engine."""
    global _engine, _async_session_factory
    
    async with _lock:
        if _engine:
            await _engine.dispose()
            _engine = None
            _async_session_factory = None
            logger.info("Database connection closed")
