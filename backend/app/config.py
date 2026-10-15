"""Настройки приложения берутся из переменных окружения."""
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop:shop@localhost:5432/shop")

# Redis Sentinel: адрес сентинела и имя мастера
REDIS_SENTINEL_HOST = os.getenv("REDIS_SENTINEL_HOST", "localhost")
REDIS_SENTINEL_PORT = int(os.getenv("REDIS_SENTINEL_PORT", "26379"))
REDIS_MASTER_NAME = os.getenv("REDIS_MASTER_NAME", "mymaster")

CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))  # секунд
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "IronRiff-2026")  # простой токен для админ-действий
