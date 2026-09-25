from app.database import SessionLocal, Base, engine
from app.models import Cliente, Deuda
import datetime

def poblar_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Verificamos si ya hay datos para no duplicarlos
    if db.query(Cliente).first():
        print("La base de datos ya tiene información. No se insertó nada nuevo.")
        db.close()
        return

    # 1. Crear Clientes
    c1 = Cliente(nombre="Ana Gómez", email="ana@ejemplo.com", telefono="5551234567")
    c2 = Cliente(nombre="Luis Ramírez", email="luis@ejemplo.com", telefono="5559876543")
    c3 = Cliente(nombre="Carlos Ruiz", email="carlos@ejemplo.com", telefono="5554567890")

    db.add_all([c1, c2, c3])
    db.commit() # Guardamos para que se generen los IDs

    # 2. Crear Deudas (Simulando fechas de vencimiento realistas)
    d1 = Deuda(
        cliente_id=c1.id, monto_total=15000.0, saldo_pendiente=15000.0, 
        fecha_vencimiento=datetime.date.today() - datetime.timedelta(days=40), estatus="En Mora"
    )
    d2 = Deuda(
        cliente_id=c2.id, monto_total=5000.0, saldo_pendiente=2500.0, 
        fecha_vencimiento=datetime.date.today() + datetime.timedelta(days=20), estatus="Pendiente"
    )
    d3 = Deuda(
        cliente_id=c3.id, monto_total=8000.0, saldo_pendiente=8000.0, 
        fecha_vencimiento=datetime.date.today() - datetime.timedelta(days=70), estatus="En Mora"
    )

    db.add_all([d1, d2, d3])
    db.commit()
    db.close()
    
    print("¡Base de datos poblada con éxito!")

if __name__ == "__main__":
    poblar_db()