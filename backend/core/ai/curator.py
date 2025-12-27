"""AI Curator for library analysis and recommendations."""

import re
import json
import asyncio
from typing import Optional, List, Dict, Any
import structlog

from backend.core.ai.provider import AIProvider

logger = structlog.get_logger(__name__)

# Batch size for processing large libraries
MOVIE_BATCH_SIZE = 200
TV_SHOW_BATCH_SIZE = 100


CURATOR_SYSTEM_PROMPT = """You are Butlarr's AI Curator, analyzing a Plex media library to provide:

1. RECOMMENDATIONS - Movies/shows the user might enjoy based on their library
2. REMOVAL SUGGESTIONS - Poor quality movies that could be removed

RULES FOR RECOMMENDATIONS:
- Suggest content similar to what the user already enjoys
- Consider genres, directors, actors, themes
- Prioritize critically acclaimed content (IMDB 7.0+, RT 70%+)
- Don't suggest anything already in the library
- Provide 10-20 recommendations per category

RULES FOR REMOVAL SUGGESTIONS:
- Only suggest theatrical releases that failed both critically AND commercially
- IMDB below 5.0 AND Rotten Tomatoes below 30%
- NEVER suggest removing:
  * Cult classics (even if poorly rated)
  * So-bad-it's-good movies
  * User-requested content (marked as REQUESTED)
  * Movies with sentimental/personal value patterns
- Focus on forgettable, mediocre content
- Provide clear reasoning for each suggestion

OUTPUT FORMAT (JSON):
{
  "recommendations": {
    "movies": [
      {"title": "...", "year": 2024, "tmdb_id": 12345, "reason": "...", "confidence": 0.9}
    ],
    "tv_shows": [
      {"title": "...", "year": 2024, "tmdb_id": 12345, "reason": "...", "confidence": 0.9}
    ],
    "anime": [
      {"title": "...", "year": 2024, "tmdb_id": 12345, "reason": "...", "confidence": 0.9}
    ]
  },
  "removal_suggestions": [
    {"title": "...", "year": 2020, "plex_key": "...", "imdb": 4.2, "rt": 15, "reason": "...", "bad_score": 8.5}
  ]
}

IMPORTANT:
- Respond ONLY with valid JSON. No markdown, no explanation, just JSON.
- ALWAYS use tmdb_id (TMDB ID) for ALL content including movies, TV shows, and anime. Never use tvdb_id."""


def extract_json_from_response(text: str) -> Dict[str, Any]:
    """
    Robustly extract JSON from AI response.
    Handles markdown code blocks, extra text, and malformed JSON.
    """
    # Try direct parsing first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Remove markdown code blocks
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```$', '', text, flags=re.MULTILINE)
    
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Find JSON object in text
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Find JSON by counting braces
    start = text.find('{')
    if start != -1:
        depth = 0
        end = start
        for i, char in enumerate(text[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    
    # Return default structure
    logger.warning("Could not parse JSON from AI response", response_preview=text[:200])
    return {
        "recommendations": {"movies": [], "tv_shows": [], "anime": []},
        "removal_suggestions": [],
        "parse_error": True,
    }


class AICurator:
    """AI Curator for library analysis."""

    def __init__(self, provider: AIProvider, config):
        self.provider = provider
        self.config = config

    def _prepare_batch_summary(
        self,
        movies: List[Dict],
        shows: List[Dict],
        batch_num: int = 1,
        total_batches: int = 1,
        total_movies: int = 0,
        total_shows: int = 0,
    ) -> str:
        """Prepare library summary for a single batch."""
        summary = f"LIBRARY BATCH {batch_num}/{total_batches}:\n"
        summary += f"(Total library: {total_movies} movies, {total_shows} TV shows)\n\n"

        # Movies in this batch
        if movies:
            summary += "MOVIES IN THIS BATCH:\n"
            for movie in movies:
                title = movie.get("title", "Unknown")
                year = movie.get("year", "")
                genres = ", ".join(movie.get("genres", [])[:3]) if movie.get("genres") else ""
                imdb = movie.get("imdb_rating") or "N/A"
                rt = movie.get("rotten_tomatoes_rating") or "N/A"
                requested = movie.get("is_overseerr_requested", False)
                plex_key = movie.get("plex_rating_key", "")

                summary += f"- {title} ({year}) | Genres: {genres} | IMDB: {imdb} | RT: {rt}"
                if requested:
                    summary += " | REQUESTED"
                summary += f" | KEY: {plex_key}\n"

        # TV Shows in this batch
        if shows:
            summary += "\nTV SHOWS IN THIS BATCH:\n"
            for show in shows:
                title = show.get("title", "Unknown")
                year = show.get("year", "")
                genres = ", ".join(show.get("genres", [])[:3]) if show.get("genres") else ""
                show_type = show.get("media_type", "tv_show")

                summary += f"- {title} ({year}) | Genres: {genres} | Type: {show_type}\n"

        return summary

    def _prepare_library_summary(self, movies: List[Dict], shows: List[Dict]) -> str:
        """Prepare full library summary (for backward compatibility with small libraries)."""
        return self._prepare_batch_summary(
            movies, shows,
            batch_num=1, total_batches=1,
            total_movies=len(movies), total_shows=len(shows)
        )
    
    async def _analyze_batch(
        self,
        movies: List[Dict],
        shows: List[Dict],
        batch_num: int,
        total_batches: int,
        total_movies: int,
        total_shows: int,
    ) -> Dict[str, Any]:
        """Analyze a single batch of the library."""
        library_summary = self._prepare_batch_summary(
            movies, shows,
            batch_num=batch_num,
            total_batches=total_batches,
            total_movies=total_movies,
            total_shows=total_shows,
        )

        prompt = f"""{library_summary}

Based on this batch of the library, provide:
1. Movie recommendations (similar to what's in this batch)
2. TV show recommendations
3. Anime recommendations (if anime is present)
4. Movies from THIS BATCH that could be removed (poor quality, not cult classics)

Remember:
- Don't recommend anything already in the library
- Only suggest removing movies with IMDB < 5.0 AND RT < 30%
- Never suggest removing movies marked as REQUESTED
- bad_score should be 1-10 (10 = worst)
- Use tmdb_id (TMDB ID) for all recommendations

Respond with valid JSON only."""

        provider = self.config.ai.curator_provider
        model = self.config.ai.curator_model

        result = await self.provider.chat(
            messages=[{"role": "user", "content": prompt}],
            provider=provider if provider != "best_available" else "auto",
            model=model if model != "auto" else "auto",
            system=CURATOR_SYSTEM_PROMPT,
            max_tokens=8192,
        )

        response_text = result.get("response", "")
        analysis = extract_json_from_response(response_text)

        # Ensure required keys exist
        if "recommendations" not in analysis:
            analysis["recommendations"] = {"movies": [], "tv_shows": [], "anime": []}
        if "removal_suggestions" not in analysis:
            analysis["removal_suggestions"] = []

        # Add usage info
        analysis["usage"] = {
            "model": result.get("model", "unknown"),
            "provider": result.get("provider", "unknown"),
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "total_tokens": result.get("total_tokens", 0),
            "cost_usd": result.get("cost_usd", 0.0),
        }

        return analysis

    def _merge_batch_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge results from multiple batches, deduplicating recommendations."""
        merged = {
            "recommendations": {"movies": [], "tv_shows": [], "anime": []},
            "removal_suggestions": [],
            "usage": {
                "model": "unknown",
                "provider": "unknown",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            },
        }

        seen_movie_tmdb = set()
        seen_tv_tmdb = set()
        seen_anime_tmdb = set()
        seen_removal_keys = set()

        for result in results:
            # Merge usage stats
            usage = result.get("usage", {})
            merged["usage"]["model"] = usage.get("model", merged["usage"]["model"])
            merged["usage"]["provider"] = usage.get("provider", merged["usage"]["provider"])
            merged["usage"]["input_tokens"] += usage.get("input_tokens", 0)
            merged["usage"]["output_tokens"] += usage.get("output_tokens", 0)
            merged["usage"]["total_tokens"] += usage.get("total_tokens", 0)
            merged["usage"]["cost_usd"] += usage.get("cost_usd", 0.0)

            recs = result.get("recommendations", {})

            # Dedupe movies
            for movie in recs.get("movies", []):
                tmdb_id = movie.get("tmdb_id")
                if tmdb_id and tmdb_id not in seen_movie_tmdb:
                    seen_movie_tmdb.add(tmdb_id)
                    merged["recommendations"]["movies"].append(movie)

            # Dedupe TV shows
            for show in recs.get("tv_shows", []):
                tmdb_id = show.get("tmdb_id")
                if tmdb_id and tmdb_id not in seen_tv_tmdb:
                    seen_tv_tmdb.add(tmdb_id)
                    merged["recommendations"]["tv_shows"].append(show)

            # Dedupe anime
            for anime in recs.get("anime", []):
                tmdb_id = anime.get("tmdb_id")
                if tmdb_id and tmdb_id not in seen_anime_tmdb:
                    seen_anime_tmdb.add(tmdb_id)
                    merged["recommendations"]["anime"].append(anime)

            # Dedupe removal suggestions by plex_key
            for removal in result.get("removal_suggestions", []):
                plex_key = removal.get("plex_key")
                if plex_key and plex_key not in seen_removal_keys:
                    seen_removal_keys.add(plex_key)
                    merged["removal_suggestions"].append(removal)

        return merged

    async def analyze_library(
        self,
        movies: List[Dict],
        shows: List[Dict],
    ) -> Dict[str, Any]:
        """Analyze library and generate recommendations using batching for large libraries."""
        total_movies = len(movies)
        total_shows = len(shows)

        # Determine if we need batching
        needs_batching = total_movies > MOVIE_BATCH_SIZE or total_shows > TV_SHOW_BATCH_SIZE

        if not needs_batching:
            # Small library - single request
            logger.info("Small library, using single AI request",
                       movies=total_movies, shows=total_shows)
            try:
                return await self._analyze_batch(
                    movies, shows,
                    batch_num=1, total_batches=1,
                    total_movies=total_movies, total_shows=total_shows
                )
            except Exception as e:
                logger.error("AI curation failed", error=str(e), exc_info=True)
                return {
                    "recommendations": {"movies": [], "tv_shows": [], "anime": []},
                    "removal_suggestions": [],
                    "error": str(e),
                    "usage": {"model": "none", "provider": "none", "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}
                }

        # Large library - batch processing
        movie_batches = [
            movies[i:i + MOVIE_BATCH_SIZE]
            for i in range(0, total_movies, MOVIE_BATCH_SIZE)
        ]
        show_batches = [
            shows[i:i + TV_SHOW_BATCH_SIZE]
            for i in range(0, total_shows, TV_SHOW_BATCH_SIZE)
        ]

        # Create combined batches (pair movie batches with show batches)
        max_batches = max(len(movie_batches), len(show_batches))
        total_batches = max_batches

        logger.info("Large library detected, using batched AI requests",
                   movies=total_movies, shows=total_shows,
                   movie_batches=len(movie_batches),
                   show_batches=len(show_batches),
                   total_batches=total_batches)

        batch_results = []
        errors = []

        for i in range(max_batches):
            movie_batch = movie_batches[i] if i < len(movie_batches) else []
            show_batch = show_batches[i] if i < len(show_batches) else []

            if not movie_batch and not show_batch:
                continue

            logger.info(f"Processing batch {i + 1}/{total_batches}",
                       movies_in_batch=len(movie_batch),
                       shows_in_batch=len(show_batch))

            try:
                result = await self._analyze_batch(
                    movie_batch, show_batch,
                    batch_num=i + 1, total_batches=total_batches,
                    total_movies=total_movies, total_shows=total_shows
                )
                batch_results.append(result)

                logger.info(f"Batch {i + 1}/{total_batches} complete",
                           recommendations=len(result.get("recommendations", {}).get("movies", [])),
                           removals=len(result.get("removal_suggestions", [])))

            except Exception as e:
                logger.error(f"Batch {i + 1} failed", error=str(e))
                errors.append(f"Batch {i + 1}: {str(e)}")

        if not batch_results:
            return {
                "recommendations": {"movies": [], "tv_shows": [], "anime": []},
                "removal_suggestions": [],
                "error": "; ".join(errors) if errors else "All batches failed",
                "usage": {"model": "none", "provider": "none", "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}
            }

        # Merge all batch results
        merged = self._merge_batch_results(batch_results)

        if errors:
            merged["partial_errors"] = errors

        logger.info("AI curation complete (batched)",
                   total_movies_recommended=len(merged["recommendations"].get("movies", [])),
                   total_tv_recommended=len(merged["recommendations"].get("tv_shows", [])),
                   total_anime_recommended=len(merged["recommendations"].get("anime", [])),
                   removal_suggestions=len(merged["removal_suggestions"]),
                   batches_processed=len(batch_results),
                   batches_failed=len(errors))

        return merged
    
    async def get_recommendations_only(
        self,
        movies: List[Dict],
        shows: List[Dict],
    ) -> Dict[str, Any]:
        """Get only recommendations (no removal suggestions)."""
        library_summary = self._prepare_library_summary(movies, shows)
        
        prompt = f"""{library_summary}

Based on this library's preferences, recommend:
- 15 movies the user would likely enjoy
- 10 TV shows
- 5 anime (if anime is present in library)

Don't recommend anything already in the library.
IMPORTANT: Always use tmdb_id (TMDB ID) for ALL content - movies, TV shows, AND anime.
Respond with valid JSON only: {{"movies": [...], "tv_shows": [...], "anime": [...]}}"""

        try:
            result = await self.provider.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are a movie recommendation expert. Respond only with valid JSON.",
                max_tokens=4096,
            )
            
            response_text = result.get("response", "")
            parsed = extract_json_from_response(response_text)
            
            # Ensure structure
            return {
                "movies": parsed.get("movies", []),
                "tv_shows": parsed.get("tv_shows", []),
                "anime": parsed.get("anime", []),
            }
            
        except Exception as e:
            logger.error("Recommendation generation failed", error=str(e))
            return {"movies": [], "tv_shows": [], "anime": []}
    
    async def evaluate_movie(self, movie: Dict) -> Dict[str, Any]:
        """Evaluate a single movie for removal."""
        prompt = f"""Evaluate this movie for potential removal:

Title: {movie.get('title')}
Year: {movie.get('year')}
IMDB Rating: {movie.get('imdb_rating', 'N/A')}
RT Score: {movie.get('rotten_tomatoes_rating', 'N/A')}
Genres: {', '.join(movie.get('genres', []))}

Is this a cult classic? Is it "so bad it's good"? Should it be kept?

Respond with JSON: {{"should_remove": true/false, "reason": "...", "bad_score": 1-10}}"""

        try:
            result = await self.provider.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are a film expert. Evaluate movies objectively. Protect cult classics. Respond only with JSON.",
                max_tokens=200,
            )
            
            response_text = result.get("response", "")
            return extract_json_from_response(response_text)
            
        except Exception as e:
            logger.error("Movie evaluation failed", error=str(e))
            return {"should_remove": False, "reason": "Could not evaluate", "bad_score": 0}
