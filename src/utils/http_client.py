"""
HTTP client with connection pooling and retry logic.
"""
import httpx
import asyncio
from typing import Optional, Dict, Any
from functools import lru_cache
from .logger import logger


class HTTPClientManager:
    """Manages HTTP connections with pooling and retry logic."""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None
    
    async def get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=5.0
                ),
                headers={"User-Agent": "SAP-Tools-API/1.0.0"}
            )
        return self._client
    
    def get_sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client with connection pooling."""
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=5.0
                ),
                headers={"User-Agent": "SAP-Tools-API/1.0.0"}
            )
        return self._sync_client
    
    async def close(self):
        """Close all HTTP clients."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()


@lru_cache()
def get_http_client_manager() -> HTTPClientManager:
    """Get cached HTTP client manager instance."""
    return HTTPClientManager()


# Simple in-memory cache for metadata and schemas
class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            import time
            entry = self._cache[key]
            if time.time() < entry['expires']:
                logger.debug(f"Cache hit for key: {key}")
                return entry['value']
            else:
                # Expired, remove from cache
                del self._cache[key]
                logger.debug(f"Cache expired for key: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        import time
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
        logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
        logger.debug("Cache cleared")


# Global cache instance
metadata_cache = SimpleCache(default_ttl=10)  # 10 secs for metadata