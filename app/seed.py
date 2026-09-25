"""Datos ficticios de demostración. No modifica clientes ni deudas existentes."""
from datetime import date, timedelta
from app.database import SessionLocal
from app.migrate import migrar
from app.models import Cliente, Deuda

NOMBRES = ['Ana Gómez', 'Luis Ramírez', 'Carlos Ruiz', 'Marta Solís', 'Diego Luna',
           'Elena Ríos', 'Pedro Vega', 'Lucía Torres', 'Jorge Soto', 'Sara Méndez',
           'Raúl Pineda', 'Clara Vidal', 'Ana Gómez', 'Pablo Cano', 'Inés Robles']
EMAILS = ['ana@example.invalid', 'luis@example.invalid', 'carlos@example.invalid'] + [
    f'cliente{i:02d}@example.invalid' for i in range(4, 16)]
LEGACY_EMAILS = dict(zip(EMAILS[:3], ['ana@ejemplo.com', 'luis@ejemplo.com', 'carlos@ejemplo.com']))


def poblar_db():
    migrar()
    with SessionLocal.begin() as db:
        for i, (nombre, email) in enumerate(zip(NOMBRES, EMAILS)):
            cliente = db.query(Cliente).filter(Cliente.email.in_([email, LEGACY_EMAILS.get(email, email)])).first()
            if cliente:
                # La cartera existente puede haber recibido pagos. Nunca reponer deudas.
                continue
            cliente = Cliente(nombre=nombre, email=email, telefono=None)
            db.add(cliente)
            db.flush()
            cantidad = 2 if i in (3, 7, 11) else 1
            for j in range(cantidad):
                monto = [15000, 5000, 8000, 45000, 350, 1200, 22000][i % 7] + j * 1500
                dias = [-40, 20, -70, -5, 30, 0, -15][i % 7] + j * 40
                saldo = 0 if i == 14 else monto / 2 if i % 4 == 1 else monto
                db.add(Deuda(cliente_id=cliente.id, monto_total=monto, saldo_pendiente=saldo,
                    fecha_vencimiento=date.today() + timedelta(days=dias),
                    estatus='Pagada' if saldo == 0 else 'En Mora' if dias < 0 else 'Pendiente'))
    print('Clientes ficticios faltantes creados; cartera existente conservada.')


if __name__ == '__main__':
    poblar_db()
