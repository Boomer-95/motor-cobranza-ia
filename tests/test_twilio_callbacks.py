from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlencode

import pytest
from starlette.datastructures import FormData
from twilio.request_validator import RequestValidator

from app import main, models
from app.services import twilio_service, comunicaciones

PATH = '/api/webhooks/twilio/status'
URL = 'https://callbacks.example.invalid/backend' + PATH
TOKEN = 'token-ficticio-callback'
ACCOUNT = 'AC' + '1' * 32
SID = 'SM' + '2' * 32


@pytest.fixture
def configuracion_callback(monkeypatch):
    monkeypatch.setenv('TWILIO_AUTH_TOKEN', TOKEN)
    monkeypatch.setenv('TWILIO_ACCOUNT_SID', ACCOUNT)
    monkeypatch.setenv('TWILIO_STATUS_CALLBACK_URL', URL)
    # Ni siquiera se debe instanciar un cliente externo al recibir callbacks.
    constructor = Mock(side_effect=AssertionError('Callback no puede contactar Twilio'))
    monkeypatch.setattr(twilio_service, 'Client', constructor)
    return constructor


@pytest.fixture
def registro(db):
    cliente = models.Cliente(nombre='Fixture')
    db.add(cliente)
    db.flush()
    fila = models.Comunicacion(cliente_id=cliente.id, canal='SMS', mensaje='Mensaje fixture',
        modo='real', provider='twilio', estado='Enviado', external_id=SID, exitoso=True)
    db.add(fila)
    db.commit()
    return fila


def callback(client, estado='delivered', sid=SID, extras=None, query='', signature=None,
             url=URL, pairs=None, headers=None):
    datos = {'AccountSid': ACCOUNT, 'MessageSid': sid, 'MessageStatus': estado}
    datos.update(extras or {})
    form = FormData(pairs if pairs is not None else datos.items())
    firma = RequestValidator(TOKEN).compute_signature(url + query, form)
    return client.post(PATH + query, content=urlencode(list(form.multi_items())), headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Twilio-Signature': signature if signature is not None else firma,
        **(headers or {}),
    })


@pytest.mark.parametrize('estado,esperado', [
    ('queued', 'En cola'), ('sending', 'Enviando'), ('sent', 'Enviado'),
    ('delivered', 'Entregado'), ('read', 'Leído'), ('failed', 'Fallido'),
    ('undelivered', 'No entregado'),
])
def test_callback_valido_actualiza_sin_duplicar(client, db, headers, registro,
                                              configuracion_callback, estado, esperado):
    registro.canal = 'WhatsApp' if estado == 'read' else 'SMS'
    db.commit()
    original = (registro.id, registro.cliente_id, registro.canal, registro.mensaje, registro.external_id)
    for _ in range(2):
        res = callback(client, estado, extras={'ErrorCode': '63015',
            'ErrorMessage': 'SECRETO-SENTINELA', 'To': 'DESTINO-SENTINELA', 'Body': 'CUERPO-SENTINELA'})
        assert res.status_code == 204
        db.refresh(registro)
        assert registro.provider_status == estado and registro.estado == esperado
        assert registro.exitoso is (estado not in ('failed', 'undelivered'))
        assert registro.error_tecnico == ('TwilioError:63015' if not registro.exitoso else None)
        assert db.query(models.Comunicacion).count() == 1
        assert (registro.id, registro.cliente_id, registro.canal, registro.mensaje, registro.external_id) == original
    historial = client.get(f'/api/clientes/{registro.cliente_id}', headers=headers).json()['comunicaciones'][0]
    assert historial['provider_status'] == estado
    configuracion_callback.assert_not_called()


@pytest.mark.parametrize('signature', ['firma-invalida', ''])
def test_firma_invalida_rechazada(client, db, registro, configuracion_callback, signature, caplog):
    res = callback(client, signature=signature, extras={'Body': 'CUERPO-SENTINELA'})
    assert res.status_code == 403
    db.refresh(registro)
    assert registro.provider_status is None
    assert TOKEN not in res.text + caplog.text
    assert 'CUERPO-SENTINELA' not in res.text + caplog.text


def test_firma_incluye_todos_los_campos(client, registro, configuracion_callback):
    datos = {'AccountSid': ACCOUNT, 'MessageSid': SID, 'MessageStatus': 'delivered'}
    firma = RequestValidator(TOKEN).compute_signature(URL, datos)
    assert callback(client, signature=firma, extras={'NuevoCampo': 'fixture'}).status_code == 403


def test_url_publica_fija_no_confia_en_proxy(client, registro, configuracion_callback):
    assert callback(client, headers={'Host': 'evil.invalid',
        'X-Forwarded-Proto': 'http', 'X-Forwarded-Host': 'evil.invalid'}).status_code == 204
    assert callback(client, url='https://evil.invalid' + PATH).status_code == 403


def test_callback_sin_entra(client, registro, configuracion_callback, monkeypatch):
    # Las llamadas se realizan sin Authorization/Entra.
    monkeypatch.setattr(main.auth, 'get_entra_user', Mock(side_effect=AssertionError('No Entra')))
    assert callback(client).status_code == 204


@pytest.mark.parametrize('extras', [{'MessageSid': ''}, {'MessageStatus': ''},
                                   {'MessageSid': 'invalido'}])
def test_callback_campos_requeridos(client, registro, configuracion_callback, extras):
    assert callback(client, extras=extras).status_code == 400


def test_sid_desconocido_no_crea(client, db, registro, configuracion_callback):
    assert callback(client, sid='SM' + 'f' * 32).status_code == 204
    assert db.query(models.Comunicacion).count() == 1
    db.refresh(registro)
    assert registro.provider_status is None


def test_callback_sin_sid(client, db, registro, configuracion_callback):
    assert callback(client, pairs=[('AccountSid', ACCOUNT),
                                   ('MessageStatus', 'delivered')]).status_code == 400
    assert db.query(models.Comunicacion).count() == 1
    db.refresh(registro)
    assert registro.provider_status is None


def test_formato_no_admitido(client, registro, configuracion_callback):
    assert client.post(PATH, json={'MessageSid': SID}, headers={
        'X-Twilio-Signature': 'firma-ficticia'}).status_code == 415


@pytest.mark.parametrize('modo,provider,canal', [('simulado', 'twilio', 'SMS'),
    ('real', 'sendgrid', 'Email'), ('real', 'twilio', 'Llamada')])
def test_callback_no_modifica_otros_registros(client, db, registro, configuracion_callback,
                                           modo, provider, canal):
    registro.modo, registro.provider, registro.canal = modo, provider, canal
    db.commit()
    assert callback(client).status_code == 204
    db.refresh(registro)
    assert registro.provider_status is None


@pytest.mark.parametrize('estados,final', [
    (['delivered', 'sent', 'queued'], 'delivered'),
    (['failed', 'sent', 'delivered'], 'failed'),
    (['delivered', 'undelivered'], 'delivered'),
    (['read', 'delivered', 'sent'], 'read'),
    (['sent', 'failed'], 'failed'),
])
def test_fuera_de_orden_no_retrocede(client, db, registro, configuracion_callback, estados, final):
    registro.canal = 'WhatsApp'
    db.commit()
    for estado in estados:
        assert callback(client, estado).status_code == 204
    db.refresh(registro)
    assert registro.provider_status == final


def test_read_sms_y_estado_desconocido_ignorados(client, db, registro, configuracion_callback):
    for estado in ('read', 'nuevo_estado'):
        assert callback(client, estado).status_code == 204
    db.refresh(registro)
    assert registro.provider_status is None


@pytest.mark.parametrize('error', ['', 'ERROR-SENTINELA', '1234567'])
def test_error_solo_codigo_seguro(client, db, registro, configuracion_callback, error, caplog):
    assert callback(client, 'failed', extras={'ErrorCode': error}).status_code == 204
    db.refresh(registro)
    assert registro.error_tecnico == 'TwilioDeliveryFailed'
    assert 'ERROR-SENTINELA' not in caplog.text


def test_firma_query_y_callback_temprano(client, db, registro, configuracion_callback):
    registro.external_id = None
    registro.estado = 'Pendiente'
    db.commit()
    query = f'?comunicacion_id={registro.id}'
    # Una firma calculada sin query no autoriza la correlación temprana.
    firma = RequestValidator(TOKEN).compute_signature(URL, {
        'AccountSid': ACCOUNT, 'MessageSid': SID, 'MessageStatus': 'delivered'})
    assert callback(client, query=query, signature=firma).status_code == 403
    assert callback(client, query=query).status_code == 204
    db.refresh(registro)
    assert registro.external_id == SID and registro.provider_status == 'delivered'
    assert db.query(models.Comunicacion).count() == 1


def test_sid_ambiguo_no_actualiza(client, db, registro, configuracion_callback):
    db.add(models.Comunicacion(cliente_id=registro.cliente_id, mensaje='Otro', canal='SMS',
        modo='real', provider='twilio', external_id=SID, estado='Enviado'))
    db.commit()
    assert callback(client).status_code == 204
    assert all(r.provider_status is None for r in db.query(models.Comunicacion).all())


def test_cuenta_incorrecta_y_campos_duplicados(client, registro, configuracion_callback):
    assert callback(client, extras={'AccountSid': 'AC' + 'f' * 32}).status_code == 403
    pares = [('AccountSid', ACCOUNT), ('MessageSid', SID), ('MessageSid', 'SM' + 'f' * 32),
             ('MessageStatus', 'delivered')]
    assert callback(client, pairs=pares).status_code == 400


def test_configuracion_ausente_y_body_grande(client, registro, configuracion_callback, monkeypatch):
    assert callback(client, extras={'Body': 'x' * 17000}).status_code == 413
    monkeypatch.delenv('TWILIO_AUTH_TOKEN')
    assert callback(client).status_code == 503


@pytest.mark.parametrize('canal', ['SMS', 'WhatsApp'])
def test_envio_mock_incluye_callback_y_preserva_estado_temprano(client, db, registro,
        configuracion_callback, monkeypatch, canal):
    monkeypatch.setenv('COMMUNICATIONS_REAL_ENABLED', 'true')
    monkeypatch.setenv('TWILIO_PHONE_NUMBER', '+12025550101')
    monkeypatch.setenv('TWILIO_WHATSAPP_NUMBER', '+12025550102')
    cliente = db.get(models.Cliente, registro.cliente_id)
    cliente.telefono = '+12025550103'
    db.commit()
    constructor = Mock()

    def crear(**kwargs):
        query = kwargs['status_callback'][len(URL):]
        # Firma oficial calculada localmente; callback llega antes de retornar SDK.
        assert callback(client, query=query).status_code == 204
        return SimpleNamespace(sid=SID, status='queued')

    # Usar otro SID para no encontrar la fila fixture por accidente.
    registro.external_id = 'SM' + '3' * 32
    db.commit()
    constructor.return_value.messages.create.side_effect = crear
    monkeypatch.setattr(twilio_service, 'Client', constructor)
    fila = comunicaciones.registrar(db, cliente, canal, 'Mensaje fixture')
    assert fila.provider_status == 'delivered' and fila.estado == 'Entregado'
    assert constructor.return_value.messages.create.call_args.kwargs['status_callback'] == (
        URL + f'?comunicacion_id={fila.id}')
    assert db.query(models.Comunicacion).count() == 2
