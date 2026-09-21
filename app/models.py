import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
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
    rol = Column(String, nullable=False, default="usuario", server_default="usuario")

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
    __tablename__ = "precios"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    producto_id = Column(UUID(as_uuid=False), ForeignKey("productos.id"), nullable=False)
    establecimiento_id = Column(UUID(as_uuid=False), ForeignKey("establecimientos.id"), nullable=False)
    valor = Column(Float, nullable=False)

    vigente_desde = Column(DateTime, default=datetime.utcnow, nullable=False)
    vigente_hasta = Column(DateTime, nullable=True)

    fuente_usuario_id = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)

    reportado_lat = Column(Float, nullable=True)
    reportado_lng = Column(Float, nullable=True)
    tiene_foto_evidencia = Column(Boolean, nullable=False, default=False, server_default="false")

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