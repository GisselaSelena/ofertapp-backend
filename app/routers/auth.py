from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioLogin, TokenOut
from app.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _generar_token(usuario: Usuario) -> str:
    return create_access_token({
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": usuario.rol,
    })


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: UsuarioCreate, db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existente:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    # El autorregistro SIEMPRE crea usuarios con rol "usuario". El rol
    # "administrador" se asigna manualmente (ver README), nunca a
    # través de este endpoint público.
    usuario = Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        rol="usuario",
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    token = _generar_token(usuario)
    return TokenOut(access_token=token, usuario=usuario)


@router.post("/login", response_model=TokenOut)
def login(data: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == data.email).first()
    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = _generar_token(usuario)
    return TokenOut(access_token=token, usuario=usuario)
