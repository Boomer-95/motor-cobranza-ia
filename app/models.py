from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    telefono = Column(String)
    score_riesgo = Column(Float, default=0.0) 
    segmento = Column(String, default="No definido") 
    
    deudas = relationship("Deuda", back_populates="cliente")
    comunicaciones = relationship("Comunicacion", back_populates="cliente")
    mensajes = relationship("HistorialMensaje", back_populates="cliente")
    pagos = relationship("Pago", back_populates="cliente")

class Deuda(Base):
    __tablename__ = "deudas"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    monto_total = Column(Float)
    saldo_pendiente = Column(Float)
    fecha_vencimiento = Column(Date)
    estatus = Column(String, default="Pendiente")
    probabilidad_pago = Column(Float, nullable=True) 
    
    cliente = relationship("Cliente", back_populates="deudas")

class Comunicacion(Base):
    __tablename__ = "comunicaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    canal = Column(String)
    fecha_envio = Column(Date)
    mensaje = Column(String)
    exitoso = Column(Boolean, default=True)
    
    cliente = relationship("Cliente", back_populates="comunicaciones")

class HistorialMensaje(Base):
    __tablename__ = "historial_mensajes"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    monto_al_momento = Column(Float)
    mensaje_generado = Column(Text)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    cliente = relationship("Cliente", back_populates="mensajes")


class Pago(Base):
    """Historial de pagos: la materia prima del modelo predictivo de riesgo."""
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))

    monto = Column(Float, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    fecha_pago = Column(Date, nullable=True)
    dias_atraso = Column(Integer, nullable=True)
    canal_contacto = Column(String, nullable=True)
    se_recuperó = Column(Boolean, default=True)

    cliente = relationship("Cliente", back_populates="pagos")


class Administrador(Base):
    """
    Usuarios que pueden iniciar sesión en el dashboard.
    No hay endpoint de registro público a propósito: los administradores
    se crean con app/seed_admin.py, para que solo personal autorizado
    tenga cuenta (nadie se auto-registra desde el frontend).
    """
    __tablename__ = "administradores"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    nombre_completo = Column(String, nullable=True)
    activo = Column(Boolean, default=True)
