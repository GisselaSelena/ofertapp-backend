from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin, CurrentUser
from app.models import Promocion
from app.schemas import PromocionCreate
from app.cache import invalidate_cache
from app.queue import encolar_notificacion_promocion

router = APIRouter(prefix="/api/promociones", tags=["promociones"])


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_promocion(
    data: PromocionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    promocion = Promocion(
        producto_id=data.producto_id,
        establecimiento_id=data.establecimiento_id,
        descripcion=data.descripcion,
        descuento_pct=data.descuento_pct,
        valido_hasta=data.valido_hasta,
    )
    db.add(promocion)
    db.commit()
    db.refresh(promocion)

    invalidate_cache(f"precios:producto:{data.producto_id}")
    job_id = encolar_notificacion_promocion(promocion.id, data.producto_id)

    return {
        "id": promocion.id,
        "mensaje": "Promoción creada. Notificando a usuarios interesados en segundo plano.",
        "job_id": job_id,
    }
