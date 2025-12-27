"""Sonarr API client."""

from typing import Optional, List, Dict, Any
import httpx
from urllib.parse import urljoin


class SonarrClient:
    """Client for interacting with Sonarr."""
    
    def __init__(self, url: str, api_key: str):
        self.base_url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-Api-Key": api_key}
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request to Sonarr."""
        url = urljoin(self.base_url, f"/api/v3{endpoint}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else None
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get Sonarr system status."""
        return await self._request("GET", "/system/status")
    
    async def get_series(self) -> List[Dict[str, Any]]:
        """Get all series."""
        return await self._request("GET", "/series")
    
    async def get_series_by_id(self, series_id: int) -> Dict[str, Any]:
        """Get series by ID."""
        return await self._request("GET", f"/series/{series_id}")
    
    async def get_series_by_tvdb(self, tvdb_id: int) -> Optional[Dict[str, Any]]:
        """Get series by TVDB ID."""
        series_list = await self.get_series()
        for series in series_list:
            if series.get("tvdbId") == tvdb_id:
                return series
        return None
    
    async def get_series_count(self) -> int:
        """Get total series count."""
        series = await self.get_series()
        return len(series)
    
    async def get_episodes(self, series_id: int) -> List[Dict[str, Any]]:
        """Get episodes for a series."""
        return await self._request("GET", "/episode", params={"seriesId": series_id})
    
    async def get_episode_files(self, series_id: int) -> List[Dict[str, Any]]:
        """Get episode files for a series."""
        return await self._request("GET", "/episodefile", params={"seriesId": series_id})
    
    async def get_root_folders(self) -> List[Dict[str, Any]]:
        """Get root folders."""
        return await self._request("GET", "/rootfolder")
    
    async def get_quality_profiles(self) -> List[Dict[str, Any]]:
        """Get quality profiles."""
        return await self._request("GET", "/qualityprofile")
    
    async def rename_series_files(self, series_id: int) -> Dict[str, Any]:
        """Trigger rename for a series."""
        return await self._request("POST", "/command", json={
            "name": "RenameSeries",
            "seriesIds": [series_id]
        })
    
    async def rescan_series(self, series_id: int) -> Dict[str, Any]:
        """Rescan series files."""
        return await self._request("POST", "/command", json={
            "name": "RescanSeries",
            "seriesId": series_id
        })
    
    async def delete_series(self, series_id: int, delete_files: bool = True) -> None:
        """Delete series."""
        params = {"deleteFiles": str(delete_files).lower()}
        await self._request("DELETE", f"/series/{series_id}", params=params)
    
    async def get_tags(self) -> List[Dict[str, Any]]:
        """Get all tags."""
        return await self._request("GET", "/tag")
    
    def is_anime(self, series: Dict[str, Any]) -> bool:
        """Check if series is anime based on tags or path."""
        path = series.get("path", "").lower()
        tags = series.get("tags", [])
        series_type = series.get("seriesType", "")
        
        if "anime" in path:
            return True
        if series_type == "anime":
            return True
        
        return False
