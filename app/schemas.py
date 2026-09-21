from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class UsuarioOut(BaseModel):
    id: str
    nombre: str
    email: EmailStr
    rol: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


class ProductoCreate(BaseModel):
    nombre: str
    categoria: Optional[str] = None


class ProductoOut(BaseModel):
    id: str
    nombre: str
    categoria: Optional[str]

    class Config:
        from_attributes = True


class EstablecimientoCreate(BaseModel):
    nombre: str
    direccion: Optional[str] = None


class EstablecimientoOut(BaseModel):
    id: str
    nombre: str
    direccion: Optional[str]

    class Config:
        from_attributes = True


class PrecioCreate(BaseModel):
    producto_id: str
    establecimiento_id: str
    valor: float
    reportado_lat: Optional[float] = None
    reportado_lng: Optional[float] = None
    tiene_foto_evidencia: bool = False


class EstablecimientoMini(BaseModel):
    id: str
    nombre: str
    direccion: Optional[str]

    class Config:
        from_attributes = True


class PrecioOut(BaseModel):
    id: str
    valor: float
    vigente_desde: datetime
    establecimiento: EstablecimientoMini

    class Config:
        from_attributes = True


class FavoritoCreate(BaseModel):
    producto_id: str


class FavoritoOut(BaseModel):
    id: str
    producto: ProductoOut
    created_at: datetime

    class Config:
        from_attributes = True


class PromocionCreate(BaseModel):
    producto_id: str
    establecimiento_id: str
    descripcion: str
    descuento_pct: float
    valido_hasta: datetime