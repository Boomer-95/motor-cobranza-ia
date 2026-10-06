"""Valida exclusivamente la base restaurada de entrega en el socket temporal."""
import json
import os
from pathlib import Path
import re
import socket
import sys


def validar(url, archivo):
    from sqlalchemy.engine import make_url
    destino = make_url(url)
    if destino.database != 'motor_cobranza_validacion_tmp':
        raise ValueError('Solo se admite la base temporal de validación.')
    from seed_entrega import preparar_entorno
    preparar_entorno(destino.set(database='motor_cobranza_entrega_tmp').render_as_string(hide_password=False))
    os.environ['DATABASE_URL'] = url
    # Revisión del SQL sin imprimir coincidencias potencialmente sensibles.
    sql = Path(archivo).read_text()
    prohibidos = [r'Bearer\s+\S+', r'(?:TWILIO_AUTH_TOKEN|SENDGRID_API_KEY|GROQ_API_KEY|CLIENT_SECRET)',
                  r'\b(?:AC|SM|MM|SK)[a-fA-F0-9]{32}\b', r'\b(?:sk-|gsk_|SG\.)[A-Za-z0-9_-]+',
                  r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', r'\+[1-9][0-9]{7,14}',
                  r'OWNER TO', r'^(?:GRANT|REVOKE) ', r'postgres(?:ql)?://']
    if any(re.search(p, sql, re.I | re.M) for p in prohibidos):
        raise ValueError('Revisión de seguridad SQL fallida; contenido no mostrado.')
    correos = re.findall(r'[\w.+-]+@[\w.-]+', sql)
    if len(correos) != 15 or any(not re.fullmatch(r'cliente\d{2}@example\.invalid', c) for c in correos):
        raise ValueError('Correos del dump fuera de la lista ficticia permitida.')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from sqlalchemy import inspect, text
    from app.database import engine, Base
    from app import models  # noqa: F401
    esperados = dict(clientes=15, deudas=23, pagos=40, historial_mensajes=24,
                     comunicaciones=24, metricas_snapshots=15, administradores=0)
    with engine.connect() as conn:
        inspector = inspect(conn)
        assert set(inspector.get_table_names()) == set(esperados)
        for nombre, tabla in Base.metadata.tables.items():
            assert {c['name'] for c in inspector.get_columns(nombre)} == set(tabla.columns.keys()), nombre
            fks = {(tuple(f['constrained_columns']), f['referred_table'], tuple(f['referred_columns'])) for f in inspector.get_foreign_keys(nombre)}
            for fk in tabla.foreign_keys:
                assert ((fk.parent.name,), fk.column.table.name, (fk.column.name,)) in fks
            indices = {i['name'] for i in inspector.get_indexes(nombre)}
            assert {i.name for i in tabla.indexes} <= indices
        conteos = {t: conn.scalar(text(f'SELECT count(*) FROM {t}')) for t in esperados}
        assert conteos == esperados, conteos
        comprobaciones = {
            'deuda_vencida': "SELECT count(*) FROM deudas WHERE saldo_pendiente > 0 AND fecha_vencimiento < CURRENT_DATE",
            'deuda_futura': "SELECT count(*) FROM deudas WHERE saldo_pendiente > 0 AND fecha_vencimiento > CURRENT_DATE",
            'sin_evaluar': "SELECT count(*) FROM clientes WHERE segmento = 'No definido' AND score_riesgo IS NULL",
            'estrategias': 'SELECT count(*) FROM historial_mensajes',
            'comunicaciones_con_estrategia': 'SELECT count(*) FROM comunicaciones c JOIN historial_mensajes h ON h.id=c.estrategia_id AND h.cliente_id=c.cliente_id',
            'fechas_snapshots': 'SELECT count(DISTINCT fecha) FROM metricas_snapshots',
        }
        resultados = {k: conn.scalar(text(v)) for k, v in comprobaciones.items()}
        assert all(v > 0 for v in resultados.values()), resultados
        assert resultados['fechas_snapshots'] == 15
        assert conn.scalar(text('SELECT count(*) FROM clientes WHERE telefono IS NOT NULL')) == 0
        assert conn.scalar(text("SELECT count(*) FROM comunicaciones WHERE modo IS DISTINCT FROM 'simulado' OR exitoso IS DISTINCT FROM false OR external_id IS NOT NULL OR provider IS NOT NULL OR provider_status IS NOT NULL OR error_tecnico IS NOT NULL")) == 0
        # Cada deuda cumple monto original = saldo + pagos; no pagos sueltos.
        assert conn.scalar(text('SELECT count(*) FROM pagos WHERE deuda_id IS NULL')) == 0
        assert conn.scalar(text('SELECT count(*) FROM deudas d WHERE abs(d.monto_total - d.saldo_pendiente - COALESCE((SELECT sum(p.monto) FROM pagos p WHERE p.deuda_id=d.id),0)) > 0.01')) == 0
        assert conn.scalar(text('SELECT count(*) FROM pagos p JOIN deudas d ON d.id=p.deuda_id WHERE p.cliente_id<>d.cliente_id OR p.dias_atraso<>p.fecha_pago-p.fecha_vencimiento')) == 0
        # Comprobar estado de secuencias restauradas sin consumir IDs ni insertar datos.
        for tabla in Base.metadata.tables:
            secuencia = conn.scalar(text("SELECT pg_get_serial_sequence(:tabla, 'id')"), {'tabla': tabla})
            assert secuencia
            estado = conn.execute(text(f'SELECT last_value, is_called FROM {secuencia}')).one()
            maximo = conn.scalar(text(f'SELECT COALESCE(max(id), 0) FROM {tabla}'))
            assert estado[0] >= maximo
    # Entra se sustituye SOLO en este TestClient local; jamás se cambian credenciales o código.
    conectar = socket.socket.connect
    def solo_socket_local(sock, address):
        if sock.family != socket.AF_UNIX:
            raise AssertionError('Conexiones externas prohibidas durante validación demo.')
        return conectar(sock, address)
    socket.socket.connect = solo_socket_local
    from fastapi.testclient import TestClient
    from app import main, auth
    main.app.dependency_overrides[auth.get_entra_user] = lambda: {'oid': 'demo-local', 'name': 'Evaluador ficticio'}
    rutas = ['/api/metricas', '/api/clientes', '/api/clientes/1', '/api/cartera-priorizada',
             '/ia/historial/1', '/api/analitica/resumen?dias=30',
             '/api/analitica/canales?dias=30', '/api/analitica/evolucion?dias=30', '/api/integraciones/estado']
    estados = {}
    try:
        # Sin lifespan: la validación no crea tablas; el SQL es la única fuente del esquema.
        cliente = TestClient(main.app)
        for ruta in rutas:
            respuesta = cliente.get(ruta)
            assert respuesta.status_code == 200, (ruta, respuesta.status_code)
            estados[ruta] = respuesta.status_code
            if '/resumen?' in ruta:
                assert respuesta.json()['monto_recuperado_post_ia'] == 0
            if '/evolucion?' in ruta:
                assert len(respuesta.json()) >= 15
        cliente.close()
    finally:
        main.app.dependency_overrides.clear()
        socket.socket.connect = conectar
        engine.dispose()
    print(json.dumps({'conteos_importados': conteos, 'comprobaciones': resultados,
                      'endpoints': estados, 'seguridad_sql': 'OK'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    validar(sys.argv[1], sys.argv[2])
