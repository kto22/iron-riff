"""Кэш в Redis, мастер ищем через Sentinel.

Если Redis недоступен, магазин продолжает работать без кэша —
ошибки перехватываются и только логируются.
"""
import json

from redis import RedisError
from redis.sentinel import Sentinel


class RedisCache:
    def __init__(self, host: str, port: int, master: str, ttl: int):
        self.ttl = ttl
        self.sentinel = Sentinel([(host, port)], socket_timeout=0.5)
        self.master_name = master

    @property
    def client(self):
        return self.sentinel.master_for(self.master_name, socket_timeout=0.5)

    def get(self, key: str):
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except (RedisError, OSError) as e:
            print(f"[cache] get {key}: {e}")
            return None

    def set(self, key: str, value) -> None:
        try:
            self.client.setex(key, self.ttl, json.dumps(value, ensure_ascii=False, default=str))
        except (RedisError, OSError) as e:
            print(f"[cache] set {key}: {e}")

    def clear(self, prefix: str = "") -> None:
        try:
            for key in self.client.scan_iter(f"{prefix}*"):
                self.client.delete(key)
        except (RedisError, OSError) as e:
            print(f"[cache] clear: {e}")

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except (RedisError, OSError):
            return False
