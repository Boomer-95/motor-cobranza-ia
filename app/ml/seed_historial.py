"""Historial exclusivamente sintético, reproducible e idempotente por cliente demo."""
from datetime import date, timedelta
import random
from app.database import SessionLocal
from app.migrate import migrar
from app.models import Cliente, Pago
from app.seed import EMAILS, LEGACY_EMAILS


def poblar_historial():
    migrar()
    with SessionLocal.begin() as db:
        for i, email in enumerate(EMAILS):
            cliente = db.query(Cliente).filter(Cliente.email.in_([email, LEGACY_EMAILS.get(email, email)])).first()
            if not cliente or db.query(Pago.id).filter_by(cliente_id=cliente.id).first():
                continue
            rng = random.Random(42 + i)
            for n in range(12):
                vencimiento = date(2025, 1, 1) + timedelta(days=30 * n)
                atraso = rng.randint(1, [25, 3, 12][i % 3]) if rng.random() < [.7, .1, .4][i % 3] else rng.randint(-5, 0)
                db.add(Pago(cliente_id=cliente.id, monto=round(rng.uniform(1000, 10000), 2),
                    fecha_vencimiento=vencimiento, fecha_pago=vencimiento + timedelta(days=atraso),
                    dias_atraso=atraso, canal_contacto='Demo sintética', se_recuperó=True))
    print('Historial sintético creado solo para clientes demo sin pagos existentes.')


if __name__ == '__main__':
    poblar_historial()
