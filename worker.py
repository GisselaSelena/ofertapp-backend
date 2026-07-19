"""
Proceso independiente que escucha la cola y ejecuta los jobs.
Se ejecuta con: python worker.py   (en una terminal aparte del servidor)
"""
from rq import Worker
from app.queue import notification_queue, rq_redis

if __name__ == "__main__":
    print("👷 Worker escuchando la cola 'ofertapp-notificaciones'...")
    worker = Worker([notification_queue], connection=rq_redis)
    worker.work()
