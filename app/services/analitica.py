"""Analítica observacional: asociación temporal, nunca evidencia causal."""
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session
from .. import auth, models as m
from ..database import get_db

router = APIRouter(prefix='/api/analitica', dependencies=[Depends(auth.get_entra_user)])
CANALES = ('Email', 'SMS', 'WhatsApp')


def periodo(dias: int = Query(30, json_schema_extra={'enum': [30, 90, 180, 365]})):
    if dias not in (30, 90, 180, 365):
        raise HTTPException(422, 'El periodo debe ser 30, 90, 180 o 365 días.')
    return dias


def ventana_dias():
    return max(1, min(365, int(os.getenv('ANALITICA_VENTANA_IA_DIAS', '7'))))


def cartera_actual(db):
    """Comparte la definición de cartera vencida con /api/metricas."""
    saldo = db.query(func.sum(m.Deuda.saldo_pendiente)).scalar() or 0
    vencida = db.query(func.sum(m.Deuda.saldo_pendiente)).filter(
        m.Deuda.saldo_pendiente > 0,
        or_(m.Deuda.estatus == 'En Mora', m.Deuda.fecha_vencimiento < date.today())).scalar() or 0
    activos = m.Cliente.deudas.any(m.Deuda.saldo_pendiente > 0)
    return dict(saldo_pendiente=saldo, cartera_vencida=vencida,
                deudores_activos=db.query(m.Cliente).filter(activos).count(),
                clientes_alto_riesgo=db.query(m.Cliente).filter(activos, m.Cliente.score_riesgo >= .66).count())


def pagos_validos(db):
    return db.query(m.Pago).filter(m.Pago.fecha_pago.isnot(None), m.Pago.se_recuperó.is_(True), m.Pago.monto > 0)


def importe(pagos):
    return float(sum((Decimal(str(p.monto)) for p in pagos), Decimal(0)).quantize(Decimal('.01')))


def datos_periodo(db, dias):
    hoy = date.today()
    inicio = hoy - timedelta(days=dias - 1)
    ventana = ventana_dias()
    pagos = pagos_validos(db).filter(m.Pago.fecha_pago.between(inicio, hoy)).all()
    contactos = db.query(m.Comunicacion).filter(
        m.Comunicacion.fecha_envio.between(inicio - timedelta(days=ventana), hoy),
        m.Comunicacion.canal.in_(CANALES)).all()
    # Simulaciones, fallos e intenciones pendientes no equivalen a contacto.
    validos = [c for c in contactos if c.modo != 'simulado' and c.exitoso
               and c.estado != 'Fallido' and c.provider_status not in ('failed', 'undelivered', 'bounced', 'dropped')]
    por_cliente = {}
    for c in validos:
        if c.estrategia_id is not None:
            por_cliente.setdefault(c.cliente_id, []).append(c)
    asociados = []
    for pago in pagos:
        candidatos = [c for c in por_cliente.get(pago.cliente_id, [])
                      if 0 < (pago.fecha_pago - c.fecha_envio).days <= ventana]
        if candidatos:
            asociados.append((pago, max(candidatos, key=lambda c: (c.fecha_envio, c.id))))
    return inicio, hoy, pagos, [c for c in contactos if c.fecha_envio >= inicio], validos, asociados


def actualizar_snapshot(db):
    # El bloqueo protege tanto la lectura como el upsert frente a consultas concurrentes.
    if db.get_bind().dialect.name == 'postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(71924002)'))
    valores = cartera_actual(db)
    valores['monto_recuperado'] = importe(pagos_validos(db).filter(m.Pago.fecha_pago <= date.today()).all())
    valores['clientes_con_estrategia_ia'] = db.query(func.count(func.distinct(m.HistorialMensaje.cliente_id))).scalar() or 0
    dialecto = db.get_bind().dialect.name
    if dialecto == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    sentencia = insert(m.MetricaSnapshot).values(fecha=date.today(), **valores)
    db.execute(sentencia.on_conflict_do_update(index_elements=['fecha'], set_=valores))
    db.commit()


@router.get('/resumen')
def resumen(dias: int = Depends(periodo), db: Session = Depends(get_db)):
    inicio, hoy, pagos, contactos, validos, asociados = datos_periodo(db, dias)
    actual = cartera_actual(db)
    recuperado = importe(pagos)
    contactados = {c.cliente_id for c in validos if c.estrategia_id is not None and inicio <= c.fecha_envio <= hoy}
    # Cohorte: solo pagos atribuidos a contactos del periodo para la tasa.
    con_pago = {p.cliente_id for p, c in asociados if c.fecha_envio >= inicio}
    estrategias = db.query(func.count(func.distinct(m.HistorialMensaje.cliente_id))).filter(
        m.HistorialMensaje.fecha_creacion >= datetime.combine(inicio, datetime.min.time()),
        m.HistorialMensaje.fecha_creacion < datetime.combine(hoy + timedelta(days=1), datetime.min.time())).scalar() or 0
    return dict(periodo_dias=dias, **actual, monto_recuperado_total=recuperado,
                porcentaje_recuperacion=round(100 * recuperado / (recuperado + actual['saldo_pendiente']), 2)
                if recuperado + actual['saldo_pendiente'] else 0,
                clientes_con_estrategia_ia=estrategias, clientes_contactados_ia=len(contactados),
                clientes_con_pago_post_ia=len({p.cliente_id for p, _ in asociados}),
                monto_recuperado_post_ia=importe([p for p, _ in asociados]),
                tasa_pago_post_ia=round(100 * len(con_pago) / len(contactados), 2) if contactados else 0,
                ventana_ia_dias=ventana_dias(), ultima_actualizacion=datetime.now(timezone.utc),
                inicio_historico=db.query(func.min(m.MetricaSnapshot.fecha)).scalar(),
                comunicaciones_simuladas=sum(c.modo == 'simulado' for c in contactos))


@router.get('/evolucion')
def evolucion(dias: int = Depends(periodo), db: Session = Depends(get_db)):
    actualizar_snapshot(db)
    filas = db.query(m.MetricaSnapshot).filter(m.MetricaSnapshot.fecha.between(
        date.today() - timedelta(days=dias - 1), date.today())).order_by(m.MetricaSnapshot.fecha).all()
    return [{campo: getattr(s, campo) for campo in ('fecha', 'saldo_pendiente', 'cartera_vencida', 'monto_recuperado')} for s in filas]


@router.get('/canales')
def canales(dias: int = Depends(periodo), db: Session = Depends(get_db)):
    inicio, _, _, contactos, validos, asociados = datos_periodo(db, dias)
    resultado = []
    for canal in CANALES:
        registros = [c for c in contactos if c.canal == canal]
        enviados = [c for c in validos if c.canal == canal and c.fecha_envio >= inicio]
        pagos = [p for p, c in asociados if c.canal == canal]
        resultado.append(dict(canal=canal, comunicaciones_enviadas=len(enviados),
            entregadas=sum(c.modo != 'simulado' and c.provider_status in ('delivered', 'read') for c in registros),
            fallidas=sum(c.modo != 'simulado' and (c.estado == 'Fallido' or c.provider_status in ('failed', 'undelivered', 'bounced', 'dropped')) for c in registros),
            simuladas=sum(c.modo == 'simulado' for c in registros),
            clientes_unicos_contactados=len({c.cliente_id for c in enviados}),
            pagos_posteriores_asociados=len(pagos), monto_recuperado_post_ia=importe(pagos)))
    return resultado
