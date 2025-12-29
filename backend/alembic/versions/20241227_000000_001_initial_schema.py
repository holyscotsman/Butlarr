"""Initial schema - Butlarr v2512.1.0

Revision ID: 001
Revises: None
Create Date: 2024-12-27

This migration creates the initial database schema for Butlarr.
All tables are created from scratch for new installations.
For existing installations, this migration will be marked as applied
since the tables already exist via SQLAlchemy create_all().
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create collections table
    op.create_table(
        'collections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plex_rating_key', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('tmdb_id', sa.Integer(), nullable=True),
        sa.Column('total_movies_expected', sa.Integer(), nullable=True),
        sa.Column('total_movies_owned', sa.Integer(), nullable=True),
        sa.Column('is_complete', sa.Boolean(), nullable=True),
        sa.Column('missing_movies', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_collections_plex_rating_key', 'collections', ['plex_rating_key'], unique=True)
    op.create_index('ix_collections_tmdb_id', 'collections', ['tmdb_id'], unique=False)

    # Create movies table
    op.create_table(
        'movies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plex_rating_key', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('sort_title', sa.String(length=500), nullable=True),
        sa.Column('original_title', sa.String(length=500), nullable=True),
        sa.Column('tagline', sa.String(length=1000), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('imdb_id', sa.String(length=20), nullable=True),
        sa.Column('tmdb_id', sa.Integer(), nullable=True),
        sa.Column('imdb_rating', sa.Float(), nullable=True),
        sa.Column('rotten_tomatoes_rating', sa.Integer(), nullable=True),
        sa.Column('audience_rating', sa.Float(), nullable=True),
        sa.Column('critic_rating', sa.Float(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('content_rating', sa.String(length=20), nullable=True),
        sa.Column('studio', sa.String(length=200), nullable=True),
        sa.Column('genres', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('collection_id', sa.Integer(), nullable=True),
        sa.Column('collection_order', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(length=2000), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('container', sa.String(length=20), nullable=True),
        sa.Column('video_codec', sa.String(length=50), nullable=True),
        sa.Column('audio_codec', sa.String(length=50), nullable=True),
        sa.Column('resolution', sa.String(length=20), nullable=True),
        sa.Column('is_hdr', sa.Boolean(), nullable=True),
        sa.Column('hdr_type', sa.String(length=50), nullable=True),
        sa.Column('bitrate', sa.Integer(), nullable=True),
        sa.Column('is_bad_movie', sa.Boolean(), nullable=True),
        sa.Column('bad_movie_score', sa.Float(), nullable=True),
        sa.Column('is_ignored', sa.Boolean(), nullable=True),
        sa.Column('is_overseerr_requested', sa.Boolean(), nullable=True),
        sa.Column('is_cult_classic', sa.Boolean(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.Column('last_scanned', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_movie_ratings', 'movies', ['imdb_rating', 'rotten_tomatoes_rating'], unique=False)
    op.create_index('idx_movie_status', 'movies', ['is_bad_movie', 'is_ignored'], unique=False)
    op.create_index('ix_movies_imdb_id', 'movies', ['imdb_id'], unique=False)
    op.create_index('ix_movies_plex_rating_key', 'movies', ['plex_rating_key'], unique=True)
    op.create_index('ix_movies_tmdb_id', 'movies', ['tmdb_id'], unique=False)

    # Create tv_shows table
    op.create_table(
        'tv_shows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plex_rating_key', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('sort_title', sa.String(length=500), nullable=True),
        sa.Column('original_title', sa.String(length=500), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('tvdb_id', sa.Integer(), nullable=True),
        sa.Column('tmdb_id', sa.Integer(), nullable=True),
        sa.Column('imdb_id', sa.String(length=20), nullable=True),
        sa.Column('imdb_rating', sa.Float(), nullable=True),
        sa.Column('content_rating', sa.String(length=20), nullable=True),
        sa.Column('studio', sa.String(length=200), nullable=True),
        sa.Column('network', sa.String(length=200), nullable=True),
        sa.Column('genres', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('media_type', sa.Enum('MOVIE', 'TV_SHOW', 'TV_EPISODE', 'ANIME', 'ANIME18', 'CARTOON', 'GAME_SHOW', 'MUSIC', 'OTHER', name='mediatype'), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('total_seasons', sa.Integer(), nullable=True),
        sa.Column('total_episodes', sa.Integer(), nullable=True),
        sa.Column('is_ignored', sa.Boolean(), nullable=True),
        sa.Column('is_overseerr_requested', sa.Boolean(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.Column('last_scanned', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tv_shows_imdb_id', 'tv_shows', ['imdb_id'], unique=False)
    op.create_index('ix_tv_shows_plex_rating_key', 'tv_shows', ['plex_rating_key'], unique=True)
    op.create_index('ix_tv_shows_tmdb_id', 'tv_shows', ['tmdb_id'], unique=False)
    op.create_index('ix_tv_shows_tvdb_id', 'tv_shows', ['tvdb_id'], unique=False)

    # Create tv_seasons table
    op.create_table(
        'tv_seasons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plex_rating_key', sa.String(length=50), nullable=False),
        sa.Column('show_id', sa.Integer(), nullable=False),
        sa.Column('season_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('episode_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['show_id'], ['tv_shows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tv_seasons_plex_rating_key', 'tv_seasons', ['plex_rating_key'], unique=True)

    # Create tv_episodes table
    op.create_table(
        'tv_episodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plex_rating_key', sa.String(length=50), nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('episode_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(length=2000), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('container', sa.String(length=20), nullable=True),
        sa.Column('video_codec', sa.String(length=50), nullable=True),
        sa.Column('audio_codec', sa.String(length=50), nullable=True),
        sa.Column('resolution', sa.String(length=20), nullable=True),
        sa.Column('aired_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['season_id'], ['tv_seasons.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tv_episodes_plex_rating_key', 'tv_episodes', ['plex_rating_key'], unique=True)

    # Create media_files table
    op.create_table(
        'media_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('movie_id', sa.Integer(), nullable=True),
        sa.Column('episode_id', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(length=2000), nullable=False),
        sa.Column('file_name', sa.String(length=500), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('container', sa.String(length=20), nullable=True),
        sa.Column('video_codec', sa.String(length=50), nullable=True),
        sa.Column('video_profile', sa.String(length=50), nullable=True),
        sa.Column('audio_codec', sa.String(length=50), nullable=True),
        sa.Column('audio_channels', sa.Integer(), nullable=True),
        sa.Column('resolution', sa.String(length=20), nullable=True),
        sa.Column('resolution_width', sa.Integer(), nullable=True),
        sa.Column('resolution_height', sa.Integer(), nullable=True),
        sa.Column('bitrate', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('is_hdr', sa.Boolean(), nullable=True),
        sa.Column('hdr_type', sa.String(length=50), nullable=True),
        sa.Column('color_space', sa.String(length=50), nullable=True),
        sa.Column('audio_languages', sa.JSON(), nullable=True),
        sa.Column('subtitle_languages', sa.JSON(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=True),
        sa.Column('is_corrupt', sa.Boolean(), nullable=True),
        sa.Column('integrity_checked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['episode_id'], ['tv_episodes.id'], ),
        sa.ForeignKeyConstraint(['movie_id'], ['movies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_path')
    )
    op.create_index('idx_file_duplicate', 'media_files', ['movie_id', 'is_duplicate'], unique=False)
    op.create_index('idx_file_quality', 'media_files', ['quality_score', 'is_primary'], unique=False)

    # Create issues table
    op.create_table(
        'issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('movie_id', sa.Integer(), nullable=True),
        sa.Column('tv_show_id', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(length=2000), nullable=True),
        sa.Column('issue_type', sa.Enum('CORRUPT_FILE', 'AUDIO_SYNC', 'MISSING_AUDIO', 'MISSING_SUBTITLE', 'SUBTITLE_TIMING', 'HDR_METADATA', 'WRONG_LANGUAGE', 'OVERSIZED_FILE', 'UNDERSIZED_FILE', 'DUPLICATE_FILE', 'BAD_NAMING', 'MISSING_COLLECTION', 'OUTDATED_CODEC', 'LOW_QUALITY', name='issuetype'), nullable=False),
        sa.Column('severity', sa.Enum('INFO', 'WARNING', 'ERROR', 'CRITICAL', name='issueseverity'), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('can_auto_fix', sa.Boolean(), nullable=True),
        sa.Column('auto_fix_action', sa.String(length=100), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['movie_id'], ['movies.id'], ),
        sa.ForeignKeyConstraint(['tv_show_id'], ['tv_shows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_issue_resolved', 'issues', ['is_resolved'], unique=False)
    op.create_index('idx_issue_type_severity', 'issues', ['issue_type', 'severity'], unique=False)

    # Create recommendations table
    op.create_table(
        'recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('media_type', sa.Enum('MOVIE', 'TV_SHOW', 'TV_EPISODE', 'ANIME', 'ANIME18', 'CARTOON', 'GAME_SHOW', 'MUSIC', 'OTHER', name='mediatype'), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('tmdb_id', sa.Integer(), nullable=True),
        sa.Column('tvdb_id', sa.Integer(), nullable=True),
        sa.Column('imdb_id', sa.String(length=20), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('ai_model_used', sa.String(length=100), nullable=True),
        sa.Column('imdb_rating', sa.Float(), nullable=True),
        sa.Column('rotten_tomatoes_rating', sa.Integer(), nullable=True),
        sa.Column('poster_url', sa.String(length=1000), nullable=True),
        sa.Column('backdrop_url', sa.String(length=1000), nullable=True),
        sa.Column('is_ignored', sa.Boolean(), nullable=True),
        sa.Column('is_requested', sa.Boolean(), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=True),
        sa.Column('is_added', sa.Boolean(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('media_type', 'tmdb_id', name='uq_recommendation_tmdb')
    )
    op.create_index('idx_rec_status', 'recommendations', ['is_ignored', 'is_requested', 'is_added'], unique=False)
    op.create_index('ix_recommendations_tmdb_id', 'recommendations', ['tmdb_id'], unique=False)
    op.create_index('ix_recommendations_tvdb_id', 'recommendations', ['tvdb_id'], unique=False)

    # Create bad_movie_suggestions table
    op.create_table(
        'bad_movie_suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('movie_id', sa.Integer(), nullable=False),
        sa.Column('bad_score', sa.Float(), nullable=False),
        sa.Column('imdb_rating', sa.Float(), nullable=True),
        sa.Column('rotten_tomatoes_rating', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('ai_model_used', sa.String(length=100), nullable=True),
        sa.Column('is_ignored', sa.Boolean(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('suggested_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['movie_id'], ['movies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('movie_id')
    )

    # Create scans table
    op.create_table(
        'scans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED', 'CANCELLED', name='scanstatus'), nullable=True),
        sa.Column('current_phase', sa.Integer(), nullable=True),
        sa.Column('total_phases', sa.Integer(), nullable=True),
        sa.Column('phase_name', sa.String(length=100), nullable=True),
        sa.Column('current_item', sa.String(length=500), nullable=True),
        sa.Column('items_processed', sa.Integer(), nullable=True),
        sa.Column('items_total', sa.Integer(), nullable=True),
        sa.Column('progress_percent', sa.Float(), nullable=True),
        sa.Column('movies_scanned', sa.Integer(), nullable=True),
        sa.Column('tv_shows_scanned', sa.Integer(), nullable=True),
        sa.Column('episodes_scanned', sa.Integer(), nullable=True),
        sa.Column('issues_found', sa.Integer(), nullable=True),
        sa.Column('files_renamed', sa.Integer(), nullable=True),
        sa.Column('duplicates_found', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('elapsed_seconds', sa.Integer(), nullable=True),
        sa.Column('estimated_remaining_seconds', sa.Integer(), nullable=True),
        sa.Column('ai_tokens_used', sa.Integer(), nullable=True),
        sa.Column('ai_cost_usd', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create activity table
    op.create_table(
        'activity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.Enum('SCAN_STARTED', 'SCAN_COMPLETED', 'SCAN_FAILED', 'MOVIE_DELETED', 'MOVIE_IGNORED', 'RECOMMENDATION_REQUESTED', 'RECOMMENDATION_IGNORED', 'FILE_RENAMED', 'FILE_MOVED', 'DUPLICATE_REMOVED', 'ISSUE_RESOLVED', 'SETTINGS_CHANGED', 'AI_QUERY', name='actiontype'), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('movie_id', sa.Integer(), nullable=True),
        sa.Column('tv_show_id', sa.Integer(), nullable=True),
        sa.Column('scan_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['movie_id'], ['movies.id'], ),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ),
        sa.ForeignKeyConstraint(['tv_show_id'], ['tv_shows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_activity_type_date', 'activity', ['action_type', 'created_at'], unique=False)

    # Create ai_usage table
    op.create_table(
        'ai_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('purpose', sa.String(length=100), nullable=True),
        sa.Column('scan_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ai_usage_month', 'ai_usage', ['created_at'], unique=False)
    op.create_index('idx_ai_usage_provider', 'ai_usage', ['provider', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order of dependencies
    op.drop_table('ai_usage')
    op.drop_table('activity')
    op.drop_table('scans')
    op.drop_table('bad_movie_suggestions')
    op.drop_table('recommendations')
    op.drop_table('issues')
    op.drop_table('media_files')
    op.drop_table('tv_episodes')
    op.drop_table('tv_seasons')
    op.drop_table('tv_shows')
    op.drop_table('movies')
    op.drop_table('collections')
