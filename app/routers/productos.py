from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, CurrentUser
from app.models import Producto, Establecimiento
from app.schemas import ProductoCreate, ProductoOut, EstablecimientoCreate, EstablecimientoOut

router = APIRouter(prefix="/api", tags=["productos"])


@router.post("/productos", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear_producto(
    data: ProductoCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    producto = Producto(nombre=data.nombre, categoria=data.categoria)
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


@router.get("/productos", response_model=list[ProductoOut])
def listar_productos(db: Session = Depends(get_db)):
    return db.query(Producto).order_by(Producto.nombre).all()


@router.post("/establecimientos", response_model=EstablecimientoOut, status_code=status.HTTP_201_CREATED)
def crear_establecimiento(
    data: EstablecimientoCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    establecimiento = Establecimiento(nombre=data.nombre, direccion=data.direccion)
    db.add(establecimiento)
    db.commit()
    db.refresh(establecimiento)
    return establecimiento


@router.get("/establecimientos", response_model=list[EstablecimientoOut])
def listar_establecimientos(db: Session = Depends(get_db)):
    return db.query(Establecimiento).order_by(Establecimiento.nombre).all()
