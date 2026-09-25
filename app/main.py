import os
import logging
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from dotenv import load_dotenv
load_dotenv()

from . import models, auth
from .database import get_db, engine, Base
from openai import AsyncOpenAI
from sqlalchemy import func, or_
import joblib
import pandas as pd

from .ml.features import extraer_features_cliente, FEATURE_COLUMNS


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    yield
    if client is not None:
        await client.close()


app = FastAPI(title="Motor Inteligente de Cobranza PluriOne API", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    ).split(",") if origin.strip() and origin.strip() != "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
IA_MODO_DEMO = os.getenv("IA_MODO_DEMO", "true").lower() == "true"
client = (
    AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1",
                timeout=20.0, max_retries=0)
    if GROQ_API_KEY and not IA_MODO_DEMO else None
)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml", "risk_model.joblib")
_modelo_riesgo = None
_columnas_modelo = FEATURE_COLUMNS

if os.path.exists(MODEL_PATH):
    _bundle = joblib.load(MODEL_PATH)
    _modelo_riesgo = _bundle["modelo"]
    _columnas_modelo = _bundle["columnas"]
    print("✅ Modelo de riesgo cargado correctamente.")
else:
    print("⚠️  No se encontró app/ml/risk_model.joblib. Corre 'python -m app.ml.train_model'.")


# ============ AUTENTICACIÓN ============

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login del administrador. Recibe username/password como form-data
    (estándar OAuth2), NO como JSON, por eso el frontend usa
    application/x-www-form-urlencoded.
    """
    admin = db.query(models.Administrador).filter(
        models.Administrador.username == form_data.username
    ).first()

    if not admin or not auth.verificar_password(form_data.password, admin.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not admin.activo:
        raise HTTPException(status_code=403, detail="Esta cuenta está desactivada.")

    access_token = auth.crear_access_token(data={"sub": admin.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "nombre": admin.nombre_completo or admin.username,
    }


@app.get("/auth/me")
def whoami(admin: models.Administrador = Depends(auth.get_admin_actual)):
    """Útil para que el frontend valide si el token guardado sigue siendo válido."""
    return {"username": admin.username, "nombre": admin.nombre_completo}


# ============ ENDPOINTS PROTEGIDOS (requieren sesión) ============

@app.post("/ia/analizar-riesgo/{cliente_id}")
async def analizar_riesgo_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    admin: models.Administrador = Depends(auth.get_admin_actual),
):
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    deudas = cliente.deudas
    monto_pendiente = sum(deuda.saldo_pendiente for deuda in deudas) if deudas else 0.0
    estatus_deudas = [deuda.estatus for deuda in deudas]

    prompt = (
        f"El cliente se llama {cliente.nombre}. "
        f"Tiene un saldo pendiente de {monto_pendiente} pesos. "
        f"El estatus de sus deudas es: {', '.join(estatus_deudas) if estatus_deudas else 'Sin deudas pendientes'}. "
        "Genera un mensaje corto, sumamente empático y profesional ofreciendo una opción de reestructuración de su deuda."
    )

    modo_generacion = "groq"
    try:
        if client is None:
            raise RuntimeError("Modo local")
        response = await client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente de cobranza inteligente, empático y muy profesional. "
                        "REGLAS ESTRICTAS: "
                        "1. NUNCA inventes números de teléfono, correos electrónicos o nombres falsos. "
                        "2. Firma siempre el mensaje exactamente como: 'Cobranza Inteligente PluriOne'. "
                        "3. No inventes canales de contacto ni prometas condiciones financieras específicas."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        mensaje_reestructuracion = response.choices[0].message.content.strip()
    except Exception:
        modo_generacion = "local"
        logging.getLogger(__name__).info("Se utilizó la plantilla local de demostración.")
        mensaje_reestructuracion = (
            f"Estimado/a {cliente.nombre}, entendemos que a veces surgen imprevistos. "
            f"Queremos apoyarte a regularizar tu situación con un plan diseñado a tu medida "
            f"para tu saldo de {monto_pendiente} pesos. Por favor contacta a PluriOne por sus canales oficiales. "
            "Atentamente, Cobranza Inteligente PluriOne."
        )

    nuevo_historial = models.HistorialMensaje(
        cliente_id=cliente.id,
        monto_al_momento=monto_pendiente,
        mensaje_generado=mensaje_reestructuracion,
    )
    db.add(nuevo_historial)
    db.commit()
    db.refresh(nuevo_historial)

    return {
        "cliente_id": cliente.id,
        "cliente_nombre": cliente.nombre,
        "monto_pendiente": monto_pendiente,
        "historial_id": nuevo_historial.id,
        "modo_generacion": modo_generacion,
        "mensaje_empatico": mensaje_reestructuracion,
    }


@app.post("/ia/calcular-riesgo/{cliente_id}")
def calcular_riesgo_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    admin: models.Administrador = Depends(auth.get_admin_actual),
):
    if _modelo_riesgo is None:
        raise HTTPException(
            status_code=503,
            detail="El modelo de riesgo no está entrenado. Corre 'python -m app.ml.train_model'.",
        )

    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    features = extraer_features_cliente(db, cliente)
    X = pd.DataFrame([features])[_columnas_modelo]

    prob_paga_a_tiempo = float(_modelo_riesgo.predict_proba(X)[0][1])
    score_riesgo = round(1 - prob_paga_a_tiempo, 3)

    cliente.score_riesgo = score_riesgo
    if score_riesgo >= 0.66:
        cliente.segmento = "Alto riesgo"
    elif score_riesgo >= 0.33:
        cliente.segmento = "Riesgo medio"
    else:
        cliente.segmento = "Bajo riesgo"

    db.commit()
    db.refresh(cliente)

    return {
        "cliente_id": cliente.id,
        "cliente_nombre": cliente.nombre,
        "features_usadas": features,
        "probabilidad_pago_a_tiempo": round(prob_paga_a_tiempo, 3),
        "score_riesgo": score_riesgo,
        "segmento": cliente.segmento,
    }


@app.get("/api/cartera-priorizada")
def cartera_priorizada(
    db: Session = Depends(get_db),
    admin: models.Administrador = Depends(auth.get_admin_actual),
):
    clientes = db.query(models.Cliente).all()
    resultado = []

    for cliente in clientes:
        deudas_activas = [d for d in cliente.deudas if d.estatus in ("Pendiente", "En Mora")]
        monto_pendiente = sum(d.saldo_pendiente for d in deudas_activas)
        if monto_pendiente <= 0:
            continue

        prioridad = cliente.score_riesgo * monto_pendiente
        resultado.append({
            "cliente_id": cliente.id,
            "cliente_nombre": cliente.nombre,
            "monto_pendiente": monto_pendiente,
            "score_riesgo": cliente.score_riesgo,
            "segmento": cliente.segmento,
            "prioridad": round(prioridad, 2),
        })

    resultado.sort(key=lambda r: r["prioridad"], reverse=True)
    return resultado


@app.get("/ia/historial/{cliente_id}")
def ver_historial_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    admin: models.Administrador = Depends(auth.get_admin_actual),
):
    historial = db.query(models.HistorialMensaje).filter(
        models.HistorialMensaje.cliente_id == cliente_id
    ).order_by(models.HistorialMensaje.fecha_creacion.desc(), models.HistorialMensaje.id.desc()).all()

    if not historial:
        raise HTTPException(status_code=404, detail="No hay historial de mensajes para este cliente")

    return historial


@app.get("/api/metricas")
def obtener_metricas_globales(
    db: Session = Depends(get_db),
    admin: models.Administrador = Depends(auth.get_admin_actual),
):
    total_clientes = db.query(models.Cliente).count()
    saldo_total = db.query(func.sum(models.Deuda.saldo_pendiente)).scalar() or 0.0
    cartera_vencida = db.query(func.sum(models.Deuda.saldo_pendiente)).filter(
        models.Deuda.saldo_pendiente > 0,
        or_(models.Deuda.estatus == "En Mora", models.Deuda.fecha_vencimiento < date.today()),
    ).scalar() or 0.0
    total_estrategias = db.query(models.HistorialMensaje).count()

    monto_original = db.query(func.sum(models.Deuda.monto_total)).scalar() or 0.0
    if monto_original > 0:
        monto_pagado = monto_original - saldo_total
        porcentaje_recuperacion = (monto_pagado / monto_original) * 100
    else:
        porcentaje_recuperacion = 0.0

    return {
        "deudores_activos": total_clientes,
        "cartera_vencida": cartera_vencida,
        "estrategias_ia": total_estrategias,
        "porcentaje_recuperacion": round(porcentaje_recuperacion, 1),
    }


class ComunicacionSimulada(BaseModel):
    cliente_id: int = Field(gt=0)
    canal: Literal["Email", "SMS", "WhatsApp", "Llamada"]
    mensaje: str = Field(min_length=1, max_length=10000)

    @field_validator("mensaje")
    @classmethod
    def mensaje_no_vacio(cls, value):
        if not value.strip():
            raise ValueError("El mensaje no puede estar vacío")
        return value.strip()


@app.post("/api/comunicaciones", status_code=201)
def registrar_comunicacion(
    datos: ComunicacionSimulada,
    db: Session = Depends(get_db),
    admin: models.Administrador = Depends(auth.get_admin_actual),
):
    if db.get(models.Cliente, datos.cliente_id) is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    comunicacion = models.Comunicacion(
        **datos.model_dump(), fecha_envio=date.today(), exitoso=False,
    )
    db.add(comunicacion)
    db.commit()
    db.refresh(comunicacion)
    return {
        "id": comunicacion.id, "cliente_id": comunicacion.cliente_id,
        "canal": comunicacion.canal, "fecha_envio": comunicacion.fecha_envio,
        "mensaje": comunicacion.mensaje, "exitoso": comunicacion.exitoso,
        "simulada": True,
        "detalle": "Modo demostración: la comunicación se registra pero no se envía externamente.",
    }
