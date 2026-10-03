"""Sin reintentos automáticos: un timeout puede ocultar un envío aceptado."""
import logging
import re
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from twilio.base.exceptions import TwilioRestException
from .configuracion import estado_proveedores, valor, url_callback_twilio
from .mensajes import validar_sms

# El SDK registra URLs con el SID a nivel INFO; impedir esos logs sensibles.
logging.getLogger('twilio.http_client').disabled = True
logger = logging.getLogger(__name__)


def normalizar_destino_whatsapp(numero):
    """Alias mexicano de WhatsApp; no cambia el contacto ni destinos SMS.

    Solo transformar +52 seguido de los diez dígitos nacionales. Conservar
    el alias +521 ya existente y otros países, sin interpretar números locales.
    """
    if not isinstance(numero, str) or not re.fullmatch(r'\+[1-9][0-9]{7,14}', numero):
        raise ValueError('Destino WhatsApp no válido (E.164)')
    if not numero.startswith('+521') and re.fullmatch(r'\+52[0-9]{10}', numero):
        return '+521' + numero[3:]
    return numero


def enviar_mensaje(destinatario, mensaje, whatsapp=False, comunicacion_id=None):
    if not whatsapp:
        validar_sms(mensaje)
    clave = 'twilio_whatsapp' if whatsapp else 'twilio_sms'
    if not estado_proveedores()[clave]:
        raise ValueError('Proveedor no configurado')
    origen = valor('TWILIO_WHATSAPP_NUMBER' if whatsapp else 'TWILIO_PHONE_NUMBER')
    if whatsapp:
        origen = 'whatsapp:' + origen.removeprefix('whatsapp:')
        destinatario = 'whatsapp:' + normalizar_destino_whatsapp(destinatario)
    client = Client(valor('TWILIO_ACCOUNT_SID'), valor('TWILIO_AUTH_TOKEN'),
                    http_client=TwilioHttpClient(timeout=15, max_retries=0))
    callback = url_callback_twilio()
    opciones = {}
    if callback:
        # Correlación firmada para callbacks que llegan antes de persistir el SID.
        opciones['status_callback'] = callback + (
            f'?comunicacion_id={comunicacion_id}' if comunicacion_id is not None else '')
    try:
        respuesta = client.messages.create(to=destinatario, from_=origen, body=mensaje, **opciones)
    except TwilioRestException as exc:
        # Lista permitida estricta: nunca interpolar la excepción ni su contexto.
        http_status = exc.status if type(exc.status) is int else None
        code = exc.code if type(exc.code) is int else None
        logger.warning('TwilioRequestFailed channel=%s http_status=%s code=%s',
                       'WhatsApp' if whatsapp else 'SMS', http_status, code)
        raise RuntimeError('ProviderRequestFailed') from None
    if respuesta.status in ('failed', 'undelivered', 'canceled') or not respuesta.sid:
        raise RuntimeError('Envío rechazado')
    return respuesta.sid


def enviar_llamada(destinatario, mensaje):
    """Reservado para Voice: requiere diseño y habilitación explícitos."""
    raise NotImplementedError('Voice permanece simulado')
