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
    # historial de pagos, es la materia prima para entrenar el modelo de riesgo
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
    """
    Historial de pagos (resueltos) de cada cliente.
    Esta tabla es la que le da 'memoria' al modelo predictivo: le dice si,
    en el pasado, el cliente pagó a tiempo, tarde, o no pagó.
    Cada vez que una Deuda se cierra (se paga o se da de baja), se debe
    crear un registro aquí.
    """
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))

    monto = Column(Float, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    fecha_pago = Column(Date, nullable=True)  # NULL = todavía no paga / nunca pagó
    # dias_atraso: negativo o 0 = pagó a tiempo o antes; positivo = días de atraso
    dias_atraso = Column(Integer, nullable=True)
    canal_contacto = Column(String, nullable=True)  # SMS, WhatsApp, Email, Llamada
    se_recuperó = Column(Boolean, default=True)  # False si nunca se logró cobrar

    cliente = relationship("Cliente", back_populates="pagos")