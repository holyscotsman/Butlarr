"""
Butlarr Database Models
SQLAlchemy models for all data persistence
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class MediaType(str, Enum):
    """Types of media."""
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    TV_EPISODE = "tv_episode"
    ANIME = "anime"
    ANIME18 = "anime18"
    CARTOON = "cartoon"
    GAME_SHOW = "game_show"
    MUSIC = "music"
    OTHER = "other"


class IssueType(str, Enum):
    """Types of issues that can be detected."""
    CORRUPT_FILE = "corrupt_file"
    AUDIO_SYNC = "audio_sync"
    MISSING_AUDIO = "missing_audio"
    MISSING_SUBTITLE = "missing_subtitle"
    SUBTITLE_TIMING = "subtitle_timing"
    HDR_METADATA = "hdr_metadata"
    WRONG_LANGUAGE = "wrong_language"
    OVERSIZED_FILE = "oversized_file"
    UNDERSIZED_FILE = "undersized_file"
    DUPLICATE_FILE = "duplicate_file"
    BAD_NAMING = "bad_naming"
    MISSING_COLLECTION = "missing_collection"
    OUTDATED_CODEC = "outdated_codec"
    LOW_QUALITY = "low_quality"


class IssueSeverity(str, Enum):
    """Severity levels for issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ScanStatus(str, Enum):
    """Status of a scan."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(str, Enum):
    """Types of actions that can be logged."""
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    SCAN_FAILED = "scan_failed"
    MOVIE_DELETED = "movie_deleted"
    MOVIE_IGNORED = "movie_ignored"
    RECOMMENDATION_REQUESTED = "recommendation_requested"
    RECOMMENDATION_IGNORED = "recommendation_ignored"
    FILE_RENAMED = "file_renamed"
    FILE_MOVED = "file_moved"
    DUPLICATE_REMOVED = "duplicate_removed"
    ISSUE_RESOLVED = "issue_resolved"
    SETTINGS_CHANGED = "settings_changed"
    AI_QUERY = "ai_query"


# =============================================================================
# Media Models
# =============================================================================

class Movie(Base):
    """Movie metadata from Plex."""
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True)
    plex_rating_key = Column(String(50), unique=True, nullable=False, index=True)
    
    # Basic info
    title = Column(String(500), nullable=False)
    year = Column(Integer)
    sort_title = Column(String(500))
    original_title = Column(String(500))
    tagline = Column(String(1000))
    summary = Column(Text)
    
    # Ratings
    imdb_id = Column(String(20), index=True)
    tmdb_id = Column(Integer, index=True)
    imdb_rating = Column(Float)
    rotten_tomatoes_rating = Column(Integer)
    audience_rating = Column(Float)
    critic_rating = Column(Float)
    
    # Technical
    duration_ms = Column(Integer)  # Runtime in milliseconds
    content_rating = Column(String(20))  # PG-13, R, etc.
    studio = Column(String(200))
    
    # Genres and tags
    genres = Column(JSON)  # List of genre strings
    tags = Column(JSON)  # List of tag strings
    
    # Collection info
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=True)
    collection_order = Column(Integer)
    
    # File info (primary file)
    file_path = Column(String(2000))
    file_size_bytes = Column(Integer)
    container = Column(String(20))  # mkv, mp4, etc.
    video_codec = Column(String(50))
    audio_codec = Column(String(50))
    resolution = Column(String(20))  # 4k, 1080p, 720p, etc.
    is_hdr = Column(Boolean, default=False)
    hdr_type = Column(String(50))  # HDR10, Dolby Vision, etc.
    bitrate = Column(Integer)
    
    # Status flags
    is_bad_movie = Column(Boolean, default=False)
    bad_movie_score = Column(Float)
    is_ignored = Column(Boolean, default=False)
    is_overseerr_requested = Column(Boolean, default=False)
    is_cult_classic = Column(Boolean, default=False)
    
    # Timestamps
    added_at = Column(DateTime, default=func.now())
    last_scanned = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    collection = relationship("Collection", back_populates="movies")
    files = relationship("MediaFile", back_populates="movie", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="movie", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_movie_ratings", "imdb_rating", "rotten_tomatoes_rating"),
        Index("idx_movie_status", "is_bad_movie", "is_ignored"),
    )


class TVShow(Base):
    """TV Show metadata from Plex."""
    __tablename__ = "tv_shows"
    
    id = Column(Integer, primary_key=True)
    plex_rating_key = Column(String(50), unique=True, nullable=False, index=True)
    
    # Basic info
    title = Column(String(500), nullable=False)
    sort_title = Column(String(500))
    original_title = Column(String(500))
    year = Column(Integer)
    summary = Column(Text)
    
    # IDs
    tvdb_id = Column(Integer, index=True)
    tmdb_id = Column(Integer, index=True)
    imdb_id = Column(String(20), index=True)
    
    # Ratings
    imdb_rating = Column(Float)
    
    # Content
    content_rating = Column(String(20))
    studio = Column(String(200))
    network = Column(String(200))
    genres = Column(JSON)
    tags = Column(JSON)
    
    # Show type
    media_type = Column(SQLEnum(MediaType), default=MediaType.TV_SHOW)
    
    # Status
    status = Column(String(50))  # Continuing, Ended, etc.
    total_seasons = Column(Integer, default=0)
    total_episodes = Column(Integer, default=0)
    
    # Flags
    is_ignored = Column(Boolean, default=False)
    is_overseerr_requested = Column(Boolean, default=False)
    
    # Timestamps
    added_at = Column(DateTime, default=func.now())
    last_scanned = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    seasons = relationship("TVSeason", back_populates="show", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="tv_show", cascade="all, delete-orphan")


class TVSeason(Base):
    """TV Season metadata."""
    __tablename__ = "tv_seasons"
    
    id = Column(Integer, primary_key=True)
    plex_rating_key = Column(String(50), unique=True, nullable=False, index=True)
    show_id = Column(Integer, ForeignKey("tv_shows.id"), nullable=False)
    
    season_number = Column(Integer, nullable=False)
    title = Column(String(500))
    summary = Column(Text)
    episode_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    show = relationship("TVShow", back_populates="seasons")
    episodes = relationship("TVEpisode", back_populates="season", cascade="all, delete-orphan")


class TVEpisode(Base):
    """TV Episode metadata."""
    __tablename__ = "tv_episodes"
    
    id = Column(Integer, primary_key=True)
    plex_rating_key = Column(String(50), unique=True, nullable=False, index=True)
    season_id = Column(Integer, ForeignKey("tv_seasons.id"), nullable=False)
    
    episode_number = Column(Integer, nullable=False)
    title = Column(String(500))
    summary = Column(Text)
    duration_ms = Column(Integer)
    
    # File info
    file_path = Column(String(2000))
    file_size_bytes = Column(Integer)
    container = Column(String(20))
    video_codec = Column(String(50))
    audio_codec = Column(String(50))
    resolution = Column(String(20))
    
    # Timestamps
    aired_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    season = relationship("TVSeason", back_populates="episodes")
    files = relationship("MediaFile", back_populates="episode", cascade="all, delete-orphan")


class Collection(Base):
    """Movie collections (franchises, series)."""
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True)
    plex_rating_key = Column(String(50), unique=True, index=True)
    
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    tmdb_id = Column(Integer, index=True)
    
    # Completeness tracking
    total_movies_expected = Column(Integer)
    total_movies_owned = Column(Integer, default=0)
    is_complete = Column(Boolean, default=False)
    missing_movies = Column(JSON)  # List of missing movie info
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    movies = relationship("Movie", back_populates="collection")


class MediaFile(Base):
    """Individual media files (for duplicate tracking)."""
    __tablename__ = "media_files"
    
    id = Column(Integer, primary_key=True)
    
    # Link to parent (one of these will be set)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)
    episode_id = Column(Integer, ForeignKey("tv_episodes.id"), nullable=True)
    
    # File info
    file_path = Column(String(2000), nullable=False, unique=True)
    file_name = Column(String(500))
    file_size_bytes = Column(Integer)
    
    # Technical details
    container = Column(String(20))
    video_codec = Column(String(50))
    video_profile = Column(String(50))
    audio_codec = Column(String(50))
    audio_channels = Column(Integer)
    resolution = Column(String(20))
    resolution_width = Column(Integer)
    resolution_height = Column(Integer)
    bitrate = Column(Integer)
    duration_ms = Column(Integer)
    
    # HDR info
    is_hdr = Column(Boolean, default=False)
    hdr_type = Column(String(50))
    color_space = Column(String(50))
    
    # Language info
    audio_languages = Column(JSON)  # List of language codes
    subtitle_languages = Column(JSON)  # List of language codes
    
    # Quality score (calculated)
    quality_score = Column(Float)
    is_primary = Column(Boolean, default=False)  # Main file for this media
    is_duplicate = Column(Boolean, default=False)
    
    # Integrity
    is_corrupt = Column(Boolean, default=False)
    integrity_checked_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    movie = relationship("Movie", back_populates="files")
    episode = relationship("TVEpisode", back_populates="files")
    
    __table_args__ = (
        Index("idx_file_quality", "quality_score", "is_primary"),
        Index("idx_file_duplicate", "movie_id", "is_duplicate"),
    )


# =============================================================================
# Issue & Recommendation Models
# =============================================================================

class Issue(Base):
    """Detected issues with media files."""
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True)
    
    # Link to media (one of these will be set)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)
    tv_show_id = Column(Integer, ForeignKey("tv_shows.id"), nullable=True)
    file_path = Column(String(2000))
    
    # Issue details
    issue_type = Column(SQLEnum(IssueType), nullable=False)
    severity = Column(SQLEnum(IssueSeverity), default=IssueSeverity.WARNING)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    details = Column(JSON)  # Additional structured data
    
    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    # Auto-fix capability
    can_auto_fix = Column(Boolean, default=False)
    auto_fix_action = Column(String(100))
    
    # Timestamps
    detected_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    movie = relationship("Movie", back_populates="issues")
    tv_show = relationship("TVShow", back_populates="issues")
    
    __table_args__ = (
        Index("idx_issue_type_severity", "issue_type", "severity"),
        Index("idx_issue_resolved", "is_resolved"),
    )


class Recommendation(Base):
    """AI-generated recommendations for new content."""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True)
    
    # Content info
    media_type = Column(SQLEnum(MediaType), nullable=False)
    title = Column(String(500), nullable=False)
    year = Column(Integer)
    
    # External IDs
    tmdb_id = Column(Integer, index=True)
    tvdb_id = Column(Integer, index=True)
    imdb_id = Column(String(20))
    
    # Recommendation details
    reason = Column(Text)  # Why this was recommended
    confidence_score = Column(Float)
    ai_model_used = Column(String(100))
    
    # Ratings
    imdb_rating = Column(Float)
    rotten_tomatoes_rating = Column(Integer)
    
    # Poster/artwork URL
    poster_url = Column(String(1000))
    backdrop_url = Column(String(1000))
    
    # Status
    is_ignored = Column(Boolean, default=False)
    is_requested = Column(Boolean, default=False)
    requested_at = Column(DateTime)
    is_added = Column(Boolean, default=False)  # Now in library
    added_at = Column(DateTime)
    
    # Timestamps
    generated_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint("media_type", "tmdb_id", name="uq_recommendation_tmdb"),
        Index("idx_rec_status", "is_ignored", "is_requested", "is_added"),
    )


class BadMovieSuggestion(Base):
    """AI-suggested movies for removal."""
    __tablename__ = "bad_movie_suggestions"
    
    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False, unique=True)
    
    # Scoring
    bad_score = Column(Float, nullable=False)  # Higher = worse
    imdb_rating = Column(Float)
    rotten_tomatoes_rating = Column(Integer)
    
    # AI reasoning
    reason = Column(Text)
    ai_model_used = Column(String(100))
    
    # Status
    is_ignored = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
    
    # Timestamps
    suggested_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    movie = relationship("Movie")


# =============================================================================
# Scan & Activity Models
# =============================================================================

class Scan(Base):
    """Scan history and progress tracking."""
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True)
    
    # Status
    status = Column(SQLEnum(ScanStatus), default=ScanStatus.PENDING)
    current_phase = Column(Integer, default=0)
    total_phases = Column(Integer, default=17)
    phase_name = Column(String(100))
    
    # Progress
    current_item = Column(String(500))
    items_processed = Column(Integer, default=0)
    items_total = Column(Integer, default=0)
    progress_percent = Column(Float, default=0.0)
    
    # Statistics
    movies_scanned = Column(Integer, default=0)
    tv_shows_scanned = Column(Integer, default=0)
    episodes_scanned = Column(Integer, default=0)
    issues_found = Column(Integer, default=0)
    files_renamed = Column(Integer, default=0)
    duplicates_found = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    elapsed_seconds = Column(Integer)
    estimated_remaining_seconds = Column(Integer)
    
    # AI costs
    ai_tokens_used = Column(Integer, default=0)
    ai_cost_usd = Column(Float, default=0.0)
    
    # Error tracking
    error_message = Column(Text)
    error_traceback = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Activity(Base):
    """Activity log for all actions."""
    __tablename__ = "activity"
    
    id = Column(Integer, primary_key=True)
    
    action_type = Column(SQLEnum(ActionType), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    details = Column(JSON)  # Additional structured data
    
    # Related entities
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=True)
    tv_show_id = Column(Integer, ForeignKey("tv_shows.id"), nullable=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index("idx_activity_type_date", "action_type", "created_at"),
    )


class AIUsage(Base):
    """Track AI API usage and costs."""
    __tablename__ = "ai_usage"
    
    id = Column(Integer, primary_key=True)
    
    # Provider info
    provider = Column(String(50), nullable=False)  # anthropic, openai, ollama
    model = Column(String(100), nullable=False)
    
    # Usage
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Cost
    cost_usd = Column(Float, default=0.0)
    
    # Context
    purpose = Column(String(100))  # assistant, curator, etc.
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index("idx_ai_usage_provider", "provider", "created_at"),
        Index("idx_ai_usage_month", "created_at"),
    )
