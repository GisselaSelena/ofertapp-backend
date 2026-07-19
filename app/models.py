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

    # LAZY LOADING (por defecto en SQLAlchemy): los favoritos de un usuario
    # solo se cargan cuando se accede explícitamente a `usuario.favoritos`,
    # por ejemplo en la pantalla "Mis favoritos". No tiene sentido traerlos
    # siempre que se autentica o se consulta un usuario.
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
    promociones = relationship("Promocion", back_populates="producto", lazy="select")


class Precio(Base):
    """
    Entidad clave del negocio: un precio de un Producto en un Establecimiento.
    Comparar precios entre establecimientos es la operación más costosa y la
    que tiene riesgo real de N+1 (por cada precio hay que saber a qué
    establecimiento pertenece).
    """
    __tablename__ = "precios"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    producto_id = Column(UUID(as_uuid=False), ForeignKey("productos.id"), nullable=False)
    establecimiento_id = Column(UUID(as_uuid=False), ForeignKey("establecimientos.id"), nullable=False)
    valor = Column(Float, nullable=False)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    producto = relationship("Producto", back_populates="precios")

    # EAGER LOADING (ver productos.py): cuando se listan los precios de un
    # producto para comparar, SIEMPRE se necesita el nombre del
    # establecimiento -> se carga con selectinload/joinedload en la consulta,
    # evitando 1 consulta adicional por cada precio (N+1).
    establecimiento = relationship("Establecimiento", back_populates="precios")


class Favorito(Base):
    __tablename__ = "favoritos"
    __table_args__ = (UniqueConstraint("usuario_id", "producto_id", name="uq_usuario_producto_favorito"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    usuario_id = Column(UUID(as_uuid=False), ForeignKey("usuarios.id"), nullable=False)
    producto_id = Column(UUID(as_uuid=False), ForeignKey("productos.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="favoritos")
    producto = relationship("Producto")


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
