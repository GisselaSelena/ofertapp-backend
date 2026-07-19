"""
Funciones que se ejecutan EN SEGUNDO PLANO por el worker de RQ.
No se llaman directamente desde los endpoints: se encolan (ver queue.py)
y un proceso aparte (worker.py) las va tomando y ejecutando.
"""
import time
from app.database import SessionLocal
from app.models import Favorito, Usuario


def notificar_favoritos(promocion_id: str, producto_id: str):
    """
    Caso de uso real de OfertApp: cuando un establecimiento publica una
    promoción, hay que avisar a todos los usuarios que tienen ese
    producto en favoritos. Buscar y notificar a muchos usuarios puede ser
    lento (consultas + envío de notificaciones), así que esto NO se
    ejecuta dentro del request HTTP de "crear promoción": se procesa
    aparte, en background.
    """
    db = SessionLocal()
    try:
        # Eager loading también aquí: en una sola consulta con join
        # obtenemos los favoritos junto con los datos del usuario.
        favoritos = (
            db.query(Favorito)
            .join(Usuario, Favorito.usuario_id == Usuario.id)
            .filter(Favorito.producto_id == producto_id)
            .all()
        )

        for favorito in favoritos:
            # Simulación de envío de notificación/correo (aquí integrarías
            # un proveedor real: FCM para push, SendGrid para email, etc.)
            time.sleep(0.3)
            print(f"✅ Notificación de promoción {promocion_id} enviada a {favorito.usuario.email}")

        return {"notificados": len(favoritos)}
    finally:
        db.close()
