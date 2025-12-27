"""AI Curator for library analysis and recommendations."""

import re
import json
from typing import Optional, List, Dict, Any
import structlog

from backend.core.ai.provider import AIProvider

logger = structlog.get_logger(__name__)


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
    "tv_shows": [...],
    "anime": [...]
  },
  "removal_suggestions": [
    {"title": "...", "year": 2020, "plex_key": "...", "imdb": 4.2, "rt": 15, "reason": "...", "bad_score": 8.5}
  ]
}

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, just JSON."""


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
    
    def _prepare_library_summary(self, movies: List[Dict], shows: List[Dict]) -> str:
        """Prepare library summary for AI analysis."""
        summary = "CURRENT LIBRARY:\n\n"
        
        # Movies (limit for token management)
        summary += "MOVIES:\n"
        for movie in movies[:500]:
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
        
        if len(movies) > 500:
            summary += f"... and {len(movies) - 500} more movies\n"
        
        # TV Shows
        summary += "\nTV SHOWS:\n"
        for show in shows[:200]:
            title = show.get("title", "Unknown")
            year = show.get("year", "")
            genres = ", ".join(show.get("genres", [])[:3]) if show.get("genres") else ""
            show_type = show.get("media_type", "tv_show")
            
            summary += f"- {title} ({year}) | Genres: {genres} | Type: {show_type}\n"
        
        if len(shows) > 200:
            summary += f"... and {len(shows) - 200} more shows\n"
        
        return summary
    
    async def analyze_library(
        self,
        movies: List[Dict],
        shows: List[Dict],
    ) -> Dict[str, Any]:
        """Analyze library and generate recommendations."""
        library_summary = self._prepare_library_summary(movies, shows)
        
        prompt = f"""{library_summary}

Based on this library, provide:
1. Movie recommendations (similar to what's in the library)
2. TV show recommendations
3. Anime recommendations (if anime is present)
4. Movies that could be removed (poor quality, not cult classics)

Remember:
- Don't recommend anything already in the library
- Only suggest removing movies with IMDB < 5.0 AND RT < 30%
- Never suggest removing movies marked as REQUESTED
- bad_score should be 1-10 (10 = worst)

Respond with valid JSON only."""

        # Get response from AI
        provider = self.config.ai.curator_provider
        model = self.config.ai.curator_model
        
        try:
            result = await self.provider.chat(
                messages=[{"role": "user", "content": prompt}],
                provider=provider if provider != "best_available" else "auto",
                model=model if model != "auto" else "auto",
                system=CURATOR_SYSTEM_PROMPT,
                max_tokens=8192,
            )
            
            # Parse JSON response with robust parsing
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
            
            logger.info("AI curation complete", 
                       movies_recommended=len(analysis["recommendations"].get("movies", [])),
                       removal_suggestions=len(analysis["removal_suggestions"]))
            
            return analysis
            
        except Exception as e:
            logger.error("AI curation failed", error=str(e), exc_info=True)
            return {
                "recommendations": {"movies": [], "tv_shows": [], "anime": []},
                "removal_suggestions": [],
                "error": str(e),
                "usage": {"model": "none", "provider": "none", "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}
            }
    
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
Provide tmdb_id for movies/shows, tvdb_id for anime.
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
