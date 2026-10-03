"""Callbacks firmados: actualizar intención existente, nunca crear comunicaciones."""
import re
from sqlalchemy import select
from ..models import Comunicacion

ESTADOS = {'accepted': 'Aceptado', 'queued': 'En cola', 'sending': 'Enviando', 'sent': 'Enviado',
           'delivered': 'Entregado', 'read': 'Leído', 'failed': 'Fallido',
           'undelivered': 'No entregado'}
PROGRESO = {'accepted': -1, 'queued': 0, 'sending': 1, 'sent': 2, 'delivered': 3, 'read': 4}
FALLOS = {'failed', 'undelivered'}


def actualizar(db, sid, estado, error=None, comunicacion_id=None):
    registros = db.scalars(select(Comunicacion).where(
        Comunicacion.external_id == sid, Comunicacion.provider == 'twilio',
        Comunicacion.modo == 'real', Comunicacion.canal.in_(('SMS', 'WhatsApp'))
    ).with_for_update().execution_options(populate_existing=True).limit(2)).all()
    if len(registros) > 1:
        return  # SID ambiguo heredado: nunca actualizar dos registros.
    registro = registros[0] if registros else None
    if registro is None and comunicacion_id is not None:
        registro = db.scalar(select(Comunicacion).where(
            Comunicacion.id == comunicacion_id, Comunicacion.external_id.is_(None),
            Comunicacion.provider == 'twilio', Comunicacion.modo == 'real',
            Comunicacion.estado == 'Pendiente', Comunicacion.canal.in_(('SMS', 'WhatsApp'))
        ).with_for_update().execution_options(populate_existing=True))
    if registro is None or estado not in ESTADOS or (estado == 'read' and registro.canal != 'WhatsApp'):
        return
    anterior = registro.provider_status
    if anterior in FALLOS or (anterior is None and registro.estado == 'Fallido'):
        return
    if anterior == estado:
        return
    if anterior in PROGRESO:
        if estado in PROGRESO and PROGRESO[estado] < PROGRESO[anterior]:
            return
        if estado in FALLOS and PROGRESO[anterior] >= PROGRESO['delivered']:
            return
    registro.external_id = sid
    registro.provider_status = estado
    registro.estado = ESTADOS[estado]
    registro.exitoso = estado not in FALLOS
    registro.error_tecnico = (
        'TwilioError:' + error if isinstance(error, str) and re.fullmatch(r'[0-9]{3,6}', error)
        else 'TwilioDeliveryFailed'
    ) if estado in FALLOS else None
    db.commit()
