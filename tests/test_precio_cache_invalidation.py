from app.auth import CurrentUser
from app.routers.precios import crear_precio
from app.schemas import PrecioCreate


class FakeRedis:
    def __init__(self):
        self.values = {}

    def set(self, key, value, ex=None):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        return self.values.pop(key, None) is not None


class FakeQuery:
    def filter(self, *conditions):
        return self

    def first(self):
        return None


class FakeSession:
    def query(self, model):
        return FakeQuery()

    def add(self, instance):
        self.instance = instance

    def commit(self):
        pass

    def refresh(self, instance):
        instance.id = "precio-nuevo"


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
        db=FakeSession(),
        current_user=CurrentUser(
            id="admin-789",
            nombre="Admin",
            email="admin@example.com",
            rol="administrador",
        ),
    )

    assert redis.get(cache_key) is None
