from rq import Queue
import redis
from app.config import settings

rq_redis = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=False)

# Cola de trabajos, respaldada por Redis. Solo "publica" tareas, no las
# ejecuta: eso lo hace el proceso worker (correr con: rq worker ofertapp-notificaciones)
notification_queue = Queue("ofertapp-notificaciones", connection=rq_redis)


def encolar_notificacion_promocion(promocion_id: str, producto_id: str):
    """
    Encola la notificación SIN bloquear la respuesta HTTP de "crear
    promoción". El endpoint responde de inmediato; el envío real ocurre
    después, en el worker.
    """
    job = notification_queue.enqueue(
        "app.tasks.notificar_favoritos",
        promocion_id,
        producto_id,
        job_timeout=60,
    )
    print(f"📨 Job encolado ({job.id}): notificar promoción {promocion_id}")
    return job.id
