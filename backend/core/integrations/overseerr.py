"""Overseerr API client."""

from typing import Optional, List, Dict, Any
import httpx
from urllib.parse import urljoin


class OverseerrClient:
    """Client for interacting with Overseerr."""
    
    def __init__(self, url: str, api_key: str):
        self.base_url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-Api-Key": api_key}
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request to Overseerr."""
        url = urljoin(self.base_url, f"/api/v1{endpoint}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else None
    
    async def get_status(self) -> Dict[str, Any]:
        """Get Overseerr status."""
        return await self._request("GET", "/status")
    
    async def get_requests(self, take: int = 100, skip: int = 0) -> Dict[str, Any]:
        """Get all requests."""
        return await self._request("GET", "/request", params={"take": take, "skip": skip})
    
    async def get_all_requests(self) -> List[Dict[str, Any]]:
        """Get all requests (paginated)."""
        all_requests = []
        skip = 0
        take = 100
        
        while True:
            data = await self.get_requests(take=take, skip=skip)
            results = data.get("results", [])
            all_requests.extend(results)
            
            if len(results) < take:
                break
            skip += take
        
        return all_requests
    
    async def is_requested(self, tmdb_id: int, media_type: str = "movie") -> bool:
        """Check if media is requested."""
        requests = await self.get_all_requests()
        
        for req in requests:
            media = req.get("media", {})
            if media.get("tmdbId") == tmdb_id and media.get("mediaType") == media_type:
                return True
        
        return False
    
    async def request_movie(self, tmdb_id: int) -> Dict[str, Any]:
        """Request a movie."""
        return await self._request("POST", "/request", json={
            "mediaType": "movie",
            "mediaId": tmdb_id,
        })
    
    async def request_tv(self, tmdb_id: int, seasons: str = "all") -> Dict[str, Any]:
        """Request a TV show."""
        return await self._request("POST", "/request", json={
            "mediaType": "tv",
            "mediaId": tmdb_id,
            "seasons": seasons,
        })
    
    async def get_movie(self, tmdb_id: int) -> Dict[str, Any]:
        """Get movie details from Overseerr."""
        return await self._request("GET", f"/movie/{tmdb_id}")
    
    async def get_tv(self, tmdb_id: int) -> Dict[str, Any]:
        """Get TV show details from Overseerr."""
        return await self._request("GET", f"/tv/{tmdb_id}")
    
    async def search(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search for media."""
        return await self._request("GET", "/search", params={"query": query, "page": page})
    
    async def get_discover_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get discover movies."""
        return await self._request("GET", "/discover/movies", params={"page": page})
    
    async def get_discover_tv(self, page: int = 1) -> Dict[str, Any]:
        """Get discover TV shows."""
        return await self._request("GET", "/discover/tv", params={"page": page})
