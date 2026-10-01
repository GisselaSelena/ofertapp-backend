from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin, CurrentUser
from app.models import Establecimiento, Favorito, Precio, Producto, Promocion
from app.schemas import (
    EstablecimientoCreate,
    EstablecimientoOut,
    EstablecimientoUpdate,
    ProductoCreate,
    ProductoOut,
    ProductoUpdate,
)
from app.cache import invalidate_cache

router = APIRouter(prefix="/api", tags=["productos"])


def _invalidar_cache_producto(producto_id: str) -> None:
    invalidate_cache(f"precios:producto:{producto_id}")
    invalidate_cache(f"resumen_ia:producto:{producto_id}")


@router.post("/productos", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear_producto(
    data: ProductoCreate,
    db: Session = Depends(get_db),
    # require_admin: si el token es válido pero el usuario no es
    # administrador, responde 403 (identificado, pero sin permiso).
    current_user: CurrentUser = Depends(require_admin),
):
    producto = Producto(nombre=data.nombre, categoria=data.categoria)
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


@router.put("/productos/{producto_id}", response_model=ProductoOut)
def actualizar_producto(
    producto_id: str,
    data: ProductoUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El producto {producto_id} no existe",
        )

    producto.nombre = data.nombre
    producto.categoria = data.categoria
    db.commit()
    db.refresh(producto)
    _invalidar_cache_producto(producto_id)
    return producto


@router.delete("/productos/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(
    producto_id: str,
    forzar: bool = False,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El producto {producto_id} no existe",
        )

    precios = db.query(Precio).filter(Precio.producto_id == producto_id).all()
    favoritos = db.query(Favorito).filter(Favorito.producto_id == producto_id).all()
    promociones = db.query(Promocion).filter(Promocion.producto_id == producto_id).all()
    if (precios or favoritos or promociones) and not forzar:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "mensaje": (
                    f"No se puede eliminar el producto {producto.nombre}: "
                    "tiene datos asociados"
                ),
                "nombre": producto.nombre,
                "precios": len(precios),
                "favoritos": len(favoritos),
                "promociones": len(promociones),
            },
        )

    try:
        for relacion in precios + favoritos + promociones:
            db.delete(relacion)
        db.delete(producto)
        db.commit()
    except Exception:
        db.rollback()
        raise
    _invalidar_cache_producto(producto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/productos", response_model=list[ProductoOut])
def listar_productos(db: Session = Depends(get_db)):
    return db.query(Producto).order_by(Producto.nombre).all()


@router.post("/establecimientos", response_model=EstablecimientoOut, status_code=status.HTTP_201_CREATED)
def crear_establecimiento(
    data: EstablecimientoCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    establecimiento = Establecimiento(nombre=data.nombre, direccion=data.direccion)
    db.add(establecimiento)
    db.commit()
    db.refresh(establecimiento)
    return establecimiento


@router.put("/establecimientos/{establecimiento_id}", response_model=EstablecimientoOut)
def actualizar_establecimiento(
    establecimiento_id: str,
    data: EstablecimientoUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    establecimiento = (
        db.query(Establecimiento)
        .filter(Establecimiento.id == establecimiento_id)
        .first()
    )
    if not establecimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El establecimiento {establecimiento_id} no existe",
        )

    producto_ids = (
        db.query(Precio.producto_id)
        .filter(Precio.establecimiento_id == establecimiento_id)
        .distinct()
        .all()
    )
    establecimiento.nombre = data.nombre
    establecimiento.direccion = data.direccion
    db.commit()
    db.refresh(establecimiento)

    for producto_id in {fila[0] for fila in producto_ids}:
        _invalidar_cache_producto(producto_id)
    return establecimiento


@router.delete(
    "/establecimientos/{establecimiento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_establecimiento(
    establecimiento_id: str,
    forzar: bool = False,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    establecimiento = (
        db.query(Establecimiento)
        .filter(Establecimiento.id == establecimiento_id)
        .first()
    )
    if not establecimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El establecimiento {establecimiento_id} no existe",
        )

    precios = (
        db.query(Precio)
        .filter(Precio.establecimiento_id == establecimiento_id)
        .all()
    )
    promociones = (
        db.query(Promocion)
        .filter(Promocion.establecimiento_id == establecimiento_id)
        .all()
    )
    if (precios or promociones) and not forzar:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "mensaje": (
                    f"No se puede eliminar el establecimiento {establecimiento.nombre}: "
                    "tiene datos asociados"
                ),
                "nombre": establecimiento.nombre,
                "precios": len(precios),
                "favoritos": 0,
                "promociones": len(promociones),
            },
        )

    producto_ids = {precio.producto_id for precio in precios}
    try:
        for relacion in precios + promociones:
            db.delete(relacion)
        db.delete(establecimiento)
        db.commit()
    except Exception:
        db.rollback()
        raise
    for producto_id in producto_ids:
        _invalidar_cache_producto(producto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/establecimientos", response_model=list[EstablecimientoOut])
def listar_establecimientos(db: Session = Depends(get_db)):
    return db.query(Establecimiento).order_by(Establecimiento.nombre).all()
