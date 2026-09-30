import os
import re
from email_validator import validate_email, EmailNotValidError


def valor(nombre):
    return os.getenv(nombre, '').strip()


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
