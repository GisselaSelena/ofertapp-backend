from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import app.cache
from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import Establecimiento, Favorito, Precio, Producto, Promocion
from app.routers import productos
from tests.fakes import FakeRedis, FakeSession


ADMIN = CurrentUser(
    id="admin-1", nombre="Admin", email="admin@example.com", rol="administrador"
)
USUARIO = CurrentUser(
    id="user-1", nombre="Usuario", email="user@example.com", rol="usuario"
)


def crear_cliente(db, usuario=ADMIN, *, raise_server_exceptions=True):
    app = FastAPI()
    app.include_router(productos.router)
    app.dependency_overrides[get_db] = lambda: db
    if usuario is not None:
        app.dependency_overrides[get_current_user] = lambda: usuario
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def test_producto_sin_forzar_responde_409_con_nombre_y_conteos():
    producto = SimpleNamespace(id="prod-1", nombre="Arroz descontinuado")
    precios = [SimpleNamespace(id="price-1"), SimpleNamespace(id="price-2")]
    favoritos = [SimpleNamespace(id="fav-1")]
    promociones = [
        SimpleNamespace(id="promo-1"),
        SimpleNamespace(id="promo-2"),
        SimpleNamespace(id="promo-3"),
    ]
    db = FakeSession(
        query_results={
            Producto: producto,
            Precio: precios,
            Favorito: favoritos,
            Promocion: promociones,
        }
    )

    response = crear_cliente(db).delete("/api/productos/prod-1")

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "mensaje": "No se puede eliminar el producto Arroz descontinuado: tiene datos asociados",
        "nombre": "Arroz descontinuado",
        "precios": 2,
        "favoritos": 1,
        "promociones": 3,
    }
    assert db.deleted == []


def test_producto_forzado_elimina_relaciones_producto_y_cache(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(app.cache, "redis_client", redis)
    producto = SimpleNamespace(id="prod-1", nombre="Arroz descontinuado")
    precios = [SimpleNamespace(id="price-1"), SimpleNamespace(id="price-2")]
    favoritos = [SimpleNamespace(id="fav-1")]
    promociones = [SimpleNamespace(id="promo-1")]
    db = FakeSession(
        query_results={
            Producto: producto,
            Precio: precios,
            Favorito: favoritos,
            Promocion: promociones,
        }
    )
    keys = ["precios:producto:prod-1", "resumen_ia:producto:prod-1"]
    for key in keys:
        redis.set(key, "cached")

    response = crear_cliente(db).delete("/api/productos/prod-1?forzar=true")

    assert response.status_code == 204
    assert db.deleted == precios + favoritos + promociones + [producto]
    assert db.commits == 1
    assert all(redis.get(key) is None for key in keys)


@pytest.mark.parametrize(
    "path",
    [
        "/api/productos/prod-1?forzar=true",
        "/api/establecimientos/est-1?forzar=true",
    ],
)
def test_usuario_normal_con_forzar_recibe_403(path):
    response = crear_cliente(FakeSession(), usuario=USUARIO).delete(path)

    assert response.status_code == 403


@pytest.mark.parametrize(
    "path",
    [
        "/api/productos/no-existe?forzar=true",
        "/api/establecimientos/no-existe?forzar=true",
    ],
)
def test_borrado_forzado_inexistente_responde_404(path):
    response = crear_cliente(FakeSession()).delete(path)

    assert response.status_code == 404


def test_producto_forzado_hace_rollback_si_falla_el_borrado():
    producto = SimpleNamespace(id="prod-1", nombre="Arroz")
    precio = SimpleNamespace(id="price-1")

    class FailingSession(FakeSession):
        def delete(self, instance):
            if instance is producto:
                raise RuntimeError("fallo al borrar producto")
            super().delete(instance)

        def rollback(self):
            super().rollback()
            self.deleted.clear()

    db = FailingSession(query_results={Producto: producto, Precio: [precio]})
    response = crear_cliente(db, raise_server_exceptions=False).delete(
        "/api/productos/prod-1?forzar=true"
    )

    assert response.status_code == 500
    assert db.rollbacks == 1
    assert db.deleted == []
    assert db.commits == 0


def test_establecimiento_sin_forzar_responde_409_con_conteos():
    establecimiento = SimpleNamespace(
        id="est-1", nombre="Tienda cerrada", direccion="Centro"
    )
    db = FakeSession(
        query_results={
            Establecimiento: establecimiento,
            Precio: [SimpleNamespace(id="p1"), SimpleNamespace(id="p2")],
            Promocion: [SimpleNamespace(id="promo-1")],
        }
    )

    response = crear_cliente(db).delete("/api/establecimientos/est-1")

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "mensaje": "No se puede eliminar el establecimiento Tienda cerrada: tiene datos asociados",
        "nombre": "Tienda cerrada",
        "precios": 2,
        "favoritos": 0,
        "promociones": 1,
    }
    assert db.deleted == []


def test_establecimiento_forzado_elimina_relaciones_e_invalida_productos(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(app.cache, "redis_client", redis)
    establecimiento = SimpleNamespace(
        id="est-1", nombre="Tienda cerrada", direccion="Centro"
    )
    precios = [
        SimpleNamespace(id="p1", producto_id="prod-1"),
        SimpleNamespace(id="p2", producto_id="prod-2"),
        SimpleNamespace(id="p3", producto_id="prod-1"),
    ]
    promociones = [SimpleNamespace(id="promo-1")]
    db = FakeSession(
        query_results={Establecimiento: establecimiento, Precio: precios, Promocion: promociones}
    )
    keys = [
        f"{prefix}:producto:{producto_id}"
        for producto_id in ("prod-1", "prod-2")
        for prefix in ("precios", "resumen_ia")
    ]
    for key in keys:
        redis.set(key, "cached")

    response = crear_cliente(db).delete(
        "/api/establecimientos/est-1?forzar=true"
    )

    assert response.status_code == 204
    assert db.deleted == precios + promociones + [establecimiento]
    assert db.commits == 1
    assert all(redis.get(key) is None for key in keys)


def test_forzar_aparece_como_parametro_en_docs():
    client = crear_cliente(FakeSession())
    schema = client.get("/openapi.json").json()

    for path in (
        "/api/productos/{producto_id}",
        "/api/establecimientos/{establecimiento_id}",
    ):
        parameters = schema["paths"][path]["delete"]["parameters"]
        assert any(
            parameter["name"] == "forzar"
            and parameter["in"] == "query"
            and parameter["schema"]["default"] is False
            for parameter in parameters
        )
