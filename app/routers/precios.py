from datetime import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import Precio
from app.schemas import PrecioCreate
from app.cache import get_or_set_cache, invalidate_cache

router = APIRouter(prefix="/api", tags=["precios"])


@router.post("/precios", status_code=status.HTTP_201_CREATED)
def crear_precio(
    data: PrecioCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Registra un nuevo precio como HISTÓRICO: si ya existe un precio
    vigente para este producto+establecimiento, se cierra (se le
    asigna vigente_hasta = ahora) y se crea uno nuevo como vigente.
    Así se conserva el historial completo en vez de sobrescribir.
    """
    ahora = datetime.utcnow()

    # Busca el precio actualmente vigente (si existe) para cerrarlo.
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
        fuente_usuario_id=current_user.id,  # queda registrado quién lo actualizó
    )
    db.add(nuevo_precio)
    db.commit()
    db.refresh(nuevo_precio)

    invalidate_cache(f"precios:producto:{data.producto_id}")

    return {
        "id": nuevo_precio.id,
        "valor": nuevo_precio.valor,
        "vigente_desde": nuevo_precio.vigente_desde.isoformat(),
        "mensaje": "Precio registrado",
    }


@router.get("/productos/{producto_id}/precios")
def comparar_precios(
    producto_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Compara los precios VIGENTES (vigente_hasta IS NULL) de un producto
    entre establecimientos. Al filtrar solo los vigentes, se evita
    comparar contra precios ya desactualizados que quedaron en el
    historial.
    """
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
                Precio.vigente_hasta.is_(None),  # solo el precio actual
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
    """
    Devuelve TODO el historial de precios de un producto (vigentes y no
    vigentes), opcionalmente filtrado por establecimiento. Útil para
    mostrar "cómo ha variado el precio" en la app, y para auditar quién
    actualizó cada valor.
    """
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
            }
            for p in precios
        ],
    }
