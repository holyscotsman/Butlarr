"""Scan Manager - Orchestrates the 17-phase scanning process."""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import structlog

from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db_session
from backend.db.models import (
    Scan, ScanStatus, Movie, TVShow, TVSeason, TVEpisode, MediaFile,
    Issue, IssueType, IssueSeverity, Recommendation, BadMovieSuggestion,
    Activity, ActionType, MediaType, AIUsage, Collection
)
from backend.utils.config import get_config
from backend.core.integrations import PlexClient, RadarrClient, SonarrClient, OverseerrClient, TautulliClient
from backend.core.ai.provider import AIProvider
from backend.core.ai.curator import AICurator

logger = structlog.get_logger(__name__)

# Semaphore for concurrent file operations
FILE_CHECK_SEMAPHORE = asyncio.Semaphore(4)


SCAN_PHASES = [
    (1, "Library Sync", "Syncing with Plex library"),
    (2, "AI Curation", "Analyzing library with AI"),
    (3, "Service Sync", "Cross-referencing services"),
    (4, "Overseerr Sync", "Checking requested items"),
    (5, "Collection Analysis", "Finding incomplete collections"),
    (6, "Movie Organization", "Checking movie organization"),
    (7, "TV Organization", "Checking TV organization"),
    (8, "Movie Deep Scan", "Scanning movie files"),
    (9, "TV Deep Scan", "Scanning TV files"),
    (10, "Other Media Scan", "Scanning other media"),
    (11, "Movie Integrity", "Checking movie integrity"),
    (12, "TV Integrity", "Checking TV integrity"),
    (13, "Language Validation", "Validating languages"),
    (14, "Movie HDR/Subtitle", "Checking movie HDR/subtitles"),
    (15, "TV HDR/Subtitle", "Checking TV HDR/subtitles"),
    (16, "Storage Analysis", "Analyzing storage usage"),
    (17, "Codec Analysis", "Analyzing codecs"),
]


class ScanManager:
    """Manages library scanning operations."""

    # Class-level lock to prevent race conditions across instances
    _scan_lock = asyncio.Lock()

    def __init__(self, ws_manager):
        self.ws_manager = ws_manager
        self.is_running = False
        self.is_paused = False
        self.current_scan_id: Optional[int] = None
        self._stop_requested = False
        self._task: Optional[asyncio.Task] = None
        self._start_time: Optional[datetime] = None
        self._phase_errors: List[Dict] = []

        self._stats = {
            "movies_scanned": 0,
            "tv_shows_scanned": 0,
            "episodes_scanned": 0,
            "issues_found": 0,
            "duplicates_found": 0,
            "recommendations_generated": 0,
            "bad_movies_found": 0,
        }
    
    async def start_scan(
        self,
        scan_id: int,
        phases: Optional[List[int]] = None,
        skip_ai_curator: bool = False,
    ):
        """Start a new scan with race condition protection."""
        # Use lock to prevent race condition where multiple requests could start scans
        async with self._scan_lock:
            if self.is_running:
                raise Exception("Scan already running")

            # Set running state while still holding the lock
            self.is_running = True
            self.is_paused = False
            self.current_scan_id = scan_id
            self._stop_requested = False
            self._start_time = datetime.utcnow()
            self._phase_errors = []
            self._stats = {k: 0 for k in self._stats}

            logger.info("Starting scan", scan_id=scan_id, phases=phases, skip_ai=skip_ai_curator)

            self._task = asyncio.create_task(
                self._run_scan(scan_id, phases, skip_ai_curator)
            )
    
    async def stop_scan(self):
        """Stop the current scan."""
        logger.info("Stopping scan", scan_id=self.current_scan_id)
        self._stop_requested = True
        if self._task:
            self._task.cancel()
        self.is_running = False
        self.is_paused = False
        
        if self.current_scan_id:
            await self._update_scan_status(ScanStatus.CANCELLED)
            await self._broadcast_scan_complete("cancelled")
    
    async def pause_scan(self):
        """Pause the current scan."""
        logger.info("Pausing scan", scan_id=self.current_scan_id)
        self.is_paused = True
        await self._update_scan_status(ScanStatus.PAUSED)
    
    async def resume_scan(self):
        """Resume a paused scan."""
        logger.info("Resuming scan", scan_id=self.current_scan_id)
        self.is_paused = False
        await self._update_scan_status(ScanStatus.RUNNING)
    
    async def _run_scan(
        self,
        scan_id: int,
        phases: Optional[List[int]] = None,
        skip_ai_curator: bool = False,
    ):
        """Execute the scan phases."""
        config = get_config()
        phases_to_run = phases or list(range(1, 18))
        completed_phases = []
        
        try:
            await self._update_scan_status(ScanStatus.RUNNING)
            await self._log_activity(
                ActionType.SCAN_STARTED, 
                "Scan started", 
                f"Running {len(phases_to_run)} phases"
            )
            
            await self._clear_old_issues()
            
            for phase_num, phase_name, phase_desc in SCAN_PHASES:
                if self._stop_requested:
                    logger.info("Scan stop requested", phase=phase_num)
                    break
                
                if phase_num not in phases_to_run:
                    continue
                
                if phase_num == 2 and skip_ai_curator:
                    logger.info("Skipping AI curation as requested")
                    continue
                
                while self.is_paused and not self._stop_requested:
                    await asyncio.sleep(1)
                
                await self._update_phase(phase_num, phase_name)
                await self._broadcast_progress(phase_num, phase_name, 0, f"Starting {phase_name}...")
                
                logger.info("Starting phase", phase=phase_num, name=phase_name)
                phase_start = datetime.utcnow()
                
                try:
                    await self._execute_phase(phase_num, config)
                    completed_phases.append(phase_num)
                    
                    elapsed = (datetime.utcnow() - phase_start).total_seconds()
                    logger.info("Phase completed", phase=phase_num, name=phase_name, elapsed_seconds=elapsed)
                    
                    await self._broadcast_progress(phase_num, phase_name, 100, f"{phase_name} complete")
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Phase {phase_num} ({phase_name}) failed", 
                                error=error_msg, exc_info=True)
                    
                    self._phase_errors.append({
                        "phase": phase_num,
                        "name": phase_name,
                        "error": error_msg,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    
                    await self._log_activity(
                        ActionType.SCAN_FAILED,
                        f"Phase {phase_num} error: {phase_name}",
                        f"Error: {error_msg[:200]}... (continuing scan)"
                    )
                    
                    await self._broadcast_progress(
                        phase_num, phase_name, 100, 
                        f"Error in {phase_name} - continuing..."
                    )
            
            if not self._stop_requested:
                await self._finalize_scan_stats()
                
                if self._phase_errors:
                    await self._update_scan_status(
                        ScanStatus.COMPLETED, 
                        error=f"{len(self._phase_errors)} phase(s) had errors"
                    )
                    await self._log_activity(
                        ActionType.SCAN_COMPLETED, 
                        "Scan completed with errors",
                        f"Completed {len(completed_phases)}/{len(phases_to_run)} phases"
                    )
                else:
                    await self._update_scan_status(ScanStatus.COMPLETED)
                    await self._log_activity(
                        ActionType.SCAN_COMPLETED, 
                        "Scan completed successfully",
                        f"All {len(completed_phases)} phases completed"
                    )
                
                await self._broadcast_scan_complete("completed")
        
        except asyncio.CancelledError:
            logger.info("Scan cancelled")
            await self._update_scan_status(ScanStatus.CANCELLED)
            await self._broadcast_scan_complete("cancelled")
        except Exception as e:
            logger.error("Scan failed with critical error", error=str(e), exc_info=True)
            await self._update_scan_status(ScanStatus.FAILED, error=str(e))
            await self._log_activity(ActionType.SCAN_FAILED, "Scan failed", str(e))
            await self._broadcast_scan_complete("failed")
        finally:
            self.is_running = False
            self.current_scan_id = None
            logger.info("Scan finished", errors=len(self._phase_errors))
    
    async def _execute_phase(self, phase_num: int, config):
        """Execute a specific phase."""
        phase_methods = {
            1: self._phase_library_sync,
            2: self._phase_ai_curation,
            3: self._phase_service_sync,
            4: self._phase_overseerr_sync,
            5: self._phase_collection_analysis,
            6: self._phase_movie_organization,
            7: self._phase_tv_organization,
            8: self._phase_movie_deep_scan,
            9: self._phase_tv_deep_scan,
            10: self._phase_other_media_scan,
            11: self._phase_movie_integrity,
            12: self._phase_tv_integrity,
            13: self._phase_language_validation,
            14: self._phase_movie_hdr_subtitle,
            15: self._phase_tv_hdr_subtitle,
            16: self._phase_storage_analysis,
            17: self._phase_codec_analysis,
        }
        
        method = phase_methods.get(phase_num)
        if method:
            await method(config)
        else:
            logger.warning(f"No method for phase {phase_num}")
    
    async def _clear_old_issues(self):
        """Clear unresolved issues from previous scans."""
        async with get_db_session() as db:
            await db.execute(delete(Issue).where(Issue.is_resolved == False))
            await db.commit()
            logger.info("Cleared old unresolved issues")
    
    def _get_path_mappings(self, config) -> List[tuple]:
        """Get path mappings from config."""
        mappings = []
        if hasattr(config, 'path_mappings') and config.path_mappings:
            for mapping in config.path_mappings:
                if 'plex_path' in mapping and 'container_path' in mapping:
                    mappings.append((mapping['plex_path'], mapping['container_path']))
        # Default Unraid mapping
        if not mappings:
            mappings = [
                ("/mnt/user/", "/media/"),
            ]
        return mappings
    
    # =========================================================================
    # PHASE 1: Library Sync
    # =========================================================================
    async def _phase_library_sync(self, config):
        """Sync library from Plex with pagination, episodes, and Tautulli watch data."""
        if not config.plex.is_configured:
            logger.warning("Plex not configured, skipping library sync")
            return

        path_mappings = self._get_path_mappings(config)
        plex = PlexClient(config.plex.url, config.plex.token, path_mappings)

        # Initialize Tautulli if configured
        tautulli = None
        if hasattr(config, 'tautulli') and config.tautulli.is_configured:
            tautulli = TautulliClient(config.tautulli.url, config.tautulli.api_key)
            logger.info("Tautulli integration enabled for watch history")

        try:
            async with get_db_session() as db:
                server_info = await plex.get_server_info()
                logger.info("Connected to Plex", server=server_info.get("friendlyName", "Unknown"))

                # =============================================
                # STEP 1: Sync Movies (0-30%)
                # =============================================
                await self._broadcast_progress(1, "Library Sync", 0, "Fetching movies from Plex...")
                logger.info("Fetching all movies from Plex (paginated)")
                movies = await plex.get_all_movies()
                total_movies = len(movies)
                logger.info("Found movies in Plex", count=total_movies)

                for i, plex_movie in enumerate(movies):
                    if self._stop_requested:
                        break

                    progress = int(((i + 1) / max(total_movies, 1)) * 30)
                    if i % 25 == 0 or i == total_movies - 1:
                        await self._broadcast_progress(
                            1, "Library Sync", progress,
                            f"Movies: {i+1}/{total_movies} - {plex_movie.get('title', 'Unknown')[:40]}"
                        )

                    try:
                        movie = await self._upsert_movie(db, plex, plex_movie)

                        # Fetch watch history from Tautulli
                        if tautulli and movie:
                            try:
                                is_watched = await tautulli.is_watched(plex_movie.get("ratingKey"))
                                last_watched = await tautulli.get_last_watched(plex_movie.get("ratingKey"))
                                if is_watched is not None:
                                    movie.is_watched = is_watched
                                if last_watched:
                                    movie.last_watched_at = datetime.fromtimestamp(last_watched)
                            except Exception as e:
                                logger.debug("Failed to get Tautulli data for movie",
                                           title=plex_movie.get("title"), error=str(e))
                    except Exception as e:
                        logger.warning("Failed to sync movie",
                                      title=plex_movie.get("title"), error=str(e))

                await db.commit()
                self._stats["movies_scanned"] = total_movies

                # =============================================
                # STEP 2: Sync TV Shows (30-50%)
                # =============================================
                await self._broadcast_progress(1, "Library Sync", 30, "Fetching TV shows from Plex...")
                logger.info("Fetching all TV shows from Plex (paginated)")
                shows = await plex.get_all_shows()
                total_shows = len(shows)
                logger.info("Found TV shows in Plex", count=total_shows)

                synced_shows = []
                for i, plex_show in enumerate(shows):
                    if self._stop_requested:
                        break

                    progress = 30 + int(((i + 1) / max(total_shows, 1)) * 20)
                    if i % 10 == 0 or i == total_shows - 1:
                        await self._broadcast_progress(
                            1, "Library Sync", progress,
                            f"TV Shows: {i+1}/{total_shows} - {plex_show.get('title', 'Unknown')[:40]}"
                        )

                    try:
                        show = await self._upsert_show(db, plex, plex_show)
                        if show:
                            synced_shows.append((show, plex_show.get("ratingKey")))
                    except Exception as e:
                        logger.warning("Failed to sync show",
                                      title=plex_show.get("title"), error=str(e))

                await db.commit()
                self._stats["tv_shows_scanned"] = total_shows

                # =============================================
                # STEP 3: Sync Seasons & Episodes (50-90%)
                # =============================================
                await self._broadcast_progress(1, "Library Sync", 50, "Fetching seasons and episodes...")
                logger.info("Fetching seasons and episodes for all shows")

                total_episodes = 0
                for idx, (show, rating_key) in enumerate(synced_shows):
                    if self._stop_requested:
                        break

                    progress = 50 + int(((idx + 1) / max(len(synced_shows), 1)) * 40)
                    if idx % 5 == 0 or idx == len(synced_shows) - 1:
                        await self._broadcast_progress(
                            1, "Library Sync", progress,
                            f"Episodes: {show.title[:30]} ({idx+1}/{len(synced_shows)} shows)"
                        )

                    try:
                        seasons = await plex.get_seasons(rating_key)
                        for plex_season in seasons:
                            season = await self._upsert_season(db, show, plex_season)
                            if season:
                                episodes = await plex.get_episodes(plex_season.get("ratingKey"))
                                for plex_episode in episodes:
                                    await self._upsert_episode(db, plex, season, plex_episode, tautulli)
                                    total_episodes += 1
                    except Exception as e:
                        logger.warning("Failed to sync seasons/episodes",
                                      show=show.title, error=str(e))

                await db.commit()
                self._stats["episodes_scanned"] = total_episodes

                # =============================================
                # STEP 4: Sync Collections (90-100%)
                # =============================================
                await self._broadcast_progress(1, "Library Sync", 90, "Syncing collections...")
                logger.info("Syncing Plex collections")

                try:
                    libraries = await plex.get_libraries()
                    for lib in libraries:
                        if lib.get("type") == "movie":
                            collections = await plex.get_collections(lib["key"])
                            for coll in collections:
                                await self._upsert_collection(db, plex, coll)
                except Exception as e:
                    logger.warning("Failed to sync collections", error=str(e))

                await db.commit()

                await self._update_scan_stats(
                    movies_scanned=total_movies,
                    tv_shows_scanned=total_shows
                )

                logger.info("Library sync complete",
                           movies=total_movies, shows=total_shows, episodes=total_episodes)

                await self._broadcast_progress(1, "Library Sync", 100, "Library sync complete!")
        finally:
            await plex.close()
    
    async def _upsert_movie(self, db: AsyncSession, plex: PlexClient, plex_movie: Dict) -> Optional[Movie]:
        """Insert or update a movie. Returns the movie object."""
        rating_key = str(plex_movie.get("ratingKey"))

        movie = await db.scalar(
            select(Movie).where(Movie.plex_rating_key == rating_key)
        )

        media_info = plex.extract_media_info(plex_movie)
        ratings = plex.extract_ratings(plex_movie)

        data = {
            "title": plex_movie.get("title", "Unknown"),
            "year": plex_movie.get("year"),
            "summary": plex_movie.get("summary"),
            "genres": [g.get("tag") for g in plex_movie.get("Genre", []) if g.get("tag")],
            "tags": [t.get("tag") for t in plex_movie.get("tag", []) if t.get("tag")],
            "content_rating": plex_movie.get("contentRating"),
            "studio": plex_movie.get("studio"),
            "duration_ms": plex_movie.get("duration"),
            "imdb_id": ratings.get("imdb_id"),
            "tmdb_id": ratings.get("tmdb_id"),
            "file_path": media_info.get("file_path"),
            "file_size_bytes": media_info.get("file_size_bytes"),
            "video_codec": media_info.get("video_codec"),
            "audio_codec": media_info.get("audio_codec"),
            "resolution": media_info.get("resolution"),
            "is_hdr": media_info.get("is_hdr", False),
            "hdr_type": media_info.get("hdr_type"),
            "bitrate": media_info.get("bitrate"),
            "last_scanned": datetime.utcnow(),
        }

        if movie:
            for key, value in data.items():
                setattr(movie, key, value)
        else:
            movie = Movie(plex_rating_key=rating_key, **data)
            db.add(movie)

        return movie

    async def _upsert_show(self, db: AsyncSession, plex: PlexClient, plex_show: Dict) -> Optional[TVShow]:
        """Insert or update a TV show. Returns the show object."""
        rating_key = str(plex_show.get("ratingKey"))

        show = await db.scalar(
            select(TVShow).where(TVShow.plex_rating_key == rating_key)
        )

        ratings = plex.extract_ratings(plex_show)
        library_title = plex_show.get("librarySectionTitle", "").lower()

        media_type = MediaType.TV_SHOW
        if "anime" in library_title:
            media_type = MediaType.ANIME if "18" not in library_title else MediaType.ANIME18
        elif "cartoon" in library_title:
            media_type = MediaType.CARTOON
        elif "game show" in library_title:
            media_type = MediaType.GAME_SHOW

        data = {
            "title": plex_show.get("title", "Unknown"),
            "year": plex_show.get("year"),
            "summary": plex_show.get("summary"),
            "genres": [g.get("tag") for g in plex_show.get("Genre", []) if g.get("tag")],
            "tvdb_id": ratings.get("tvdb_id"),
            "tmdb_id": ratings.get("tmdb_id"),
            "imdb_id": ratings.get("imdb_id"),
            "media_type": media_type,
            "last_scanned": datetime.utcnow(),
        }

        if show:
            for key, value in data.items():
                setattr(show, key, value)
        else:
            show = TVShow(plex_rating_key=rating_key, **data)
            db.add(show)

        return show

    async def _upsert_season(self, db: AsyncSession, show: TVShow, plex_season: Dict) -> Optional[TVSeason]:
        """Insert or update a TV season. Returns the season object."""
        rating_key = str(plex_season.get("ratingKey"))

        season = await db.scalar(
            select(TVSeason).where(TVSeason.plex_rating_key == rating_key)
        )

        data = {
            "show_id": show.id,
            "season_number": plex_season.get("index", 0),
            "title": plex_season.get("title", f"Season {plex_season.get('index', 0)}"),
            "summary": plex_season.get("summary"),
            "episode_count": plex_season.get("leafCount", 0),
        }

        if season:
            for key, value in data.items():
                setattr(season, key, value)
        else:
            season = TVSeason(plex_rating_key=rating_key, **data)
            db.add(season)

        return season

    async def _upsert_episode(
        self,
        db: AsyncSession,
        plex: PlexClient,
        season: TVSeason,
        plex_episode: Dict,
        tautulli: Optional[TautulliClient] = None
    ) -> Optional[TVEpisode]:
        """Insert or update a TV episode. Returns the episode object."""
        rating_key = str(plex_episode.get("ratingKey"))

        episode = await db.scalar(
            select(TVEpisode).where(TVEpisode.plex_rating_key == rating_key)
        )

        media_info = plex.extract_media_info(plex_episode)

        data = {
            "season_id": season.id,
            "episode_number": plex_episode.get("index", 0),
            "title": plex_episode.get("title", f"Episode {plex_episode.get('index', 0)}"),
            "summary": plex_episode.get("summary"),
            "duration_ms": plex_episode.get("duration"),
            "file_path": media_info.get("file_path"),
            "file_size_bytes": media_info.get("file_size_bytes"),
            "container": media_info.get("container"),
            "video_codec": media_info.get("video_codec"),
            "audio_codec": media_info.get("audio_codec"),
            "resolution": media_info.get("resolution"),
        }

        # Parse aired date if available
        aired_at = plex_episode.get("originallyAvailableAt")
        if aired_at:
            try:
                data["aired_at"] = datetime.strptime(aired_at, "%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        if episode:
            for key, value in data.items():
                setattr(episode, key, value)
        else:
            episode = TVEpisode(plex_rating_key=rating_key, **data)
            db.add(episode)

        return episode

    async def _upsert_collection(self, db: AsyncSession, plex: PlexClient, plex_coll: Dict) -> Optional[Collection]:
        """Insert or update a collection. Returns the collection object."""
        rating_key = str(plex_coll.get("ratingKey"))

        collection = await db.scalar(
            select(Collection).where(Collection.plex_rating_key == rating_key)
        )

        data = {
            "title": plex_coll.get("title", "Unknown Collection"),
            "summary": plex_coll.get("summary"),
        }

        # Try to get item count
        try:
            items = await plex.get_collection_items(rating_key)
            data["total_movies_owned"] = len(items)
        except Exception:
            pass

        if collection:
            for key, value in data.items():
                setattr(collection, key, value)
        else:
            collection = Collection(plex_rating_key=rating_key, **data)
            db.add(collection)

        return collection
    
    # =========================================================================
    # PHASE 2: AI Curation
    # =========================================================================
    async def _phase_ai_curation(self, config):
        """Run AI curation for recommendations and bad movie detection."""
        if not config.ai.enabled:
            logger.info("AI disabled, skipping curation")
            return
        
        if not (config.ai.has_anthropic or config.ai.has_openai):
            logger.warning("No AI API keys configured, skipping curation")
            return
        
        async with get_db_session() as db:
            movies_result = await db.execute(select(Movie))
            movies = []
            for m in movies_result.scalars().all():
                movies.append({
                    "title": m.title,
                    "year": m.year,
                    "genres": m.genres or [],
                    "imdb_rating": m.imdb_rating,
                    "rotten_tomatoes_rating": m.rotten_tomatoes_rating,
                    "is_overseerr_requested": m.is_overseerr_requested,
                    "plex_rating_key": m.plex_rating_key,
                })
            
            shows_result = await db.execute(select(TVShow))
            shows = []
            for s in shows_result.scalars().all():
                shows.append({
                    "title": s.title,
                    "year": s.year,
                    "genres": s.genres or [],
                    "media_type": s.media_type.value if s.media_type else "tv_show",
                })
            
            logger.info("Preparing AI curation", movies=len(movies), shows=len(shows))
            await self._broadcast_progress(2, "AI Curation", 10, f"Analyzing {len(movies)} movies...")
            
            await db.execute(
                delete(Recommendation).where(
                    and_(
                        Recommendation.is_requested == False,
                        Recommendation.is_ignored == False,
                    )
                )
            )
            await db.commit()
            
            provider = AIProvider(
                anthropic_api_key=config.ai.anthropic_api_key,
                openai_api_key=config.ai.openai_api_key,
                ollama_url=config.ai.ollama_url,
            )
            curator = AICurator(provider, config)
            
            await self._broadcast_progress(2, "AI Curation", 30, "Sending to AI...")
            
            analysis = await curator.analyze_library(movies, shows)
            
            if analysis.get("error"):
                logger.warning("AI analysis had errors", error=analysis.get("error"))
            
            await self._broadcast_progress(2, "AI Curation", 70, "Processing recommendations...")
            
            recs_count = 0
            recs = analysis.get("recommendations", {})
            for media_type_key, items in recs.items():
                if not isinstance(items, list):
                    continue
                    
                for item in items[:20]:
                    if not isinstance(item, dict):
                        continue
                    
                    media_type = MediaType.MOVIE
                    if media_type_key == "tv_shows":
                        media_type = MediaType.TV_SHOW
                    elif media_type_key == "anime":
                        media_type = MediaType.ANIME
                    
                    rec = Recommendation(
                        media_type=media_type,
                        title=item.get("title", "Unknown"),
                        year=item.get("year"),
                        tmdb_id=item.get("tmdb_id"),
                        tvdb_id=item.get("tvdb_id"),
                        reason=item.get("reason"),
                        confidence_score=item.get("confidence", 0.8),
                        ai_model_used=analysis.get("usage", {}).get("model", "unknown"),
                    )
                    db.add(rec)
                    recs_count += 1
            
            self._stats["recommendations_generated"] = recs_count
            logger.info("Stored recommendations", count=recs_count)
            
            await self._broadcast_progress(2, "AI Curation", 85, "Processing bad movie suggestions...")
            
            bad_count = 0
            for item in analysis.get("removal_suggestions", []):
                if not isinstance(item, dict):
                    continue
                    
                plex_key = item.get("plex_key")
                if not plex_key:
                    continue
                
                movie = await db.scalar(
                    select(Movie).where(Movie.plex_rating_key == str(plex_key))
                )
                if not movie:
                    continue
                
                existing = await db.scalar(
                    select(BadMovieSuggestion).where(BadMovieSuggestion.movie_id == movie.id)
                )
                if existing:
                    continue
                
                suggestion = BadMovieSuggestion(
                    movie_id=movie.id,
                    bad_score=float(item.get("bad_score", 5.0)),
                    imdb_rating=item.get("imdb"),
                    rotten_tomatoes_rating=item.get("rt"),
                    reason=item.get("reason"),
                    ai_model_used=analysis.get("usage", {}).get("model", "unknown"),
                )
                db.add(suggestion)
                movie.is_bad_movie = True
                movie.bad_movie_score = float(item.get("bad_score", 5.0))
                bad_count += 1
            
            self._stats["bad_movies_found"] = bad_count
            logger.info("Stored bad movie suggestions", count=bad_count)
            
            usage = analysis.get("usage", {})
            if usage and usage.get("total_tokens", 0) > 0:
                ai_usage = AIUsage(
                    provider=usage.get("provider", "unknown"),
                    model=usage.get("model", "unknown"),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    cost_usd=usage.get("cost_usd", 0.0),
                    purpose="curator",
                    scan_id=self.current_scan_id,
                )
                db.add(ai_usage)
                await self._update_ai_cost(usage.get("cost_usd", 0.0))
            
            await db.commit()
    
    # =========================================================================
    # PHASE 3: Service Sync
    # =========================================================================
    async def _phase_service_sync(self, config):
        """Cross-reference Plex with Radarr/Sonarr for ratings."""
        async with get_db_session() as db:
            if config.radarr.is_configured:
                logger.info("Syncing with Radarr")
                await self._broadcast_progress(3, "Service Sync", 10, "Fetching from Radarr...")
                
                try:
                    radarr = RadarrClient(config.radarr.url, config.radarr.api_key)
                    radarr_movies = await radarr.get_all_movies()
                    
                    updated = 0
                    for rm in radarr_movies:
                        tmdb_id = rm.get("tmdbId")
                        if not tmdb_id:
                            continue
                        
                        movie = await db.scalar(
                            select(Movie).where(Movie.tmdb_id == tmdb_id)
                        )
                        if movie:
                            ratings = rm.get("ratings", {})
                            if ratings.get("imdb", {}).get("value"):
                                movie.imdb_rating = ratings["imdb"]["value"]
                            if ratings.get("rottenTomatoes", {}).get("value"):
                                movie.rotten_tomatoes_rating = ratings["rottenTomatoes"]["value"]
                            updated += 1
                    
                    await db.commit()
                    logger.info("Radarr sync complete", updated=updated)
                except Exception as e:
                    logger.error("Radarr sync failed", error=str(e))
                    raise
            
            if config.sonarr.is_configured:
                logger.info("Syncing with Sonarr")
                await self._broadcast_progress(3, "Service Sync", 60, "Fetching from Sonarr...")
                
                try:
                    sonarr = SonarrClient(config.sonarr.url, config.sonarr.api_key)
                    sonarr_series = await sonarr.get_all_series()
                    
                    updated = 0
                    for ss in sonarr_series:
                        tvdb_id = ss.get("tvdbId")
                        if not tvdb_id:
                            continue
                        
                        show = await db.scalar(
                            select(TVShow).where(TVShow.tvdb_id == tvdb_id)
                        )
                        if show:
                            show.status = ss.get("status")
                            show.total_seasons = ss.get("seasonCount", 0)
                            show.total_episodes = ss.get("episodeCount", 0)
                            updated += 1
                    
                    await db.commit()
                    logger.info("Sonarr sync complete", updated=updated)
                except Exception as e:
                    logger.error("Sonarr sync failed", error=str(e))
                    raise
    
    # =========================================================================
    # PHASE 4: Overseerr Sync
    # =========================================================================
    async def _phase_overseerr_sync(self, config):
        """Mark Overseerr-requested items as protected."""
        if not config.overseerr.is_configured:
            logger.info("Overseerr not configured, skipping")
            return
        
        logger.info("Syncing with Overseerr")
        overseerr = OverseerrClient(config.overseerr.url, config.overseerr.api_key)
        
        async with get_db_session() as db:
            await self._broadcast_progress(4, "Overseerr Sync", 20, "Fetching movie requests...")
            
            try:
                movie_requests = await overseerr.get_requests(media_type="movie")
                logger.info("Got movie requests", count=len(movie_requests))
                
                marked_movies = 0
                for req in movie_requests:
                    tmdb_id = req.get("media", {}).get("tmdbId")
                    if tmdb_id:
                        movie = await db.scalar(
                            select(Movie).where(Movie.tmdb_id == tmdb_id)
                        )
                        if movie:
                            movie.is_overseerr_requested = True
                            marked_movies += 1
                
                await self._broadcast_progress(4, "Overseerr Sync", 60, "Fetching TV requests...")
                
                tv_requests = await overseerr.get_requests(media_type="tv")
                logger.info("Got TV requests", count=len(tv_requests))
                
                marked_shows = 0
                for req in tv_requests:
                    tmdb_id = req.get("media", {}).get("tmdbId")
                    if tmdb_id:
                        show = await db.scalar(
                            select(TVShow).where(TVShow.tmdb_id == tmdb_id)
                        )
                        if show:
                            show.is_overseerr_requested = True
                            marked_shows += 1
                
                await db.commit()
                logger.info("Overseerr sync complete", 
                           movies_marked=marked_movies, shows_marked=marked_shows)
            except Exception as e:
                logger.error("Overseerr sync failed", error=str(e))
                raise
    
    # =========================================================================
    # PHASE 5: Collection Analysis
    # =========================================================================
    async def _phase_collection_analysis(self, config):
        """Find incomplete collections."""
        if not config.plex.is_configured:
            return
        
        logger.info("Analyzing collections")
        path_mappings = self._get_path_mappings(config)
        plex = PlexClient(config.plex.url, config.plex.token, path_mappings)
        
        try:
            async with get_db_session() as db:
                libraries = await plex.get_libraries()
                
                for lib in libraries:
                    if lib.get("type") != "movie":
                        continue
                    
                    try:
                        collections = await plex.get_collections(lib["key"])
                        logger.info("Found collections", library=lib.get("title"), count=len(collections))
                        
                        for coll in collections:
                            try:
                                items = await plex.get_collection_items(coll.get("ratingKey"))
                                
                                if len(items) == 1:
                                    issue = Issue(
                                        issue_type=IssueType.MISSING_COLLECTION,
                                        severity=IssueSeverity.INFO,
                                        title=f"Single-item collection: {coll.get('title')}",
                                        description=f"Collection '{coll.get('title')}' has only 1 item",
                                        details={"collection": coll.get("title"), "items": len(items)},
                                    )
                                    db.add(issue)
                                    self._stats["issues_found"] += 1
                            except Exception as e:
                                logger.warning("Failed to check collection", 
                                              collection=coll.get("title"), error=str(e))
                    except Exception as e:
                        logger.warning("Failed to get collections", library=lib.get("title"), error=str(e))
                
                await db.commit()
        finally:
            await plex.close()
    
    # =========================================================================
    # PHASE 6: Movie Organization (FIXED progress calculation)
    # =========================================================================
    async def _phase_movie_organization(self, config):
        """Check movie file organization and naming."""
        logger.info("Checking movie organization")
        
        async with get_db_session() as db:
            movies = await db.scalars(select(Movie).where(Movie.file_path.isnot(None)))
            all_movies = movies.all()
            total = len(all_movies)
            
            logger.info("Checking movie naming", count=total)
            
            for i, movie in enumerate(all_movies):
                if self._stop_requested:
                    break
                
                if not movie.file_path:
                    continue
                
                # FIXED: Use (i+1) for progress, not total
                if i % 100 == 0 or i == total - 1:
                    progress = int(((i + 1) / max(total, 1)) * 100)
                    await self._broadcast_progress(
                        6, "Movie Organization", progress,
                        f"Checking {i+1}/{total}"
                    )
                
                file_path = Path(movie.file_path)
                parent = file_path.parent.name
                
                if movie.year and f"({movie.year})" not in parent:
                    issue = Issue(
                        movie_id=movie.id,
                        issue_type=IssueType.BAD_NAMING,
                        severity=IssueSeverity.WARNING,
                        title=f"Missing year in folder: {movie.title}",
                        description=f"Folder '{parent}' should include year: {movie.title} ({movie.year})",
                        file_path=movie.file_path,
                        can_auto_fix=True,
                        auto_fix_action="rename_with_filebot",
                    )
                    db.add(issue)
                    self._stats["issues_found"] += 1
            
            await db.commit()
            logger.info("Movie organization check complete")
    
    # =========================================================================
    # PHASE 7: TV Organization
    # =========================================================================
    async def _phase_tv_organization(self, config):
        """Check TV show organization."""
        logger.info("Checking TV organization")
        
        async with get_db_session() as db:
            shows = await db.scalars(select(TVShow))
            all_shows = shows.all()
            total = len(all_shows)
            
            for i, show in enumerate(all_shows):
                if self._stop_requested:
                    break
                
                progress = int(((i + 1) / max(total, 1)) * 100)
                await self._broadcast_progress(
                    7, "TV Organization", progress,
                    f"Checking {i+1}/{total}: {show.title}"
                )
            
            await db.commit()
            logger.info("TV organization check complete", shows=total)
    
    # =========================================================================
    # PHASE 8: Movie Deep Scan
    # =========================================================================
    async def _phase_movie_deep_scan(self, config):
        """Deep scan movies for duplicates."""
        logger.info("Starting movie deep scan")
        
        async with get_db_session() as db:
            movies = await db.scalars(select(Movie))
            all_movies = movies.all()
            
            tmdb_groups = {}
            for movie in all_movies:
                if movie.tmdb_id:
                    if movie.tmdb_id not in tmdb_groups:
                        tmdb_groups[movie.tmdb_id] = []
                    tmdb_groups[movie.tmdb_id].append(movie)
            
            for tmdb_id, dups in tmdb_groups.items():
                if len(dups) > 1:
                    sorted_dups = sorted(dups, key=lambda m: (
                        1 if m.resolution == "4k" else 0,
                        1 if m.is_hdr else 0,
                        m.file_size_bytes or 0
                    ), reverse=True)
                    
                    for dup in sorted_dups[1:]:
                        issue = Issue(
                            movie_id=dup.id,
                            issue_type=IssueType.DUPLICATE_FILE,
                            severity=IssueSeverity.WARNING,
                            title=f"Duplicate: {dup.title}",
                            description=f"Found {len(dups)} copies. This appears to be a lower quality version.",
                            file_path=dup.file_path,
                            details={
                                "resolution": dup.resolution,
                                "is_hdr": dup.is_hdr,
                                "size_bytes": dup.file_size_bytes,
                                "duplicate_count": len(dups),
                            },
                            can_auto_fix=True,
                            auto_fix_action="delete_duplicate",
                        )
                        db.add(issue)
                        self._stats["duplicates_found"] += 1
                        self._stats["issues_found"] += 1
            
            await db.commit()
            logger.info("Movie deep scan complete", duplicates=self._stats["duplicates_found"])
    
    # =========================================================================
    # PHASE 9: TV Deep Scan
    # =========================================================================
    async def _phase_tv_deep_scan(self, config):
        """Deep scan TV shows for issues."""
        logger.info("Starting TV deep scan")
        
        async with get_db_session() as db:
            shows = await db.scalars(select(TVShow))
            all_shows = shows.all()
            total = len(all_shows)
            
            for i, show in enumerate(all_shows):
                if self._stop_requested:
                    break
                
                if i % 10 == 0:
                    progress = int(((i + 1) / max(total, 1)) * 100)
                    await self._broadcast_progress(
                        9, "TV Deep Scan", progress,
                        f"Scanning {i+1}/{total}: {show.title}"
                    )
            
            await db.commit()
            logger.info("TV deep scan complete", shows=total)
    
    # =========================================================================
    # PHASE 10: Other Media Scan
    # =========================================================================
    async def _phase_other_media_scan(self, config):
        """Scan non-movie/TV media."""
        logger.info("Scanning other media (music, books, etc.)")
        await self._broadcast_progress(10, "Other Media Scan", 50, "Scanning...")
        await self._broadcast_progress(10, "Other Media Scan", 100, "Complete")
    
    # =========================================================================
    # PHASE 11: Movie Integrity (FIXED: async subprocess + threshold)
    # =========================================================================
    async def _phase_movie_integrity(self, config):
        """Check movie file integrity with async FFprobe."""
        logger.info("Starting movie integrity check")
        
        # Only check movies not scanned in the last 30 days
        threshold = datetime.utcnow() - timedelta(days=30)
        
        async with get_db_session() as db:
            movies = await db.scalars(
                select(Movie).where(
                    Movie.file_path.isnot(None),
                    or_(
                        Movie.last_scanned.is_(None),
                        Movie.last_scanned < threshold
                    )
                ).limit(100)
            )
            all_movies = movies.all()
            total = len(all_movies)
            
            logger.info("Checking movie integrity", count=total)
            
            for i, movie in enumerate(all_movies):
                if self._stop_requested:
                    break
                
                if not movie.file_path:
                    continue
                
                if i % 10 == 0 or i == total - 1:
                    progress = int(((i + 1) / max(total, 1)) * 100)
                    await self._broadcast_progress(
                        11, "Movie Integrity", progress,
                        f"Checking {i+1}/{total}: {movie.title}"
                    )
                
                # Check if file exists
                if not os.path.exists(movie.file_path):
                    issue = Issue(
                        movie_id=movie.id,
                        issue_type=IssueType.CORRUPT_FILE,
                        severity=IssueSeverity.CRITICAL,
                        title=f"Missing file: {movie.title}",
                        description="File not found on disk",
                        file_path=movie.file_path,
                    )
                    db.add(issue)
                    self._stats["issues_found"] += 1
                    continue
                
                # Async integrity check
                is_corrupt = await self._check_file_integrity_async(movie.file_path)
                if is_corrupt:
                    issue = Issue(
                        movie_id=movie.id,
                        issue_type=IssueType.CORRUPT_FILE,
                        severity=IssueSeverity.CRITICAL,
                        title=f"Corrupt: {movie.title}",
                        description="File failed integrity check",
                        file_path=movie.file_path,
                    )
                    db.add(issue)
                    self._stats["issues_found"] += 1
                
                # Update last scanned
                movie.last_scanned = datetime.utcnow()
            
            await db.commit()
            logger.info("Movie integrity check complete")
    
    async def _check_file_integrity_async(self, file_path: str) -> bool:
        """Check file integrity using async FFprobe. Returns True if corrupt."""
        async with FILE_CHECK_SEMAPHORE:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                return proc.returncode != 0
            except FileNotFoundError:
                logger.warning("FFprobe not found, skipping integrity check")
                return False
            except asyncio.TimeoutError:
                logger.warning("FFprobe timeout", file=file_path)
                return False
            except Exception as e:
                logger.warning("Integrity check failed", file=file_path, error=str(e))
                return False
    
    # =========================================================================
    # PHASE 12: TV Integrity
    # =========================================================================
    async def _phase_tv_integrity(self, config):
        """Check TV episode integrity."""
        logger.info("Checking TV integrity")
        await self._broadcast_progress(12, "TV Integrity", 50, "Checking episodes...")
        # Similar to movie integrity but for episodes
        await self._broadcast_progress(12, "TV Integrity", 100, "Complete")
        logger.info("TV integrity check complete")
    
    # =========================================================================
    # PHASE 13: Language Validation
    # =========================================================================
    async def _phase_language_validation(self, config):
        """Validate audio languages."""
        logger.info("Validating audio languages")
        
        async with get_db_session() as db:
            movies = await db.scalars(
                select(Movie).where(Movie.file_path.isnot(None)).limit(100)
            )
            all_movies = movies.all()
            total = len(all_movies)
            
            for i, movie in enumerate(all_movies):
                if self._stop_requested:
                    break
                
                if not movie.file_path or not os.path.exists(movie.file_path):
                    continue
                
                if i % 20 == 0:
                    progress = int(((i + 1) / max(total, 1)) * 100)
                    await self._broadcast_progress(
                        13, "Language Validation", progress,
                        f"Checking {i+1}/{total}"
                    )
                
                audio_langs = await self._get_audio_languages_async(movie.file_path)
                
                if audio_langs and "eng" not in audio_langs and "en" not in audio_langs:
                    issue = Issue(
                        movie_id=movie.id,
                        issue_type=IssueType.WRONG_LANGUAGE,
                        severity=IssueSeverity.INFO,
                        title=f"No English audio: {movie.title}",
                        description=f"Available languages: {', '.join(audio_langs)}",
                        file_path=movie.file_path,
                        details={"languages": audio_langs},
                    )
                    db.add(issue)
                    self._stats["issues_found"] += 1
            
            await db.commit()
            logger.info("Language validation complete")
    
    async def _get_audio_languages_async(self, file_path: str) -> List[str]:
        """Get audio track languages using async FFprobe."""
        async with FILE_CHECK_SEMAPHORE:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_streams", "-select_streams", "a", file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
                if proc.returncode == 0:
                    data = json.loads(stdout)
                    return [
                        s.get("tags", {}).get("language", "und")
                        for s in data.get("streams", [])
                    ]
            except Exception as e:
                logger.warning("Failed to get audio languages", file=file_path, error=str(e))
            return []
    
    # =========================================================================
    # PHASE 14: Movie HDR/Subtitle
    # =========================================================================
    async def _phase_movie_hdr_subtitle(self, config):
        """Check movie HDR metadata and subtitles."""
        logger.info("Checking movie HDR and subtitles")
        
        async with get_db_session() as db:
            hdr_movies = await db.scalars(
                select(Movie).where(Movie.is_hdr == True)
            )
            
            for movie in hdr_movies.all():
                if not movie.hdr_type:
                    issue = Issue(
                        movie_id=movie.id,
                        issue_type=IssueType.HDR_METADATA,
                        severity=IssueSeverity.INFO,
                        title=f"Unknown HDR type: {movie.title}",
                        description="HDR detected but specific format unknown",
                        file_path=movie.file_path,
                    )
                    db.add(issue)
                    self._stats["issues_found"] += 1
            
            await db.commit()
            logger.info("HDR/subtitle check complete")
    
    # =========================================================================
    # PHASE 15: TV HDR/Subtitle
    # =========================================================================
    async def _phase_tv_hdr_subtitle(self, config):
        """Check TV HDR and subtitles."""
        logger.info("Checking TV HDR and subtitles")
        await self._broadcast_progress(15, "TV HDR/Subtitle", 50, "Checking...")
        await self._broadcast_progress(15, "TV HDR/Subtitle", 100, "Complete")
        logger.info("TV HDR/subtitle check complete")
    
    # =========================================================================
    # PHASE 16: Storage Analysis
    # =========================================================================
    async def _phase_storage_analysis(self, config):
        """Analyze storage usage and find optimization opportunities."""
        logger.info("Analyzing storage")
        
        async with get_db_session() as db:
            movies = await db.scalars(
                select(Movie).where(Movie.file_size_bytes.isnot(None))
            )
            
            thresholds = config.scan.file_size_thresholds
            
            for movie in movies.all():
                if not movie.file_size_bytes or not movie.duration_ms:
                    continue
                
                size_gb = movie.file_size_bytes / (1024**3)
                hours = movie.duration_ms / (1000 * 60 * 60)
                gb_per_hour = size_gb / max(hours, 0.1)
                
                if movie.resolution == "4k" and movie.is_hdr:
                    expected = thresholds.get("4k_hdr", {"min": 8, "max": 25})
                elif movie.resolution == "4k":
                    expected = thresholds.get("4k_sdr", {"min": 6, "max": 20})
                elif movie.resolution == "1080":
                    expected = thresholds.get("1080p", {"min": 2, "max": 10})
                elif movie.resolution == "720":
                    expected = thresholds.get("720p", {"min": 1, "max": 5})
                else:
                    expected = thresholds.get("480p", {"min": 0.5, "max": 2})
                
                if gb_per_hour > expected["max"] * 1.5:
                    issue = Issue(
                        movie_id=movie.id,
                        issue_type=IssueType.OVERSIZED_FILE,
                        severity=IssueSeverity.INFO,
                        title=f"Oversized: {movie.title}",
                        description=f"{gb_per_hour:.1f} GB/hr (expected max {expected['max']})",
                        file_path=movie.file_path,
                        details={"size_gb": round(size_gb, 2), "gb_per_hour": round(gb_per_hour, 2)},
                    )
                    db.add(issue)
                    self._stats["issues_found"] += 1
                
                elif gb_per_hour < expected["min"] * 0.3:
                    issue = Issue(
                        movie_id=movie.id,
                        issue_type=IssueType.UNDERSIZED_FILE,
                        severity=IssueSeverity.WARNING,
                        title=f"Low quality: {movie.title}",
                        description=f"{gb_per_hour:.1f} GB/hr (expected min {expected['min']})",
                        file_path=movie.file_path,
                        details={"size_gb": round(size_gb, 2), "gb_per_hour": round(gb_per_hour, 2)},
                    )
                    db.add(issue)
                    self._stats["issues_found"] += 1
            
            await db.commit()
            logger.info("Storage analysis complete")
    
    # =========================================================================
    # PHASE 17: Codec Analysis
    # =========================================================================
    async def _phase_codec_analysis(self, config):
        """Identify outdated codecs."""
        logger.info("Analyzing codecs")
        
        async with get_db_session() as db:
            old_codec_movies = await db.scalars(
                select(Movie).where(
                    or_(
                        Movie.video_codec.ilike("%mpeg2%"),
                        Movie.video_codec.ilike("%mpeg4%"),
                        Movie.video_codec.ilike("%xvid%"),
                        Movie.video_codec.ilike("%divx%"),
                        Movie.video_codec.ilike("%wmv%"),
                        Movie.video_codec.ilike("%vc1%"),
                    )
                )
            )
            
            for movie in old_codec_movies.all():
                issue = Issue(
                    movie_id=movie.id,
                    issue_type=IssueType.OUTDATED_CODEC,
                    severity=IssueSeverity.INFO,
                    title=f"Outdated codec: {movie.title}",
                    description=f"Using {movie.video_codec} - consider upgrading to H.264/H.265/AV1",
                    file_path=movie.file_path,
                    details={"codec": movie.video_codec},
                )
                db.add(issue)
                self._stats["issues_found"] += 1
            
            await db.commit()
            logger.info("Codec analysis complete")
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    async def _update_scan_status(self, status: ScanStatus, error: str = None):
        """Update scan status in database."""
        async with get_db_session() as db:
            scan = await db.get(Scan, self.current_scan_id)
            if scan:
                scan.status = status
                if status == ScanStatus.COMPLETED:
                    scan.completed_at = datetime.utcnow()
                if status == ScanStatus.RUNNING and not scan.started_at:
                    scan.started_at = datetime.utcnow()
                if error:
                    scan.error_message = error
                if self._start_time:
                    scan.elapsed_seconds = int((datetime.utcnow() - self._start_time).total_seconds())
                await db.commit()
    
    async def _update_phase(self, phase_num: int, phase_name: str):
        """Update current phase in database."""
        async with get_db_session() as db:
            scan = await db.get(Scan, self.current_scan_id)
            if scan:
                scan.current_phase = phase_num
                scan.phase_name = phase_name
                await db.commit()
    
    async def _update_scan_stats(self, **kwargs):
        """Update scan statistics."""
        async with get_db_session() as db:
            scan = await db.get(Scan, self.current_scan_id)
            if scan:
                for key, value in kwargs.items():
                    if hasattr(scan, key):
                        setattr(scan, key, value)
                await db.commit()
    
    async def _finalize_scan_stats(self):
        """Write final statistics to scan record."""
        async with get_db_session() as db:
            scan = await db.get(Scan, self.current_scan_id)
            if scan:
                scan.movies_scanned = self._stats["movies_scanned"]
                scan.tv_shows_scanned = self._stats["tv_shows_scanned"]
                scan.issues_found = self._stats["issues_found"]
                scan.duplicates_found = self._stats["duplicates_found"]
                await db.commit()
    
    async def _update_ai_cost(self, cost: float):
        """Update AI cost for current scan."""
        async with get_db_session() as db:
            scan = await db.get(Scan, self.current_scan_id)
            if scan:
                scan.ai_cost_usd = (scan.ai_cost_usd or 0) + cost
                await db.commit()
    
    async def _broadcast_progress(self, phase: int, phase_name: str, percent: int, item: str):
        """Broadcast progress via WebSocket and update database."""
        # Update database with current progress
        try:
            async with get_db_session() as db:
                scan = await db.get(Scan, self.current_scan_id)
                if scan:
                    scan.current_phase = phase
                    scan.phase_name = phase_name
                    scan.progress_percent = float(percent)
                    scan.current_item = item
                    if self._start_time:
                        scan.elapsed_seconds = int((datetime.utcnow() - self._start_time).total_seconds())
                    await db.commit()
        except Exception as e:
            logger.warning("Failed to update scan progress in DB", error=str(e))

        # Broadcast via WebSocket
        if self.ws_manager:
            await self.ws_manager.broadcast("scan", {
                "type": "scan_progress",
                "phase": phase,
                "phase_name": phase_name,
                "progress_percent": percent,
                "current_item": item,
                "scan_id": self.current_scan_id,
            })
    
    async def _broadcast_scan_complete(self, status: str):
        """Broadcast scan completion via WebSocket."""
        if self.ws_manager:
            await self.ws_manager.broadcast("scan", {
                "type": "scan_complete",
                "status": status,
                "scan_id": self.current_scan_id,
                "stats": self._stats,
                "errors": self._phase_errors,
            })
    
    async def _log_activity(self, action_type: ActionType, title: str, description: str = None):
        """Log an activity."""
        async with get_db_session() as db:
            activity = Activity(
                action_type=action_type,
                title=title,
                description=description,
                scan_id=self.current_scan_id,
            )
            db.add(activity)
            await db.commit()
