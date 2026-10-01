from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import Establecimiento, Favorito, Precio, Producto, Promocion
from app.routers import productos
from tests.fakes import FakeRedis, FakeSession


ADMIN = CurrentUser(
    id="admin-1", nombre="Admin", email="admin@example.com", rol="administrador"
)
USUARIO = CurrentUser(
    id="usuario-1", nombre="Usuario", email="usuario@example.com", rol="usuario"
)

OPERACIONES = [
    ("put", "/api/productos/prod-1", {"nombre": "Arroz nuevo", "categoria": "Granos"}),
    ("delete", "/api/productos/prod-1", None),
    ("put", "/api/establecimientos/est-1", {"nombre": "Tienda nueva", "direccion": "Centro"}),
    ("delete", "/api/establecimientos/est-1", None),
]


def crear_cliente(db, usuario=ADMIN):
    app = FastAPI()
    app.include_router(productos.router)
    app.dependency_overrides[get_db] = lambda: db
    if usuario is not None:
        app.dependency_overrides[get_current_user] = lambda: usuario
    return TestClient(app)


@pytest.mark.parametrize(("method", "path", "payload"), OPERACIONES)
def test_operaciones_catalogo_requieren_rol_admin(method, path, payload):
    client = crear_cliente(FakeSession(), usuario=USUARIO)

    response = client.request(method.upper(), path, json=payload)

    assert response.status_code == 403


@pytest.mark.parametrize(("method", "path", "payload"), OPERACIONES)
def test_operaciones_catalogo_sin_token_responden_401(method, path, payload):
    client = crear_cliente(FakeSession(), usuario=None)

    response = client.request(method.upper(), path, json=payload)

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "payload"), OPERACIONES)
def test_actualizar_o_eliminar_catalogo_inexistente_responde_404(method, path, payload):
    client = crear_cliente(FakeSession())

    response = client.request(method.upper(), path, json=payload)

    assert response.status_code == 404
    assert "no existe" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    ("path", "parent_model", "related_model", "parent"),
    [
        (
            "/api/productos/prod-1",
            Producto,
            Precio,
            SimpleNamespace(id="prod-1", nombre="Producto de prueba"),
        ),
        (
            "/api/productos/prod-1",
            Producto,
            Favorito,
            SimpleNamespace(id="prod-1", nombre="Producto de prueba"),
        ),
        (
            "/api/productos/prod-1",
            Producto,
            Promocion,
            SimpleNamespace(id="prod-1", nombre="Producto de prueba"),
        ),
        (
            "/api/establecimientos/est-1",
            Establecimiento,
            Precio,
            SimpleNamespace(id="est-1", nombre="Establecimiento de prueba"),
        ),
        (
            "/api/establecimientos/est-1",
            Establecimiento,
            Promocion,
            SimpleNamespace(id="est-1", nombre="Establecimiento de prueba"),
        ),
    ],
)
def test_no_elimina_entidad_con_relaciones(path, parent_model, related_model, parent):
    db = FakeSession(
        query_results={parent_model: parent, related_model: SimpleNamespace(id="rel-1")}
    )
    response = crear_cliente(db).delete(path)

    assert response.status_code == 409
    assert "asociad" in response.json()["detail"]["mensaje"].lower()
    assert db.deleted == []


@pytest.mark.parametrize(
    ("path", "payload", "model", "expected_fields"),
    [
        (
            "/api/productos/prod-1",
            {"nombre": "Arroz integral", "categoria": "Granos"},
            Producto,
            {"nombre": "Arroz integral", "categoria": "Granos"},
        ),
        (
            "/api/establecimientos/est-1",
            {"nombre": "Tienda Central", "direccion": "Calle 1"},
            Establecimiento,
            {"nombre": "Tienda Central", "direccion": "Calle 1"},
        ),
    ],
)
def test_actualiza_entidad_existente(path, payload, model, expected_fields):
    entidad = SimpleNamespace(id=path.rsplit("/", 1)[-1], nombre="Nombre anterior")
    db = FakeSession(query_results={model: entidad})

    response = crear_cliente(db).put(path, json=payload)

    assert response.status_code == 200
    assert {field: response.json()[field] for field in expected_fields} == expected_fields
    assert db.commits == 1


def test_elimina_entidad_sin_relaciones_y_responde_204():
    producto = SimpleNamespace(id="prod-1")
    db = FakeSession(query_results={Producto: producto})

    response = crear_cliente(db).delete("/api/productos/prod-1")

    assert response.status_code == 204
    assert db.deleted == [producto]
    assert db.commits == 1


def test_elimina_establecimiento_sin_relaciones_y_responde_204():
    establecimiento = SimpleNamespace(id="est-1")
    db = FakeSession(query_results={Establecimiento: establecimiento})

    response = crear_cliente(db).delete("/api/establecimientos/est-1")

    assert response.status_code == 204
    assert db.deleted == [establecimiento]
    assert db.commits == 1


def test_actualizar_producto_invalida_caches_de_precios_y_resumen_ia(monkeypatch):
    import app.cache

    redis = FakeRedis()
    monkeypatch.setattr(app.cache, "redis_client", redis)
    producto = SimpleNamespace(id="prod-1", nombre="Arroz", categoria="Granos")
    db = FakeSession(query_results={Producto: producto})
    cache_keys = ["precios:producto:prod-1", "resumen_ia:producto:prod-1"]
    for key in cache_keys:
        redis.set(key, "dato almacenado")
        assert redis.get(key) is not None

    response = crear_cliente(db).put(
        "/api/productos/prod-1",
        json={"nombre": "Arroz nuevo", "categoria": "Granos"},
    )

    assert response.status_code == 200
    assert all(redis.get(key) is None for key in cache_keys)


def test_actualizar_establecimiento_invalida_caches_de_sus_productos(monkeypatch):
    import app.cache

    redis = FakeRedis()
    monkeypatch.setattr(app.cache, "redis_client", redis)
    establecimiento = SimpleNamespace(id="est-1", nombre="Tienda", direccion=None)
    db = FakeSession(
        query_results={
            Establecimiento: establecimiento,
            Precio.producto_id: [("prod-1",), ("prod-2",), ("prod-1",)],
        }
    )
    cache_keys = [
        f"{prefix}:producto:{producto_id}"
        for producto_id in ("prod-1", "prod-2")
        for prefix in ("precios", "resumen_ia")
    ]
    for key in cache_keys:
        redis.set(key, "dato almacenado")

    response = crear_cliente(db).put(
        "/api/establecimientos/est-1",
        json={"nombre": "Tienda actualizada", "direccion": "Centro"},
    )

    assert response.status_code == 200
    assert all(redis.get(key) is None for key in cache_keys)


def test_docs_publica_las_cuatro_operaciones_nuevas():
    client = crear_cliente(FakeSession())

    docs_response = client.get("/docs")
    schema = client.get("/openapi.json").json()

    assert docs_response.status_code == 200
    assert "/api/productos/{producto_id}" in schema["paths"]
    assert {"put", "delete"} <= set(schema["paths"]["/api/productos/{producto_id}"])
    assert {"put", "delete"} <= set(schema["paths"]["/api/establecimientos/{establecimiento_id}"])
