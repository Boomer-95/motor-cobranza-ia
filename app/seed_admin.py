"""
Crea un administrador con usuario/contraseña tomados de tu .env.
No existe endpoint de registro público a propósito: solo quien tiene
acceso al servidor (y a este script) puede crear cuentas.

Uso:
    python -m app.seed_admin
"""
import os
from app.database import SessionLocal
from app import models
from app.auth import hash_password


def crear_admin():
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    nombre = os.getenv("ADMIN_NOMBRE", "Administrador")

    if not username or not password:
        print("Faltan ADMIN_USERNAME y/o ADMIN_PASSWORD en tu .env")
        return

    db = SessionLocal()
    existente = db.query(models.Administrador).filter(
        models.Administrador.username == username
    ).first()

    if existente:
        print(f"Ya existe un administrador con username '{username}'. No se creó nada.")
        db.close()
        return

    admin = models.Administrador(
        username=username,
        hashed_password=hash_password(password),
        nombre_completo=nombre,
        activo=True,
    )
    db.add(admin)
    db.commit()
    db.close()
    print(f"Administrador '{username}' creado correctamente.")


if __name__ == "__main__":
    crear_admin()
