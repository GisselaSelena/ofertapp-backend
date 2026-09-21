from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user, require_admin, CurrentUser
from app.models import Precio
from app.schemas import PrecioCreate
from app.cache import get_or_set_cache, invalidate_cache

router = APIRouter(prefix="/api", tags=["precios"])


@router.post("/precios", status_code=status.HTTP_201_CREATED)
def crear_precio(
    data: PrecioCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    ahora = datetime.utcnow()

    precio_vigente_anterior = (
        db.query(Precio)
        .filter(
            Precio.producto_id == data.producto_id,
            Precio.establecimiento_id == data.establecimiento_id,
            Precio.vigente_hasta.is_(None),
        )
        .first()
    )
    if precio_vigente_anterior:
        precio_vigente_anterior.vigente_hasta = ahora

    nuevo_precio = Precio(
        producto_id=data.producto_id,
        establecimiento_id=data.establecimiento_id,
        valor=data.valor,
        vigente_desde=ahora,
        vigente_hasta=None,
        fuente_usuario_id=current_user.id,
        reportado_lat=data.reportado_lat,
        reportado_lng=data.reportado_lng,
        tiene_foto_evidencia=data.tiene_foto_evidencia,
    )
    db.add(nuevo_precio)
    db.commit()
    db.refresh(nuevo_precio)

    invalidate_cache(f"precios:producto:{data.producto_id}")

    return {
        "id": nuevo_precio.id,
        "valor": nuevo_precio.valor,
        "vigente_desde": nuevo_precio.vigente_desde.isoformat(),
        "reportado_lat": nuevo_precio.reportado_lat,
        "reportado_lng": nuevo_precio.reportado_lng,
        "tiene_foto_evidencia": nuevo_precio.tiene_foto_evidencia,
        "mensaje": "Precio registrado",
    }


@router.get("/productos/{producto_id}/precios")
def comparar_precios(
    producto_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    cache_key = f"precios:producto:{producto_id}"

    def fetch_from_db():
        precios = (
            db.query(Precio)
            .options(
                joinedload(Precio.establecimiento),
                joinedload(Precio.fuente_usuario),
            )
            .filter(
                Precio.producto_id == producto_id,
                Precio.vigente_hasta.is_(None),
            )
            .order_by(Precio.valor.asc())
            .all()
        )
        return [
            {
                "id": p.id,
                "valor": p.valor,
                "vigente_desde": p.vigente_desde.isoformat(),
                "establecimiento": {
                    "id": p.establecimiento.id,
                    "nombre": p.establecimiento.nombre,
                    "direccion": p.establecimiento.direccion,
                },
                "fuente": {
                    "usuario_id": p.fuente_usuario.id,
                    "nombre": p.fuente_usuario.nombre,
                },
                "tiene_ubicacion": p.reportado_lat is not None,
                "tiene_foto_evidencia": p.tiene_foto_evidencia,
            }
            for p in precios
        ]

    data, source = get_or_set_cache(cache_key, 60, fetch_from_db)
    return {"source": source, "count": len(data), "precios": data}


@router.get("/productos/{producto_id}/precios/historial")
def historial_precios(
    producto_id: str,
    establecimiento_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    query = (
        db.query(Precio)
        .options(
            joinedload(Precio.establecimiento),
            joinedload(Precio.fuente_usuario),
        )
        .filter(Precio.producto_id == producto_id)
    )
    if establecimiento_id:
        query = query.filter(Precio.establecimiento_id == establecimiento_id)

    precios = query.order_by(Precio.vigente_desde.desc()).all()

    return {
        "count": len(precios),
        "historial": [
            {
                "id": p.id,
                "valor": p.valor,
                "vigente_desde": p.vigente_desde.isoformat(),
                "vigente_hasta": p.vigente_hasta.isoformat() if p.vigente_hasta else None,
                "vigente_actualmente": p.vigente_hasta is None,
                "establecimiento": p.establecimiento.nombre,
                "registrado_por": p.fuente_usuario.nombre,
                "tiene_ubicacion": p.reportado_lat is not None,
                "tiene_foto_evidencia": p.tiene_foto_evidencia,
            }
            for p in precios
        ],
    }