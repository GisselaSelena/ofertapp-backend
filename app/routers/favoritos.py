from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import Favorito

router = APIRouter(prefix="/api/favoritos", tags=["favoritos"])


@router.get("")
def listar_favoritos(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
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
                "producto": {
                    "id": f.producto.id,
                    "nombre": f.producto.nombre,
                    "categoria": f.producto.categoria,
                },
                "created_at": f.created_at.isoformat(),
            }
            for f in favoritos
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_favorito(
    data: dict,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from sqlalchemy.exc import IntegrityError

    producto_id = data.get("producto_id")
    favorito = Favorito(usuario_id=current_user.id, producto_id=producto_id)
    db.add(favorito)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya está en tus favoritos")

    db.refresh(favorito)
    return {"id": favorito.id, "mensaje": "Agregado a favoritos"}


@router.delete("/{favorito_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_favorito(
    favorito_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    favorito = db.query(Favorito).filter(Favorito.id == favorito_id).first()

    if not favorito:
        raise HTTPException(status_code=404, detail="Favorito no encontrado")

    if favorito.usuario_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="No puedes eliminar favoritos de otro usuario",
        )

    db.delete(favorito)
    db.commit()
    return None