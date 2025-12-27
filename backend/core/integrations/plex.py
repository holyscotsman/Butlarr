"""Plex Media Server API client with pagination support."""

from typing import Optional, List, Dict, Any
import httpx
import structlog

logger = structlog.get_logger(__name__)


class PlexClient:
    """Client for interacting with Plex Media Server."""
    
    def __init__(self, url: str, token: str, path_mappings: List[tuple] = None):
        self.base_url = url.rstrip("/")
        self.token = token
        self.path_mappings = path_mappings or []
        self._client: Optional[httpx.AsyncClient] = None
    
    def _headers(self) -> Dict[str, str]:
        return {
            "X-Plex-Token": self.token,
            "Accept": "application/json",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0, headers=self._headers())
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Plex."""
        url = f"{self.base_url}{endpoint}"
        client = await self._get_client()
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def translate_path(self, path: str) -> str:
        """Translate Plex paths to container paths using mappings."""
        if not path or not self.path_mappings:
            return path
        for plex_path, container_path in self.path_mappings:
            if path.startswith(plex_path):
                return path.replace(plex_path, container_path, 1)
        return path
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get Plex server information."""
        data = await self._request("GET", "/")
        return data.get("MediaContainer", {})
    
    async def get_libraries(self) -> List[Dict[str, Any]]:
        """Get all libraries."""
        data = await self._request("GET", "/library/sections")
        return data.get("MediaContainer", {}).get("Directory", [])
    
    async def get_library_items_paginated(self, library_key: str, page_size: int = 200) -> List[Dict[str, Any]]:
        """Get all items in a library with proper pagination."""
        items = []
        start = 0
        
        while True:
            data = await self._request(
                "GET",
                f"/library/sections/{library_key}/all",
                params={
                    "X-Plex-Container-Start": start,
                    "X-Plex-Container-Size": page_size,
                }
            )
            
            container = data.get("MediaContainer", {})
            batch = container.get("Metadata", []) or []
            items.extend(batch)
            
            total_size = container.get("totalSize", len(items))
            logger.debug("Plex pagination", start=start, batch_size=len(batch), total=total_size)
            
            if len(batch) < page_size or len(items) >= total_size:
                break
            
            start += page_size
        
        return items
    
    async def get_library_items(self, library_key: str) -> List[Dict[str, Any]]:
        """Get all items in a library (uses pagination)."""
        return await self.get_library_items_paginated(library_key)
    
    async def get_movie(self, rating_key: str) -> Dict[str, Any]:
        """Get movie details."""
        data = await self._request("GET", f"/library/metadata/{rating_key}")
        items = data.get("MediaContainer", {}).get("Metadata", [])
        return items[0] if items else {}
    
    async def get_show(self, rating_key: str) -> Dict[str, Any]:
        """Get TV show details."""
        data = await self._request("GET", f"/library/metadata/{rating_key}")
        items = data.get("MediaContainer", {}).get("Metadata", [])
        return items[0] if items else {}
    
    async def get_seasons(self, show_rating_key: str) -> List[Dict[str, Any]]:
        """Get seasons for a show."""
        data = await self._request("GET", f"/library/metadata/{show_rating_key}/children")
        return data.get("MediaContainer", {}).get("Metadata", [])
    
    async def get_episodes(self, season_rating_key: str) -> List[Dict[str, Any]]:
        """Get episodes for a season."""
        data = await self._request("GET", f"/library/metadata/{season_rating_key}/children")
        return data.get("MediaContainer", {}).get("Metadata", [])
    
    async def get_collections(self, library_key: str) -> List[Dict[str, Any]]:
        """Get collections in a library."""
        try:
            data = await self._request("GET", f"/library/sections/{library_key}/collections")
            return data.get("MediaContainer", {}).get("Metadata", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise
    
    async def get_collection_items(self, collection_rating_key: str) -> List[Dict[str, Any]]:
        """Get items in a collection."""
        data = await self._request("GET", f"/library/collections/{collection_rating_key}/children")
        return data.get("MediaContainer", {}).get("Metadata", [])
    
    async def get_all_movies(self) -> List[Dict[str, Any]]:
        """Get all movies from all movie libraries with pagination."""
        libraries = await self.get_libraries()
        movies = []
        
        for lib in libraries:
            if lib.get("type") == "movie":
                try:
                    logger.info("Fetching movies from library", library=lib.get("title"))
                    lib_movies = await self.get_library_items_paginated(lib["key"])
                    movies.extend(lib_movies)
                    logger.info("Fetched movies", library=lib.get("title"), count=len(lib_movies))
                except Exception as e:
                    logger.error("Failed to get movies from library", 
                                library=lib.get("title"), error=str(e))
        
        return movies
    
    async def get_all_shows(self) -> List[Dict[str, Any]]:
        """Get all TV shows from all show libraries with pagination."""
        libraries = await self.get_libraries()
        shows = []
        
        for lib in libraries:
            if lib.get("type") == "show":
                try:
                    logger.info("Fetching shows from library", library=lib.get("title"))
                    lib_shows = await self.get_library_items_paginated(lib["key"])
                    shows.extend(lib_shows)
                    logger.info("Fetched shows", library=lib.get("title"), count=len(lib_shows))
                except Exception as e:
                    logger.error("Failed to get shows from library",
                                library=lib.get("title"), error=str(e))
        
        return shows
    
    async def refresh_library(self, library_key: str) -> None:
        """Trigger library refresh."""
        await self._request("GET", f"/library/sections/{library_key}/refresh")
    
    async def get_recently_added(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently added items."""
        data = await self._request(
            "GET",
            "/library/recentlyAdded",
            params={"X-Plex-Container-Size": limit}
        )
        return data.get("MediaContainer", {}).get("Metadata", [])
    
    def extract_media_info(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract media file information from Plex item."""
        media_list = item.get("Media", [])
        if not media_list:
            return {}
        
        media = media_list[0]
        parts = media.get("Part", [])
        part = parts[0] if parts else {}
        
        # Get file path and translate it
        file_path = part.get("file")
        if file_path:
            file_path = self.translate_path(file_path)
        
        # Detect HDR
        is_hdr = False
        hdr_type = None
        video_profile = media.get("videoProfile", "")
        
        if "dolby vision" in video_profile.lower():
            is_hdr = True
            hdr_type = "Dolby Vision"
        elif "hdr" in video_profile.lower():
            is_hdr = True
            hdr_type = "HDR10" if "hdr10" in video_profile.lower() else "HDR"
        
        return {
            "file_path": file_path,
            "file_size_bytes": part.get("size"),
            "container": part.get("container"),
            "duration_ms": item.get("duration"),
            "video_codec": media.get("videoCodec"),
            "audio_codec": media.get("audioCodec"),
            "resolution": media.get("videoResolution"),
            "width": media.get("width"),
            "height": media.get("height"),
            "bitrate": media.get("bitrate"),
            "video_profile": video_profile,
            "is_hdr": is_hdr,
            "hdr_type": hdr_type,
        }
    
    def extract_ratings(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ratings from Plex item with safe parsing."""
        ratings = {}
        
        if item.get("rating"):
            try:
                ratings["plex_rating"] = float(item["rating"])
            except (ValueError, TypeError):
                pass
        
        if item.get("audienceRating"):
            try:
                ratings["audience_rating"] = float(item["audienceRating"])
            except (ValueError, TypeError):
                pass
        
        guids = item.get("Guid", [])
        for guid in guids:
            guid_id = guid.get("id", "")
            try:
                if guid_id.startswith("imdb://"):
                    ratings["imdb_id"] = guid_id.replace("imdb://", "")
                elif guid_id.startswith("tmdb://"):
                    tmdb_str = guid_id.replace("tmdb://", "")
                    ratings["tmdb_id"] = int(tmdb_str) if tmdb_str.isdigit() else None
                elif guid_id.startswith("tvdb://"):
                    tvdb_str = guid_id.replace("tvdb://", "")
                    ratings["tvdb_id"] = int(tvdb_str) if tvdb_str.isdigit() else None
            except (ValueError, TypeError) as e:
                logger.warning("Failed to parse guid", guid_id=guid_id, error=str(e))
                continue
        
        return ratings
    
    def get_library_type(self, library_title: str) -> str:
        """Determine media type from library title."""
        title_lower = library_title.lower()
        
        if "anime" in title_lower:
            if "18" in title_lower or "adult" in title_lower:
                return "anime18"
            return "anime"
        elif "cartoon" in title_lower:
            return "cartoon"
        elif "game show" in title_lower or "gameshow" in title_lower:
            return "game_show"
        elif "music" in title_lower:
            return "music"
        
        return None
