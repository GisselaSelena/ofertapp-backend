import json
from typing import Callable, Any
from app.redis_client import redis_client

DEFAULT_TTL_SECONDS = 60


def get_or_set_cache(key: str, ttl_seconds: int, fetch_fn: Callable[[], Any]):
    """
    Patrón CACHE-ASIDE:
    1. Se pregunta primero a Redis.
    2. HIT -> se devuelve directo, sin tocar PostgreSQL.
    3. MISS -> se ejecuta fetch_fn() contra la base de datos, se guarda
       en Redis con TTL, y se devuelve.
    4. Cuando los datos cambian, se invalida explícitamente la clave.
    """
    cached = redis_client.get(key)

    if cached:
        print(f"🟢 CACHE HIT -> {key}")
        return json.loads(cached), "cache"

    print(f"🔴 CACHE MISS -> {key} (consultando la base de datos)")
    fresh_data = fetch_fn()

    redis_client.set(key, json.dumps(fresh_data), ex=ttl_seconds or DEFAULT_TTL_SECONDS)

    return fresh_data, "database"


def invalidate_cache(key: str) -> None:
    redis_client.delete(key)
    print(f"🗑️  Cache invalidado -> {key}")
