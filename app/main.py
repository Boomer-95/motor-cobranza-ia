import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from . import models, database
from openai import AsyncOpenAI
from sqlalchemy import func
import joblib
import pandas as pd

from .ml.features import extraer_features_cliente, FEATURE_COLUMNS

load_dotenv()

app = FastAPI(title="Motor Inteligente de Cobranza API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError(
        "Falta GROQ_API_KEY en tu archivo .env. No la pegues en el código."
    )

client = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

models.Base.metadata.create_all(bind=database.engine)


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml", "risk_model.joblib")
_modelo_riesgo = None
_columnas_modelo = FEATURE_COLUMNS

if os.path.exists(MODEL_PATH):
    _bundle = joblib.load(MODEL_PATH)
    _modelo_riesgo = _bundle["modelo"]
    _columnas_modelo = _bundle["columnas"]
    print("✅ Modelo de riesgo cargado correctamente.")
else:
    print(
        "⚠️  No se encontró app/ml/risk_model.joblib. "
        "Corre 'python -m app.ml.train_model' para entrenarlo."
    )


@app.post("/ia/analizar-riesgo/{cliente_id}")
async def analizar_riesgo_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """
    Genera el MENSAJE empático de cobranza usando el LLM (Groq).
    Esta parte NO predice nada: solo redacta texto con un modelo de
    lenguaje ya entrenado por terceros (por eso no requiere "entrenar" IA).
    """
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

    try:
        response = await client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente de cobranza inteligente, empático y muy profesional. "
                        "REGLAS ESTRICTAS: "
                        "1. NUNCA inventes números de teléfono, correos electrónicos o nombres falsos. "
                        "2. Firma siempre el mensaje exactamente como: 'Cobranza Inteligente PluriOne'. "
                        "3. Si ofreces un canal de contacto, pide que llamen exclusivamente al 55-9999-0000."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        mensaje_reestructuracion = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ ERROR DE LA IA: {e}")
        mensaje_reestructuracion = (
            f"Estimado/a {cliente.nombre}, entendemos que a veces surgen imprevistos. "
            f"Queremos apoyarte a regularizar tu situación con un plan diseñado a tu medida "
            f"para tu saldo de {monto_pendiente} pesos. Por favor contáctanos al 55-9999-0000. "
            "Atentamente, Cobranza Inteligente TESOEM."
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
        "mensaje_empatico": mensaje_reestructuracion,
    }


@app.post("/ia/calcular-riesgo/{cliente_id}")
def calcular_riesgo_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """
    Calcula el score_riesgo del cliente con el modelo de scikit-learn
    (RandomForest entrenado en app/ml/train_model.py). Esta es la parte
    PREDICTIVA real del proyecto, separada del LLM que redacta texto.
    """
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
    score_riesgo = round(1 - prob_paga_a_tiempo, 3)  # 0 = bajo riesgo, 1 = alto riesgo

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
def cartera_priorizada(db: Session = Depends(get_db)):
    """
    Objetivo del proyecto: 'Priorizar por riesgo financiero (deuda grande)'.
    Ordena a los clientes por (score_riesgo * monto_pendiente) descendente,
    para que cobranza atienda primero a quien representa más riesgo Y más dinero.
    """
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
def ver_historial_cliente(cliente_id: int, db: Session = Depends(get_db)):
    historial = db.query(models.HistorialMensaje).filter(
        models.HistorialMensaje.cliente_id == cliente_id
    ).all()

    if not historial:
        raise HTTPException(status_code=404, detail="No hay historial de mensajes para este cliente")

    return historial


@app.get("/api/metricas")
def obtener_metricas_globales(db: Session = Depends(get_db)):
    total_clientes = db.query(models.Cliente).count()
    cartera_vencida = db.query(func.sum(models.Deuda.saldo_pendiente)).scalar() or 0.0
    total_estrategias = db.query(models.HistorialMensaje).count()

    monto_original = db.query(func.sum(models.Deuda.monto_total)).scalar() or 0.0
    if monto_original > 0:
        monto_pagado = monto_original - cartera_vencida
        porcentaje_recuperacion = (monto_pagado / monto_original) * 100
    else:
        porcentaje_recuperacion = 0.0

    return {
        "deudores_activos": total_clientes,
        "cartera_vencida": cartera_vencida,
        "estrategias_ia": total_estrategias,
        "porcentaje_recuperacion": round(porcentaje_recuperacion, 1),
    }