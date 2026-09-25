"""Migración aditiva e idempotente. Ejecutar antes de iniciar el backend actualizado."""
from sqlalchemy import inspect, text
from .database import engine, Base
from . import models  # noqa: F401


def migrar(bind=engine):
    with bind.begin() as conn:
        if conn.dialect.name == 'postgresql':
            conn.execute(text('SELECT pg_advisory_xact_lock(71924001)'))
        Base.metadata.create_all(conn)
        cambios = {
            'pagos': {'deuda_id': 'INTEGER REFERENCES deudas(id)'},
            'clientes': {'probabilidad_pago_a_tiempo': 'FLOAT'},
            'historial_mensajes': {'contexto_hash': 'VARCHAR(64)'},
        }
        for tabla, columnas in cambios.items():
            existentes = {c['name'] for c in inspect(conn).get_columns(tabla)}
            for nombre, tipo in columnas.items():
                if nombre not in existentes:
                    conn.execute(text(f'ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}'))
        conn.execute(text('CREATE INDEX IF NOT EXISTS ix_pagos_deuda_id ON pagos (deuda_id)'))


if __name__ == '__main__':
    migrar()
    print('Migración completada; datos existentes conservados.')
