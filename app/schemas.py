from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# ---- Usuario / Auth ----
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

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ---- Producto / Establecimiento ----
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


# ---- Precio ----
class PrecioCreate(BaseModel):
    producto_id: str
    establecimiento_id: str
    valor: float


class EstablecimientoMini(BaseModel):
    id: str
    nombre: str
    direccion: Optional[str]

    class Config:
        from_attributes = True


class PrecioOut(BaseModel):
    id: str
    valor: float
    actualizado_en: datetime
    establecimiento: EstablecimientoMini

    class Config:
        from_attributes = True


# ---- Favorito ----
class FavoritoCreate(BaseModel):
    producto_id: str


class FavoritoOut(BaseModel):
    id: str
    producto: ProductoOut
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Promoción ----
class PromocionCreate(BaseModel):
    producto_id: str
    establecimiento_id: str
    descripcion: str
    descuento_pct: float
    valido_hasta: datetime
