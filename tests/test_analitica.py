from datetime import date, datetime, timedelta
import pytest
from sqlalchemy import create_engine, inspect, text
from app import models as m
from app.migrate import migrar


@pytest.mark.parametrize('ruta', ['resumen', 'evolucion', 'canales'])
def test_entra_y_periodos(client, headers, ruta):
    assert client.get(f'/api/analitica/{ruta}').status_code == 401
    assert client.get(f'/api/analitica/{ruta}', headers={'Authorization': 'Bearer invalido'}).status_code == 401
    for dias in (30, 90, 180, 365):
        assert client.get(f'/api/analitica/{ruta}?dias={dias}', headers=headers).status_code == 200
    assert client.get(f'/api/analitica/{ruta}?dias=31', headers=headers).status_code == 422


def crear(db):
    c = m.Cliente(nombre='Prueba', score_riesgo=.8)
    db.add(c); db.flush()
    db.add(m.Deuda(cliente_id=c.id, monto_total=1000, saldo_pendiente=600,
                   fecha_vencimiento=date.today() - timedelta(days=1)))
    estrategia = m.HistorialMensaje(cliente_id=c.id, mensaje_generado='Estrategia', fecha_creacion=datetime.now())
    db.add(estrategia); db.flush()
    return c, estrategia


def contacto(db, c, e, dias, canal='Email', **kwargs):
    registro = m.Comunicacion(cliente_id=c.id, estrategia_id=e.id if e else None,
                             canal=canal, fecha_envio=date.today() - timedelta(days=dias),
                             exitoso=True, modo='real', estado='Enviado')
    for k, v in kwargs.items():
        setattr(registro, k, v)
    db.add(registro)
    return registro


def pago(db, c, dias, monto=100, **kwargs):
    p = m.Pago(cliente_id=c.id, monto=monto, fecha_pago=date.today() - timedelta(days=dias),
               fecha_vencimiento=date.today(), se_recuperó=True)
    for k, v in kwargs.items():
        setattr(p, k, v)
    db.add(p)
    return p


def test_no_duplicados_limites_y_canales(client, db, headers):
    c, e = crear(db)
    contacto(db, c, e, 7)
    contacto(db, c, e, 1, 'WhatsApp', provider_status='delivered')
    contacto(db, c, e, 0, 'SMS')  # no permite inferir orden el mismo día
    contacto(db, c, None, 2, 'Email')
    contacto(db, c, e, 1, 'SMS', modo='simulado')
    contacto(db, c, e, 1, 'SMS', estado='Fallido', provider_status='failed')
    pago(db, c, 0)
    pago(db, c, 6, 50)
    pago(db, c, 8, 20)  # anterior al contacto
    pago(db, c, 0, 999, se_recuperó=False)
    db.commit()
    r = client.get('/api/analitica/resumen', headers=headers).json()
    assert r['cartera_vencida'] == 600
    assert r['clientes_alto_riesgo'] == 1
    assert r['monto_recuperado_total'] == 170
    assert r['monto_recuperado_post_ia'] == 150
    assert r['clientes_con_pago_post_ia'] == 1
    assert r['tasa_pago_post_ia'] == 100
    canales = client.get('/api/analitica/canales', headers=headers).json()
    assert sum(c['monto_recuperado_post_ia'] for c in canales) == 150
    assert sum(c['pagos_posteriores_asociados'] for c in canales) == 2
    assert canales[2]['entregadas'] == 1
    assert canales[1]['simuladas'] == 1 and canales[1]['fallidas'] == 1
    assert [c['canal'] for c in canales] == ['Email', 'SMS', 'WhatsApp']


@pytest.mark.parametrize('dias', [30, 90, 180, 365])
def test_limite_periodo(client, db, headers, dias):
    c, e = crear(db)
    pago(db, c, dias - 1, 10)
    pago(db, c, dias, 20)
    pago(db, c, -1, 30)
    db.commit()
    r = client.get(f'/api/analitica/resumen?dias={dias}', headers=headers).json()
    assert r['periodo_dias'] == dias and r['monto_recuperado_total'] == 10


@pytest.mark.parametrize('modo,estado,estrategia', [('simulado','Simulado', True), ('real','Fallido', True), ('real','Enviado', False)])
def test_sin_asociacion(client, db, headers, modo, estado, estrategia):
    c, e = crear(db)
    contacto(db, c, e if estrategia else None, 1, modo=modo, estado=estado)
    pago(db, c, 0)
    db.commit()
    assert client.get('/api/analitica/resumen', headers=headers).json()['monto_recuperado_post_ia'] == 0


def test_ventana_configurable_y_mismo_dia(client, db, headers, monkeypatch):
    c, e = crear(db)
    contacto(db, c, e, 7)
    pago(db, c, 0)
    db.commit()
    assert client.get('/api/analitica/resumen', headers=headers).json()['monto_recuperado_post_ia'] == 100
    monkeypatch.setenv('ANALITICA_VENTANA_IA_DIAS', '6')
    assert client.get('/api/analitica/resumen', headers=headers).json()['monto_recuperado_post_ia'] == 0
    contacto(db, c, e, 0); db.commit()
    assert client.get('/api/analitica/resumen', headers=headers).json()['monto_recuperado_post_ia'] == 0


def test_vacia_snapshots_actualizables(client, db, headers):
    r = client.get('/api/analitica/resumen', headers=headers).json()
    assert r['saldo_pendiente'] == r['monto_recuperado_total'] == r['porcentaje_recuperacion'] == 0
    assert r['inicio_historico'] is None
    assert db.query(m.MetricaSnapshot).count() == 0
    for _ in range(2):
        filas = client.get('/api/analitica/evolucion', headers=headers).json()
        assert len(filas) == 1 and filas[0]['fecha'] == date.today().isoformat()
    c, _ = crear(db); pago(db, c, 0); db.commit()
    filas = client.get('/api/analitica/evolucion', headers=headers).json()
    assert len(filas) == 1 and filas[0]['saldo_pendiente'] == 600 and filas[0]['monto_recuperado'] == 100
    assert db.query(m.MetricaSnapshot).count() == 1
    anterior = m.MetricaSnapshot(fecha=date.today()-timedelta(days=40), saldo_pendiente=900,
        cartera_vencida=800, deudores_activos=1, clientes_alto_riesgo=1, monto_recuperado=0, clientes_con_estrategia_ia=0)
    db.add(anterior); db.commit()
    assert len(client.get('/api/analitica/evolucion?dias=30', headers=headers).json()) == 1
    assert len(client.get('/api/analitica/evolucion?dias=90', headers=headers).json()) == 2
    db.refresh(anterior)
    assert anterior.saldo_pendiente == 900


def test_relacion_validada_y_historico(client, db, headers):
    c, e = crear(db)
    otro = m.Cliente(nombre='Otro'); db.add(otro); db.flush()
    ajena = m.HistorialMensaje(cliente_id=otro.id, mensaje_generado='Otra'); db.add(ajena); db.commit()
    datos = dict(cliente_id=c.id, canal='Email', mensaje='Estrategia')
    for estrategia in (ajena.id, 99999):
        assert client.post('/api/comunicaciones', headers=headers, json={**datos, 'estrategia_id': estrategia}).status_code == 422
    r = client.post('/api/comunicaciones', headers=headers, json={**datos, 'estrategia_id': e.id})
    assert r.status_code == 201 and r.json()['estrategia_id'] == e.id
    assert client.post('/api/comunicaciones', headers=headers, json=datos).json()['estrategia_id'] is None


def test_migracion_preserva_historicos():
    engine = create_engine('sqlite://')
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE comunicaciones (id INTEGER PRIMARY KEY, mensaje VARCHAR)'))
        conn.execute(text("INSERT INTO comunicaciones VALUES (1, 'Historico')"))
    migrar(engine); migrar(engine)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT mensaje, estrategia_id FROM comunicaciones')).one() == ('Historico', None)
    assert any(f['referred_table'] == 'historial_mensajes' for f in inspect(engine).get_foreign_keys('comunicaciones'))
    assert 'metricas_snapshots' in inspect(engine).get_table_names()


def test_contacto_anterior_al_periodo_y_cohorte(client, db, headers):
    c, e = crear(db)
    contacto(db, c, e, 30)
    pago(db, c, 29, 25)
    db.commit()
    r = client.get('/api/analitica/resumen?dias=30', headers=headers).json()
    assert r['monto_recuperado_post_ia'] == 25
    assert r['clientes_contactados_ia'] == 0
    assert r['clientes_con_pago_post_ia'] == 1
    assert r['tasa_pago_post_ia'] == 0
    assert sum(canal['pagos_posteriores_asociados'] for canal in client.get('/api/analitica/canales', headers=headers).json()) == 1


def test_no_asocia_otro_cliente_ni_llamada(client, db, headers):
    c, e = crear(db)
    otro = m.Cliente(nombre='Sin contacto'); db.add(otro); db.flush()
    contacto(db, c, e, 1)
    pago(db, otro, 0)
    contacto(db, c, e, 1, 'Llamada')
    # Solo la llamada es anterior a este pago: Email queda fuera de la ventana.
    pago(db, c, 0, 50)
    db.commit()
    db.query(m.Comunicacion).filter_by(canal='Email').update({'fecha_envio': date.today() - timedelta(days=8)})
    db.commit()
    assert client.get('/api/analitica/resumen', headers=headers).json()['monto_recuperado_post_ia'] == 0


@pytest.mark.parametrize('ruta', ['resumen', 'evolucion', 'canales'])
def test_scope_entra_requerido(client, entra_token, ruta):
    token = entra_token({'scp': 'otro_scope'})
    assert client.get(f'/api/analitica/{ruta}', headers={'Authorization': 'Bearer ' + token}).status_code == 403
