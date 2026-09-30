import time
from unittest.mock import Mock
import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from app import auth, main


def test_me(client, headers):
    assert client.get('/auth/me', headers=headers).json() == {
        'id': '33333333-3333-4333-8333-333333333333',
        'nombre': 'Usuario Microsoft', 'email': 'prueba@example.com'}


@pytest.mark.parametrize('claims,code', [
    ({'exp': 1}, 401), ({'nbf': int(time.time()) + 3600}, 401),
    ({'iss': 'https://otro.invalid'}, 401), ({'aud': 'graph'}, 401),
    ({'tid': 'otro-tenant'}, 401), ({'ver': '1.0'}, 401),
    ({'scp': 'User.Read'}, 403), ({'scp': None}, 403),
    ({'scp': 'not_access_as_user'}, 403), ({'scp': 'otra access_as_user'}, 200),
])
def test_claims(client, entra_token, claims, code):
    assert client.get('/auth/me', headers={'Authorization': 'Bearer ' + entra_token(claims)}).status_code == code


def test_firma_invalida(client, entra_token):
    otra = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert client.get('/auth/me', headers={'Authorization': 'Bearer ' + entra_token(key=otra)}).status_code == 401


@pytest.mark.parametrize('header', [None, 'Bearer no-es-jwt', 'Basic invalido'])
def test_sin_token_o_malformado(client, header):
    assert client.get('/auth/me', headers={'Authorization': header} if header else {}).status_code == 401


def test_sin_email(client, entra_token):
    res = client.get('/auth/me', headers={'Authorization': 'Bearer ' + entra_token({'preferred_username': None})})
    assert res.status_code == 200 and res.json()['email'] is None


def test_configuracion_ausente(client, headers, monkeypatch):
    monkeypatch.delenv('ENTRA_TENANT_ID')
    assert client.get('/auth/me', headers=headers).status_code == 503


def test_login_eliminado(client):
    assert client.post('/auth/login').status_code == 404


def test_todos_endpoints_protegidos(client):
    for route in main.app.routes:
        if route.path.startswith(('/api/', '/ia/', '/auth/')):
            path = route.path.replace('{cliente_id}', '1').replace('{deuda_id}', '1')
            for method in route.methods:
                assert client.request(method, path).status_code == 401, (method, path)


def test_cache_y_rotacion(client, headers, entra_token, entra_config, monkeypatch):
    original = auth.descargar_json
    descargar = Mock(side_effect=original)
    monkeypatch.setattr(auth, 'descargar_json', descargar)
    assert client.get('/auth/me', headers=headers).status_code == 200
    assert client.get('/auth/me', headers=headers).status_code == 200
    assert descargar.call_count == 2
    # Limita refrescos para kid desconocido.
    nuevo = {'Authorization': 'Bearer ' + entra_token(kid='rotada')}
    assert client.get('/auth/me', headers=nuevo).status_code == 401
    assert descargar.call_count == 2
    auth.claves.last_attempt -= 61
    tenant, _, issuer, key = entra_config
    rotada = dict(key, kid='rotada')
    descargar.side_effect = lambda url: {'issuer': issuer, 'jwks_uri': f'https://login.microsoftonline.com/{tenant}/keys'} if 'openid-configuration' in url else {'keys': [rotada]}
    assert client.get('/auth/me', headers=nuevo).status_code == 200
    assert descargar.call_count == 4


def test_error_discovery_seguro(client, headers, monkeypatch):
    monkeypatch.setattr(auth, 'descargar_json', Mock(side_effect=httpx.ConnectError('detalle privado')))
    response = client.get('/auth/me', headers=headers)
    assert response.status_code == 503
    assert 'detalle privado' not in response.text


def test_no_acepta_jwks_fuera_de_microsoft(client, headers, entra_config, monkeypatch):
    descargar = Mock(return_value={'issuer': entra_config[2], 'jwks_uri': 'https://otro.invalid/keys'})
    monkeypatch.setattr(auth, 'descargar_json', descargar)
    assert client.get('/auth/me', headers=headers).status_code == 503
    descargar.assert_called_once()


def test_validacion_mock_para_operacion(client):
    validar = Mock(return_value={'id': 'mock', 'nombre': 'Mock', 'email': None})
    # El resto de la suite usa firmas RSA reales locales y discovery/JWKS mockeados.
    main.app.dependency_overrides[auth.get_entra_user] = lambda: validar()
    assert client.get('/api/metricas').status_code == 200
    validar.assert_called_once()


def test_jwt_local_rechazado(client):
    import jwt
    token = jwt.encode({'sub': 'legacy', 'exp': int(time.time()) + 600}, 'solo-prueba-no-real-de-al-menos-32-bytes', algorithm='HS256')
    assert client.get('/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_cache_caducada_falla_cerrado(client, headers, monkeypatch):
    assert client.get('/auth/me', headers=headers).status_code == 200
    auth.claves.expires = 0
    auth.claves.last_attempt -= 61
    monkeypatch.setattr(auth, 'descargar_json', Mock(side_effect=httpx.ConnectError('sin red')))
    assert client.get('/auth/me', headers=headers).status_code == 503


def test_issuer_de_clave_incorrecto(client, headers, entra_config, monkeypatch):
    key = dict(entra_config[3], issuer='https://login.microsoftonline.com/otro/v2.0')
    original = auth.descargar_json
    monkeypatch.setattr(auth, 'descargar_json', lambda url: original(url) if 'openid-configuration' in url else {'keys': [key]})
    assert client.get('/auth/me', headers=headers).status_code == 401
