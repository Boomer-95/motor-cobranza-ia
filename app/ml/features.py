"""
Feature engineering para el motor de riesgo.

Aquí convertimos el historial "crudo" de un cliente (tablas Pago, Deuda)
en un vector de números que el modelo de scikit-learn puede entender.

IMPORTANTE: el orden de FEATURE_COLUMNS debe ser IDÉNTICO en entrenamiento
(train_model.py) y en producción (main.py), o el modelo va a leer los
números en el orden equivocado y dar predicciones sin sentido.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models

FEATURE_COLUMNS = [
    "pct_pagos_tarde",       # % de pagos históricos que llegaron tarde (0-1)
    "promedio_dias_atraso",  # promedio de días de atraso en pagos tardíos
    "num_pagos_historicos",  # cuántos pagos/deudas ha tenido el cliente en total
    "monto_promedio_pago",   # monto promedio de sus pagos históricos
    "monto_pendiente_actual",# suma de saldo_pendiente en deudas activas hoy
    "num_deudas_activas",    # cuántas deudas tiene abiertas ahora mismo
]


def extraer_features_cliente(db: Session, cliente: "models.Cliente") -> dict:
    """
    Calcula las features de UN cliente a partir de su historial real en la DB.
    Se usa tanto para producción (calcular su score_riesgo actual) como
    referencia de qué debe generar train_model.py de forma sintética.
    """
    pagos = db.query(models.Pago).filter(models.Pago.cliente_id == cliente.id).all()

    pagos_con_fecha = [p for p in pagos if p.dias_atraso is not None]
    num_pagos_historicos = len(pagos_con_fecha)

    if num_pagos_historicos > 0:
        pagos_tarde = [p for p in pagos_con_fecha if p.dias_atraso > 0]
        pct_pagos_tarde = len(pagos_tarde) / num_pagos_historicos
        promedio_dias_atraso = (
            sum(p.dias_atraso for p in pagos_tarde) / len(pagos_tarde)
            if pagos_tarde else 0.0
        )
        monto_promedio_pago = sum(p.monto for p in pagos_con_fecha) / num_pagos_historicos
    else:
        # Cliente nuevo sin historial: usamos valores "neutros" (ni bueno ni malo)
        # en vez de 0, para no castigarlo ni premiarlo injustamente.
        pct_pagos_tarde = 0.3
        promedio_dias_atraso = 5.0
        monto_promedio_pago = 0.0

    deudas_activas = [d for d in cliente.deudas if d.saldo_pendiente > 0]
    monto_pendiente_actual = sum(d.saldo_pendiente for d in deudas_activas)
    num_deudas_activas = len(deudas_activas)

    return {
        "pct_pagos_tarde": pct_pagos_tarde,
        "promedio_dias_atraso": promedio_dias_atraso,
        "num_pagos_historicos": num_pagos_historicos,
        "monto_promedio_pago": monto_promedio_pago,
        "monto_pendiente_actual": monto_pendiente_actual,
        "num_deudas_activas": num_deudas_activas,
    }