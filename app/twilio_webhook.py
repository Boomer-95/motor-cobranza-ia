"""Endpoint sin Entra; autenticación exclusivamente mediante firma Twilio."""
import re
from urllib.parse import parse_qsl
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from starlette.datastructures import FormData
from starlette.concurrency import run_in_threadpool
from twilio.request_validator import RequestValidator
from .database import get_db
from .services.configuracion import valor, url_callback_twilio
from .services.twilio_callbacks import actualizar

router = APIRouter()


@router.post('/api/webhooks/twilio/status', status_code=204)
async def status_twilio(request: Request, db: Session = Depends(get_db)):
    token = valor('TWILIO_AUTH_TOKEN')
    try:
        url = url_callback_twilio()
    except ValueError:
        url = ''
    if not token or not url:
        raise HTTPException(503, 'Callback no configurado.')
    signature = request.headers.get('X-Twilio-Signature', '')
    if not signature:
        raise HTTPException(403, 'Firma no válida.')
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/x-www-form-urlencoded':
        raise HTTPException(415, 'Se requiere formulario URL encoded.')
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 16384:
            raise HTTPException(413, 'Callback demasiado grande.')
        body.extend(chunk)
    try:
        form = FormData(parse_qsl(body.decode('utf-8'), keep_blank_values=True, max_num_fields=100))
        query = request.scope.get('query_string', b'').decode('ascii')
        # URL pública fija: no confiar en Host/X-Forwarded-* del remitente.
        signed_url = url + ('?' + query if query else '')
        valid = RequestValidator(token).validate(signed_url, form, signature)
    except (ValueError, UnicodeError):
        valid = False
    if not valid:
        raise HTTPException(403, 'Firma no válida.')
    for name in ('MessageSid', 'MessageStatus', 'ErrorCode', 'AccountSid'):
        if len(form.getlist(name)) > 1:
            raise HTTPException(400, 'Campo ambiguo.')
    account = valor('TWILIO_ACCOUNT_SID')
    if account and form.get('AccountSid') != account:
        raise HTTPException(403, 'Cuenta no válida.')
    sid = form.get('MessageSid', '')
    if not re.fullmatch(r'(?:SM|MM)[0-9a-fA-F]{32}', sid):
        raise HTTPException(400, 'SID ausente o no válido.')
    estado = form.get('MessageStatus', '')
    if not estado:
        raise HTTPException(400, 'Estado ausente.')
    ids = request.query_params.getlist('comunicacion_id')
    if len(ids) > 1 or (ids and not re.fullmatch(r'[1-9][0-9]{0,9}', ids[0])):
        raise HTTPException(400, 'Correlación no válida.')
    await run_in_threadpool(actualizar, db, sid, estado, form.get('ErrorCode'),
                            int(ids[0]) if ids else None)
    return Response(status_code=204)
