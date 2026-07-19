from fastapi import FastAPI

from app.database import Base, engine
from app.routers import auth, productos, precios, favoritos, promociones

app = FastAPI(title="OfertApp API", version="1.0.0")

# Crea las tablas automáticamente en desarrollo a partir de los modelos.
# (En un proyecto más avanzado usarías Alembic para versionar el esquema.)
Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(productos.router)
app.include_router(precios.router)
app.include_router(favoritos.router)
app.include_router(promociones.router)


@app.get("/health")
def health():
    return {"status": "ok"}
