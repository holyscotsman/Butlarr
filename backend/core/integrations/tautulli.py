"""Tautulli API client."""

from typing import Optional, List, Dict, Any
import httpx
from urllib.parse import urljoin


class TautulliClient:
    """Client for interacting with Tautulli."""
    
    def __init__(self, url: str, api_key: str):
        self.base_url = url.rstrip("/")
        self.api_key = api_key
    
    async def _request(self, cmd: str, **params) -> Any:
        """Make HTTP request to Tautulli."""
        url = urljoin(self.base_url, "/api/v2")
        params["apikey"] = self.api_key
        params["cmd"] = cmd
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("response", {}).get("result") != "success":
                raise Exception(data.get("response", {}).get("message", "Unknown error"))
            
            return data.get("response", {}).get("data", {})
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get Tautulli server info."""
        return await self._request("get_server_info")
    
    async def get_activity(self) -> Dict[str, Any]:
        """Get current activity."""
        return await self._request("get_activity")
    
    async def get_history(
        self,
        length: int = 100,
        start: int = 0,
        media_type: Optional[str] = None,
        rating_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get watch history."""
        params = {"length": length, "start": start}
        if media_type:
            params["media_type"] = media_type
        if rating_key:
            params["rating_key"] = rating_key
        
        return await self._request("get_history", **params)
    
    async def get_home_stats(self, time_range: int = 30, stats_count: int = 10) -> List[Dict[str, Any]]:
        """Get home statistics."""
        return await self._request("get_home_stats", time_range=time_range, stats_count=stats_count)
    
    async def get_library_media_info(
        self,
        section_id: int,
        length: int = 100,
        start: int = 0,
    ) -> Dict[str, Any]:
        """Get library media info."""
        return await self._request(
            "get_library_media_info",
            section_id=section_id,
            length=length,
            start=start,
        )
    
    async def get_recently_added(self, count: int = 50, media_type: Optional[str] = None) -> Dict[str, Any]:
        """Get recently added items."""
        params = {"count": count}
        if media_type:
            params["media_type"] = media_type
        return await self._request("get_recently_added", **params)
    
    async def get_item_watch_stats(self, rating_key: str) -> Dict[str, Any]:
        """Get watch statistics for an item."""
        return await self._request("get_item_watch_time_stats", rating_key=rating_key)
    
    async def get_plays_by_date(self, time_range: int = 30) -> Dict[str, Any]:
        """Get plays by date."""
        return await self._request("get_plays_by_date", time_range=time_range)
    
    async def is_watched(self, rating_key: str) -> bool:
        """Check if item has been watched."""
        try:
            history = await self.get_history(rating_key=rating_key, length=1)
            return len(history.get("data", [])) > 0
        except Exception:
            return False
    
    async def get_last_watched(self, rating_key: str) -> Optional[int]:
        """Get timestamp of last watch."""
        try:
            history = await self.get_history(rating_key=rating_key, length=1)
            data = history.get("data", [])
            if data:
                return data[0].get("stopped")
            return None
        except Exception:
            return None
    
    async def is_currently_streaming(self) -> bool:
        """Check if anyone is currently streaming."""
        activity = await self.get_activity()
        return activity.get("stream_count", 0) > 0
    
    async def get_stream_count(self) -> int:
        """Get current stream count."""
        activity = await self.get_activity()
        return activity.get("stream_count", 0)
