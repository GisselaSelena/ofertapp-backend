import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    favoritos = relationship("Favorito", back_populates="usuario", lazy="select")


class Establecimiento(Base):
    __tablename__ = "establecimientos"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nombre = Column(String, nullable=False)
    direccion = Column(String, nullable=True)

    precios = relationship("Precio", back_populates="establecimiento", lazy="select")


class Producto(Base):
    __tablename__ = "productos"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    nombre = Column(String, nullable=False, index=True)
    categoria = Column(String, nullable=True)

    precios = relationship("Precio", back_populates="producto", lazy="select")
    favoritos = relationship("Favorito", back_populates="producto", lazy="select")
    promociones = relationship("Promocion", back_populates="producto", lazy="select")


class Precio(Base):
    """
    Registro HISTÓRICO de precio: cada fila representa el valor de un
    producto en un establecimiento durante un período de vigencia.

    - vigente_desde: cuándo empezó a regir este valor.
    - vigente_hasta: cuándo dejó de regir (NULL = sigue vigente ahora).
    - fuente_usuario_id: quién registró/actualizó este precio, para
      poder rastrear el origen y detectar actualizaciones no
      autorizadas o sospechosas.

    En vez de hacer UPDATE sobre el precio vigente cuando cambia, se
    INSERTA una fila nueva y se cierra la anterior (se le asigna
    vigente_hasta). Así se conserva el historial completo de cómo varió
    el precio en el tiempo, en vez de perder esa información con cada
    actualización.
    """
    __tablename__ = "precios"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    producto_id = Column(UUID(as_uuid=False), ForeignKey("productos.id"), nullable=False)
    establecimiento_id = Column(UUID(as_uuid=False), ForeignKey("establecimientos.id"), nullable=False)
    valor = Column(Float, nullable=False)

    vigente_desde = Column(DateTime, default=datetime.utcnow, nullable=False)
    vigente_hasta = Column(DateTime, nullable=True)  # NULL = precio actual

    # Fuente/autorización: quién registró este precio. Por ahora, el
    # usuario autenticado que hizo la petición (más adelante podría
    # ampliarse a un rol "establecimiento verificado" o "admin").
    fuente_usuario_id = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)

    producto = relationship("Producto", back_populates="precios")
    establecimiento = relationship("Establecimiento", back_populates="precios")
    fuente_usuario = relationship("Usuario")


class Favorito(Base):
    __tablename__ = "favoritos"
    __table_args__ = (UniqueConstraint("usuario_id", "producto_id", name="uq_usuario_producto_favorito"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    usuario_id = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)
    producto_id = Column(UUID(as_uuid=False), ForeignKey("productos.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="favoritos")
    producto = relationship("Producto", back_populates="favoritos")


class Promocion(Base):
    __tablename__ = "promociones"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    producto_id = Column(UUID(as_uuid=False), ForeignKey("productos.id"), nullable=False)
    establecimiento_id = Column(UUID(as_uuid=False), ForeignKey("establecimientos.id"), nullable=False)
    descripcion = Column(Text, nullable=False)
    descuento_pct = Column(Float, nullable=False)
    valido_hasta = Column(DateTime, nullable=False)

    producto = relationship("Producto", back_populates="promociones")
    establecimiento = relationship("Establecimiento")
