import os
import re
from urllib.parse import urlsplit
from email_validator import validate_email, EmailNotValidError


def valor(nombre):
    return os.getenv(nombre, '').strip()


def url_callback_twilio():
    url = valor('TWILIO_STATUS_CALLBACK_URL')
    if not url:
        return ''
    parsed = urlsplit(url)
    if (parsed.scheme not in ('https', 'http') or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or not parsed.path.endswith('/api/webhooks/twilio/status')
            or (parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1'))):
        raise ValueError('URL de callback no válida')
    return url


def telefono_valido(numero):
    return bool(re.fullmatch(r'\+[1-9]\d{7,14}', numero or ''))


def email_valido(email):
    try:
        validate_email(email or '', check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def estado_proveedores():
    if valor('COMMUNICATIONS_REAL_ENABLED').lower() != 'true':
        return dict.fromkeys(('twilio_sms', 'twilio_whatsapp', 'twilio_voice', 'sendgrid'), False)
    twilio = bool(valor('TWILIO_ACCOUNT_SID') and valor('TWILIO_AUTH_TOKEN'))
    return {
        'twilio_sms': twilio and telefono_valido(valor('TWILIO_PHONE_NUMBER')),
        'twilio_whatsapp': twilio and telefono_valido(valor('TWILIO_WHATSAPP_NUMBER').removeprefix('whatsapp:')),
        'twilio_voice': False,
        'sendgrid': bool(valor('SENDGRID_API_KEY')) and email_valido(valor('SENDGRID_FROM_EMAIL')),
    }
