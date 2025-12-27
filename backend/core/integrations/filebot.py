"""FileBot Node API client."""

from typing import Optional, List, Dict, Any
import httpx
from urllib.parse import urljoin
import base64


class FileBotClient:
    """Client for interacting with FileBot Node."""
    
    def __init__(self, url: str, username: Optional[str] = None, password: Optional[str] = None):
        self.base_url = url.rstrip("/")
        self.username = username
        self.password = password
        self.headers = {}
        
        if username and password:
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            self.headers["Authorization"] = f"Basic {credentials}"
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request to FileBot Node."""
        url = urljoin(self.base_url, endpoint)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            return response.text
    
    async def get_status(self) -> Dict[str, Any]:
        """Get FileBot Node status."""
        # FileBot Node doesn't have a proper status endpoint
        # We'll try to access the root to verify connection
        try:
            await self._request("GET", "/")
            return {
                "status": "connected",
                "filebot_version": "unknown",
                "license_status": "unknown"
            }
        except Exception as e:
            raise Exception(f"Cannot connect to FileBot Node: {str(e)}")
    
    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a pre-configured FileBot task."""
        return await self._request("GET", "/task", params={"id": task_id})
    
    async def rename(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        action: str = "move",
        format_string: Optional[str] = None,
        db: str = "TheMovieDB",
        **kwargs
    ) -> Dict[str, Any]:
        """Execute FileBot rename operation."""
        args = {
            "input": input_path,
            "action": action,
            "db": db,
        }
        
        if output_path:
            args["output"] = output_path
        
        if format_string:
            args["format"] = format_string
        
        args.update(kwargs)
        
        return await self._request("POST", "/execute", json=args)
    
    async def rename_movie(
        self,
        input_path: str,
        output_path: str,
        format_string: str = "{plex.name}",
        action: str = "move"
    ) -> Dict[str, Any]:
        """Rename a movie file using FileBot."""
        return await self.rename(
            input_path=input_path,
            output_path=output_path,
            action=action,
            format_string=format_string,
            db="TheMovieDB"
        )
    
    async def rename_tv(
        self,
        input_path: str,
        output_path: str,
        format_string: str = "{plex.name}",
        action: str = "move"
    ) -> Dict[str, Any]:
        """Rename a TV show file using FileBot."""
        return await self.rename(
            input_path=input_path,
            output_path=output_path,
            action=action,
            format_string=format_string,
            db="TheTVDB"
        )
    
    async def get_mediainfo(self, file_path: str) -> Dict[str, Any]:
        """Get media info for a file."""
        return await self._request("POST", "/mediainfo", json={"input": file_path})
    
    async def detect_series(self, file_path: str) -> Dict[str, Any]:
        """Detect series information from file."""
        return await self._request("POST", "/detect", json={
            "input": file_path,
            "type": "series"
        })
    
    async def detect_movie(self, file_path: str) -> Dict[str, Any]:
        """Detect movie information from file."""
        return await self._request("POST", "/detect", json={
            "input": file_path,
            "type": "movie"
        })


def get_plex_movie_format() -> str:
    """Get the Plex-compatible movie format string."""
    return "{plex.name}/{plex.name}"


def get_plex_tv_format() -> str:
    """Get the Plex-compatible TV format string."""
    return "{plex.name}/{episode.special ? 'Specials' : 'Season '+s00}/{plex.name}"


def get_anime_format() -> str:
    """Get anime format string."""
    return "{plex.name}/{episode.special ? 'Specials' : 'Season '+s00}/{plex.name}"
