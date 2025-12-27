"""Radarr API client."""

from typing import Optional, List, Dict, Any
import httpx
from urllib.parse import urljoin


class RadarrClient:
    """Client for interacting with Radarr."""
    
    def __init__(self, url: str, api_key: str):
        self.base_url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-Api-Key": api_key}
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request to Radarr."""
        url = urljoin(self.base_url, f"/api/v3{endpoint}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else None
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get Radarr system status."""
        return await self._request("GET", "/system/status")
    
    async def get_movies(self) -> List[Dict[str, Any]]:
        """Get all movies."""
        return await self._request("GET", "/movie")
    
    async def get_movie(self, movie_id: int) -> Dict[str, Any]:
        """Get movie by ID."""
        return await self._request("GET", f"/movie/{movie_id}")
    
    async def get_movie_by_tmdb(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """Get movie by TMDB ID."""
        movies = await self.get_movies()
        for movie in movies:
            if movie.get("tmdbId") == tmdb_id:
                return movie
        return None
    
    async def get_movie_count(self) -> int:
        """Get total movie count."""
        movies = await self.get_movies()
        return len(movies)
    
    async def delete_movie(self, tmdb_id: int, delete_files: bool = True, add_exclusion: bool = True) -> None:
        """Delete movie by TMDB ID."""
        movie = await self.get_movie_by_tmdb(tmdb_id)
        if movie:
            params = {
                "deleteFiles": str(delete_files).lower(),
                "addImportExclusion": str(add_exclusion).lower(),
            }
            await self._request("DELETE", f"/movie/{movie['id']}", params=params)
    
    async def get_root_folders(self) -> List[Dict[str, Any]]:
        """Get root folders."""
        return await self._request("GET", "/rootfolder")
    
    async def get_quality_profiles(self) -> List[Dict[str, Any]]:
        """Get quality profiles."""
        return await self._request("GET", "/qualityprofile")
    
    async def rename_movie_files(self, movie_id: int) -> Dict[str, Any]:
        """Trigger rename for a movie."""
        return await self._request("POST", "/command", json={
            "name": "RenameMovie",
            "movieIds": [movie_id]
        })
    
    async def get_exclusions(self) -> List[Dict[str, Any]]:
        """Get import exclusions."""
        return await self._request("GET", "/exclusions")
    
    async def add_exclusion(self, tmdb_id: int, title: str, year: int) -> Dict[str, Any]:
        """Add import exclusion."""
        return await self._request("POST", "/exclusions", json={
            "tmdbId": tmdb_id,
            "movieTitle": title,
            "movieYear": year
        })
    
    async def rescan_movie(self, movie_id: int) -> Dict[str, Any]:
        """Rescan movie files."""
        return await self._request("POST", "/command", json={
            "name": "RescanMovie",
            "movieId": movie_id
        })
