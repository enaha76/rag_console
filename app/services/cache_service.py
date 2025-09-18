"""
Simple Redis cache service for caching embeddings, search results, and LLM outputs
"""
from __future__ import annotations
import json
import logging
from typing import Any, Optional
from datetime import timedelta

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Thin wrapper around redis-py for JSON get/set with TTL.
    Keys should be small strings; values will be JSON-serialized.
    """

    def __init__(self):
        self._client = redis.from_url(settings.redis_url, decode_responses=True)
        try:
            self._client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")

    def get_json(self, key: str) -> Optional[Any]:
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis GET failed for key={key}: {e}")
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        try:
            payload = json.dumps(value)
            self._client.set(key, payload, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.warning(f"Redis SET failed for key={key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DEL failed for key={key}: {e}")
            return False
