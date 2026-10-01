from app.auth import CurrentUser
from app.routers.precios import crear_precio
from app.schemas import PrecioCreate
from tests.fakes import FakeRedis, FakeSession


def test_crear_precio_invalida_resumen_ia_cacheado(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr("app.cache.redis_client", redis)

    producto_id = "producto-123"
    cache_key = f"resumen_ia:producto:{producto_id}"
    redis.set(cache_key, "resumen generado con precios anteriores", ex=300)
    assert redis.get(cache_key) is not None

    crear_precio(
        PrecioCreate(
            producto_id=producto_id,
            establecimiento_id="establecimiento-456",
            valor=2.5,
        ),
        db=FakeSession(refresh_id="precio-nuevo"),
        current_user=CurrentUser(
            id="admin-789",
            nombre="Admin",
            email="admin@example.com",
            rol="administrador",
        ),
    )

    assert redis.get(cache_key) is None
