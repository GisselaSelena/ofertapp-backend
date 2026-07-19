from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import Favorito
from app.schemas import FavoritoCreate

router = APIRouter(prefix="/api/favoritos", tags=["favoritos"])


@router.get("")
def listar_favoritos(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    LAZY LOADING en acción: este es el ÚNICO endpoint donde se cargan los
    favoritos de un usuario. Se piden explícitamente aquí (con
    joinedload para traer también el producto en la misma consulta),
    nunca automáticamente en el login ni en otros endpoints.
    """
    favoritos = (
        db.query(Favorito)
        .options(joinedload(Favorito.producto))
        .filter(Favorito.usuario_id == current_user.id)
        .order_by(Favorito.created_at.desc())
        .all()
    )
    return {
        "favoritos": [
            {
                "id": f.id,
                "producto": {"id": f.producto.id, "nombre": f.producto.nombre, "categoria": f.producto.categoria},
                "created_at": f.created_at.isoformat(),
            }
            for f in favoritos
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_favorito(
    data: FavoritoCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    favorito = Favorito(usuario_id=current_user.id, producto_id=data.producto_id)
    db.add(favorito)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya está en tus favoritos")

    db.refresh(favorito)
    return {"id": favorito.id, "mensaje": "Agregado a favoritos"}
