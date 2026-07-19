from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import Precio, Establecimiento
from app.schemas import PrecioCreate, PrecioOut
from app.cache import get_or_set_cache, invalidate_cache

router = APIRouter(prefix="/api", tags=["precios"])


@router.post("/precios", status_code=status.HTTP_201_CREATED)
def crear_precio(
    data: PrecioCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    precio = Precio(
        producto_id=data.producto_id,
        establecimiento_id=data.establecimiento_id,
        valor=data.valor,
    )
    db.add(precio)
    db.commit()
    db.refresh(precio)

    # Invalidación explícita: el comparador cacheado de este producto
    # quedó desactualizado con este nuevo precio.
    invalidate_cache(f"precios:producto:{data.producto_id}")

    return {"id": precio.id, "valor": precio.valor, "mensaje": "Precio registrado"}


"""
❌ VERSIÓN "ANTES" (con problema N+1) — se deja aquí comentada únicamente
como evidencia para el video / comparación de rendimiento. NO se usa.

def obtener_precios_con_n1(producto_id: str, db: Session):
    precios = db.query(Precio).filter(Precio.producto_id == producto_id).all()  # 1 consulta
    resultado = []
    for precio in precios:
        # 1 consulta ADICIONAL por cada precio para traer su establecimiento
        establecimiento = db.query(Establecimiento).filter(
            Establecimiento.id == precio.establecimiento_id
        ).first()
        resultado.append({"id": precio.id, "valor": precio.valor, "establecimiento": establecimiento})
    # Total: 1 + N consultas (N = número de precios) -> problema N+1
    return resultado
"""


@router.get("/productos/{producto_id}/precios")
def comparar_precios(
    producto_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    ✅ VERSIÓN "DESPUÉS": eager loading (joinedload -> 1 sola consulta con
    JOIN) + caché cache-aside. Esta es la operación más costosa de
    OfertApp: comparar precios de un producto entre establecimientos.
    """
    cache_key = f"precios:producto:{producto_id}"

    def fetch_from_db():
        precios = (
            db.query(Precio)
            .options(joinedload(Precio.establecimiento))  # eager loading: 1 sola consulta
            .filter(Precio.producto_id == producto_id)
            .order_by(Precio.valor.asc())  # el más barato primero
            .all()
        )
        return [
            {
                "id": p.id,
                "valor": p.valor,
                "actualizado_en": p.actualizado_en.isoformat(),
                "establecimiento": {
                    "id": p.establecimiento.id,
                    "nombre": p.establecimiento.nombre,
                    "direccion": p.establecimiento.direccion,
                },
            }
            for p in precios
        ]

    data, source = get_or_set_cache(cache_key, 60, fetch_from_db)
    return {"source": source, "count": len(data), "precios": data}
