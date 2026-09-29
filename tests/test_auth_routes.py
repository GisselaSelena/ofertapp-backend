from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.routers import auth, precios, productos


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *conditions):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self, query_result=None):
        self.query_result = query_result

    def query(self, model):
        return FakeQuery(self.query_result)


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/productos", {"nombre": "Arroz", "categoria": "Abarrotes"}),
        (
            "/api/precios",
            {
                "producto_id": "producto-123",
                "establecimiento_id": "establecimiento-456",
                "valor": 2.5,
            },
        ),
    ],
)
def test_usuario_sin_rol_admin_no_puede_crear_producto_ni_precio(path, payload):
    app = FastAPI()
    app.include_router(productos.router)
    app.include_router(precios.router)
    app.dependency_overrides[get_db] = lambda: FakeSession()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="usuario-789",
        nombre="Usuario",
        email="usuario@example.com",
        rol="usuario",
    )

    response = TestClient(app).post(path, json=payload)

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Esta acción requiere rol de administrador"
    }


def test_login_rechaza_contrasena_incorrecta(monkeypatch):
    usuario = SimpleNamespace(
        id="usuario-123",
        nombre="Usuario",
        email="usuario@example.com",
        rol="usuario",
        password_hash="hash-valido-no-verificado-en-esta-prueba",
    )
    app = FastAPI()
    app.include_router(auth.router)
    app.dependency_overrides[get_db] = lambda: FakeSession(query_result=usuario)
    monkeypatch.setattr(auth, "verify_password", lambda password, password_hash: False)

    response = TestClient(app).post(
        "/api/auth/login",
        json={"email": "usuario@example.com", "password": "incorrecta"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Credenciales inválidas"}
