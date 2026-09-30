"""Sin reintentos automáticos: un timeout puede ocultar un envío aceptado."""
import logging
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from .configuracion import estado_proveedores, valor
from .mensajes import validar_sms

# El SDK registra URLs con el SID a nivel INFO; impedir esos logs sensibles.
logging.getLogger('twilio.http_client').disabled = True


def enviar_mensaje(destinatario, mensaje, whatsapp=False):
    if not whatsapp:
        validar_sms(mensaje)
    clave = 'twilio_whatsapp' if whatsapp else 'twilio_sms'
    if not estado_proveedores()[clave]:
        raise ValueError('Proveedor no configurado')
    origen = valor('TWILIO_WHATSAPP_NUMBER' if whatsapp else 'TWILIO_PHONE_NUMBER')
    if whatsapp:
        origen = 'whatsapp:' + origen.removeprefix('whatsapp:')
        destinatario = 'whatsapp:' + destinatario
    client = Client(valor('TWILIO_ACCOUNT_SID'), valor('TWILIO_AUTH_TOKEN'),
                    http_client=TwilioHttpClient(timeout=15, max_retries=0))
    respuesta = client.messages.create(to=destinatario, from_=origen, body=mensaje)
    if respuesta.status in ('failed', 'undelivered', 'canceled') or not respuesta.sid:
        raise RuntimeError('Envío rechazado')
    return respuesta.sid


def enviar_llamada(destinatario, mensaje):
    """Reservado para Voice: requiere diseño y habilitación explícitos."""
    raise NotImplementedError('Voice permanece simulado')
