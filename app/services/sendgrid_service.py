import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email
from .configuracion import estado_proveedores, valor


# El cliente HTTP puede registrar Authorization y el payload a nivel DEBUG.
logging.getLogger('python_http_client.client').disabled = True


def enviar_email(destinatario, asunto, mensaje):
    if not estado_proveedores()['sendgrid']:
        raise ValueError('Proveedor no configurado')
    correo = Mail(from_email=Email(valor('SENDGRID_FROM_EMAIL'), valor('SENDGRID_FROM_NAME') or 'PluriOne'),
                  to_emails=destinatario, subject=asunto, plain_text_content=mensaje)
    client = SendGridAPIClient(api_key=valor('SENDGRID_API_KEY'))
    respuesta = client.client.mail.send.post(request_body=correo.get(), timeout=15)
    if respuesta.status_code != 202:
        raise RuntimeError('Envío rechazado')
    return respuesta.headers.get('X-Message-Id')
