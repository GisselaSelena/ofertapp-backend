import json
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import decode_access_token
from app.redis_client import redis_client
from app.models import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

USER_CACHE_TTL = 300


class CurrentUser:
    """Usuario autenticado, construido a partir del JWT (incluye el rol,
    así no hace falta consultar la base de datos para saber si puede o
    no realizar una acción de administrador)."""
    def __init__(self, id: str, nombre: str, email: str, rol: str = "usuario"):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.rol = rol


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    return CurrentUser(
        id=payload["id"],
        nombre=payload["nombre"],
        email=payload["email"],
        rol=payload.get("rol", "usuario"),
    )


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """
    Dependencia adicional para endpoints solo de administrador.
    Diferencia claramente 401 vs 403:
    - Si no hay token válido, get_current_user ya lanzó 401 antes de
      llegar aquí.
    - Si el token es válido pero el rol no es "administrador", se
      lanza 403: el usuario SÍ está identificado, pero no autorizado
      para esta acción.
    """
    if current_user.rol != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta acción requiere rol de administrador",
        )
    return current_user


async def get_full_user_cached(user_id: str, db: Session = Depends(get_db)) -> Usuario | None:
    cache_key = f"usuario:{user_id}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

    if usuario:
        data = {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email, "rol": usuario.rol}
        redis_client.set(cache_key, json.dumps(data), ex=USER_CACHE_TTL)

    return usuario
