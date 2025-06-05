import json
import redis
from typing import Optional, Any
from datetime import datetime, timedelta
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        if settings.redis_enabled:
            try:
                self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
                # test connection
                self.redis_client.ping()
                self.enabled = True
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
                self.enabled = False
                self._memory_cache = {}
                self._cache_ttl = {}
        else:
            self.enabled = False
            self._memory_cache = {}
            self._cache_ttl = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.enabled:
                cached_data = self.redis_client.get(key)
                return json.loads(cached_data) if cached_data else None
            else:
                # in-memory cache with TTL
                if key in self._memory_cache:
                    if datetime.now() < self._cache_ttl.get(key, datetime.min):
                        return self._memory_cache[key]
                    else:
                        self._memory_cache.pop(key, None)
                        self._cache_ttl.pop(key, None)
                return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl_minutes: int = None) -> bool:
        """Set value in cache with TTL"""
        try:
            ttl = ttl_minutes or settings.cache_ttl_minutes
            
            if self.enabled:
                return self.redis_client.setex(
                    key, 
                    ttl * 60, 
                    json.dumps(value, default=str)
                )
            else:
                # in-memory cache
                self._memory_cache[key] = value
                self._cache_ttl[key] = datetime.now() + timedelta(minutes=ttl)
                return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.enabled:
                return bool(self.redis_client.delete(key))
            else:
                self._memory_cache.pop(key, None)
                self._cache_ttl.pop(key, None)
                return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            if self.enabled:
                keys = self.redis_client.keys(pattern)
                return self.redis_client.delete(*keys) if keys else 0
            else:
                # in-memory pattern matching
                matching_keys = [k for k in self._memory_cache.keys() if pattern.replace('*', '') in k]
                for key in matching_keys:
                    self._memory_cache.pop(key, None)
                    self._cache_ttl.pop(key, None)
                return len(matching_keys)
        except Exception as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0

# global cache instance
cache_service = CacheService()