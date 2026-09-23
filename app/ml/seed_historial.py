"""
Puebla la tabla `Pago` con historial simulado para los clientes que ya
creaste con seed.py (Ana, Luis, Carlos). Esto es solo para que puedas
PROBAR el endpoint /ia/calcular-riesgo/{id} con datos que ya existen
en tu DB, mientras se acumula historial real.

Uso:
    python -m app.ml.seed_historial
"""
import datetime
import random
from app.database import SessionLocal
from app import models


def poblar_historial():
    db = SessionLocal()

    if db.query(models.Pago).first():
        print("Ya hay historial de pagos. No se insertó nada nuevo.")
        db.close()
        return

    clientes = db.query(models.Cliente).all()
    if not clientes:
        print("No hay clientes. Corre primero seed.py")
        db.close()
        return

    # Perfil de comportamiento distinto por cliente, para que el score
    # de riesgo salga distinto entre ellos (útil para la demo).
    perfiles = {
        "Ana Gómez": {"pct_tarde": 0.7, "atraso_max": 25},   # cliente riesgoso
        "Luis Ramírez": {"pct_tarde": 0.1, "atraso_max": 3}, # cliente cumplido
        "Carlos Ruiz": {"pct_tarde": 0.4, "atraso_max": 12}, # cliente intermedio
    }

    canales = ["SMS", "WhatsApp", "Email"]
    hoy = datetime.date.today()

    for cliente in clientes:
        perfil = perfiles.get(cliente.nombre, {"pct_tarde": 0.3, "atraso_max": 10})
        for i in range(12):  # 12 pagos históricos simulados (~1 año)
            fecha_venc = hoy - datetime.timedelta(days=30 * (12 - i))
            paga_tarde = random.random() < perfil["pct_tarde"]
            dias_atraso = random.randint(1, perfil["atraso_max"]) if paga_tarde else random.randint(-5, 0)
            fecha_pago = fecha_venc + datetime.timedelta(days=dias_atraso)

            pago = models.Pago(
                cliente_id=cliente.id,
                monto=round(random.uniform(1000, 10000), 2),
                fecha_vencimiento=fecha_venc,
                fecha_pago=fecha_pago,
                dias_atraso=dias_atraso,
                canal_contacto=random.choice(canales),
                se_recuperó=True,
            )
            db.add(pago)

    db.commit()
    db.close()
    print("¡Historial de pagos simulado insertado con éxito!")


if __name__ == "__main__":
    poblar_historial()