import json
from datetime import timedelta
from typing import Optional, Any

import redis

from src.lib.configuration import configuration


class RedisManager:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.client = redis.Redis.from_url(self.redis_url)

    def set(self, key: str, value: str, ex: Optional[int | timedelta] = None):
        return self.client.set(key, value, ex=ex)

    def get(self, key: str) -> Optional[str]:
        value = self.client.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return value

    def set_list(self, key: str, value: list[str], ex: Optional[int] = None):
        json_value = json.dumps(value)
        return self.set(key, json_value, ex)

    def get_list(self, key: str) -> Optional[list[str]]:
        value = self.get(key)
        return json.loads(value) if value else None

    def set_dict(self, key: str, value: dict[str, Any], ex: Optional[int] = None):
        json_value = json.dumps(value)
        return self.set(key, json_value, ex)

    def get_dict(self, key: str) -> Optional[dict[str, Any]]:
        value = self.get(key)
        return json.loads(value) if value else None

    def delete(self, key: str) -> int:
        return self.client.delete(key)

    def delete_pattern(self, pattern: str) -> int:
        count = 0
        for key in self.client.scan_iter(match=pattern):
            self.client.delete(key)
            count += 1
        return count

    def exists(self, key: str) -> bool:
        return self.client.exists(key) > 0

    def flush_all(self):
        self.client.flushall()

    def close_connection(self):
        self.client.close()

    def __del__(self):
        self.close_connection()


class RedisManagerInstance:
    instance: Optional[RedisManager] = None

    @staticmethod
    def init_database():
        if RedisManagerInstance.instance is None:
            RedisManagerInstance.instance = RedisManager(
                redis_url=configuration.get_configuration("redis.uri")
            )

    @staticmethod
    def get_instance() -> RedisManager:
        if RedisManagerInstance.instance is None:
            RedisManagerInstance.init_database()
        return RedisManagerInstance.instance

