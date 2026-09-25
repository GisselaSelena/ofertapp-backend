from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import Precio
from app.cache import get_or_set_cache
from app.gemini_service import gemini_service, GeminiError

router = APIRouter(prefix="/api", tags=["ia"])

RESUMEN_IA_TTL_SECONDS = 300  # 5 minutos


@router.get("/productos/{producto_id}/resumen-ia")
def resumen_ia_producto(
    producto_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    cache_key = f"resumen_ia:producto:{producto_id}"

    def fetch_and_generar():
        vigentes = (
            db.query(Precio)
            .options(joinedload(Precio.establecimiento))
            .filter(Precio.producto_id == producto_id, Precio.vigente_hasta.is_(None))
            .order_by(Precio.valor.asc())
            .all()
        )

        if not vigentes:
            return {"resumen": None, "disponible": False}

        historial = (
            db.query(Precio)
            .options(joinedload(Precio.establecimiento))
            .filter(Precio.producto_id == producto_id)
            .order_by(Precio.vigente_desde.desc())
            .limit(10)
            .all()
        )

        lineas_vigentes = "\n".join(
            f"- {p.establecimiento.nombre}: ${p.valor:.2f}" for p in vigentes
        )
        lineas_historial = "\n".join(
            f"- {p.establecimiento.nombre}: ${p.valor:.2f} "
            f"(desde {p.vigente_desde.date().isoformat()}"
            + (
                f", hasta {p.vigente_hasta.date().isoformat()})"
                if p.vigente_hasta
                else ", vigente)"
            )
            for p in historial
        )

        prompt = (
            "Sos el asistente de OfertApp, una app que compara precios de "
            "productos entre supermercados de Ecuador. Con los datos reales "
            "a continuación (y SOLO con ellos, no inventes precios ni "
            "establecimientos que no aparezcan), escribe un resumen de "
            "MÁXIMO 3 oraciones en español: indicá cuál es la mejor opción "
            "para comprar ahora mismo y si el historial muestra alguna "
            "tendencia de precio.\n\n"
            f"Precios vigentes:\n{lineas_vigentes}\n\n"
            f"Historial reciente (hasta 10 registros):\n{lineas_historial}"
        )

        try:
            texto = gemini_service.generar_texto(prompt)
        except GeminiError as e:
            print(f"⚠️  Gemini no disponible para producto {producto_id}: {e}")
            return {"resumen": None, "disponible": False}

        return {"resumen": texto.strip(), "disponible": True}

    data, _source = get_or_set_cache(cache_key, RESUMEN_IA_TTL_SECONDS, fetch_and_generar)
    return data
