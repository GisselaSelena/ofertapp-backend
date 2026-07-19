import json
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import decode_access_token
from app.redis_client import redis_client
from app.models import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

USER_CACHE_TTL = 300  # 5 minutos


class CurrentUser:
    """Representa al usuario autenticado, construido SOLO desde el JWT."""
    def __init__(self, id: str, nombre: str, email: str):
        self.id = id
        self.nombre = nombre
        self.email = email


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    """
    Optimización clave de autenticación: el JWT ya trae id/nombre/email
    firmados. Verificar "quién es" en cada request protegido NO requiere
    consultar PostgreSQL — se confía en la firma criptográfica del token.
    Esto evita el patrón redundante de hacer un SELECT a `usuarios` en
    CADA endpoint protegido.
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    return CurrentUser(id=payload["id"], nombre=payload["nombre"], email=payload["email"])


async def get_full_user_cached(user_id: str, db: Session = Depends(get_db)) -> Usuario | None:
    """
    Para los pocos casos donde SÍ se necesita el registro completo y
    actualizado (ej. verificar que el usuario sigue activo), se usa
    cache-aside contra Redis con TTL corto, en vez de golpear PostgreSQL
    en cada request -> evita consultas redundantes.
    """
    cache_key = f"usuario:{user_id}"
    cached = redis_client.get(cache_key)

    if cached:
        print(f"🟢 CACHE HIT usuario -> {cache_key}")
        return json.loads(cached)

    print(f"🔴 CACHE MISS usuario -> {cache_key}")
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

    if usuario:
        data = {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email}
        redis_client.set(cache_key, json.dumps(data), ex=USER_CACHE_TTL)

    return usuario
