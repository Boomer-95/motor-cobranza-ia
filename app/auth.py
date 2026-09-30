"""Autenticación exclusiva Entra ID: tokens de acceso delegados v2, RS256."""
import os
from threading import Lock
from time import monotonic
from urllib.parse import urlparse
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer(auto_error=False)


def configuracion():
    try:
        tenant = str(UUID(os.environ['ENTRA_TENANT_ID'].strip()))
        client = str(UUID(os.environ['ENTRA_CLIENT_ID'].strip()))
        scope = os.getenv('ENTRA_REQUIRED_SCOPE', 'access_as_user').strip()
        if not scope or len(scope.split()) != 1:
            raise ValueError()
    except (KeyError, ValueError):
        raise HTTPException(503, 'Microsoft Entra ID no está configurado.') from None
    return tenant, client, scope


def descargar_json(url):
    # Solo documentos públicos; nunca enviar el Bearer a discovery/JWKS.
    response = httpx.get(url, timeout=10, follow_redirects=False)
    response.raise_for_status()
    return response.json()


class ClavesEntra:
    """Caché por proceso: 1 hora; kid desconocido refresca como máximo cada 60 s."""
    def __init__(self):
        self.lock = Lock()
        self.tenant = None
        self.keys = []
        self.expires = 0
        self.last_attempt = float('-inf')

    def obtener(self, tenant, kid):
        issuer = f'https://login.microsoftonline.com/{tenant}/v2.0'
        with self.lock:
            now = monotonic()
            if self.tenant != tenant:
                self.tenant, self.keys, self.expires, self.last_attempt = tenant, [], 0, float('-inf')
            match = next((key for key in self.keys if key.get('kid') == kid), None)
            if now >= self.expires or match is None:
                if now - self.last_attempt >= 60:
                    self.last_attempt = now
                    try:
                        discovery = descargar_json(issuer + '/.well-known/openid-configuration')
                        uri = discovery['jwks_uri']
                        parsed = urlparse(uri)
                        if (discovery.get('issuer') != issuer or parsed.scheme != 'https'
                                or parsed.netloc != 'login.microsoftonline.com' or parsed.fragment):
                            raise ValueError()
                        keys = descargar_json(uri)['keys']
                        if not isinstance(keys, list) or not keys or not all(isinstance(k, dict) for k in keys):
                            raise ValueError()
                        self.keys, self.expires = keys, now + 3600
                    except (httpx.HTTPError, ValueError, KeyError, TypeError):
                        raise HTTPException(503, 'No se pudo validar la sesión con Microsoft.') from None
                if now >= self.expires:
                    raise HTTPException(503, 'No se pudo validar la sesión con Microsoft.')
                match = next((key for key in self.keys if key.get('kid') == kid), None)
            if match is None:
                raise jwt.InvalidTokenError()
            if (match.get('kty') != 'RSA' or match.get('use', 'sig') != 'sig'
                    or match.get('alg', 'RS256') != 'RS256'
                    or match.get('issuer', issuer).replace('{tenantid}', tenant) != issuer):
                raise jwt.InvalidTokenError()
            return jwt.PyJWK.from_dict(match, algorithm='RS256').key


claves = ClavesEntra()


def get_entra_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    invalid = HTTPException(401, 'Sesión no válida. Inicia sesión con Microsoft.',
                            headers={'WWW-Authenticate': 'Bearer'})
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise invalid
    tenant, audience, scope = configuracion()
    issuer = f'https://login.microsoftonline.com/{tenant}/v2.0'
    try:
        header = jwt.get_unverified_header(credentials.credentials)
        if header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str) or not header['kid']:
            raise jwt.InvalidTokenError()
        key = claves.obtener(tenant, header['kid'])
        claims = jwt.decode(credentials.credentials, key, algorithms=['RS256'],
                            audience=audience, issuer=issuer,
                            options={'require': ['exp', 'iss', 'aud', 'tid', 'oid', 'ver'], 'strict_aud': True})
        if claims['tid'] != tenant or claims['ver'] != '2.0' or not isinstance(claims['oid'], str) or not claims['oid']:
            raise jwt.InvalidTokenError()
    except (jwt.PyJWTError, ValueError, TypeError):
        raise invalid from None
    scopes = claims.get('scp')
    if not isinstance(scopes, str) or scope not in scopes.split():
        raise HTTPException(403, 'No tienes permiso para acceder a esta API.')
    return {'id': claims['oid'], 'nombre': claims.get('name') if isinstance(claims.get('name'), str) else None,
            'email': next((claims[k] for k in ('preferred_username', 'email')
                           if isinstance(claims.get(k), str) and claims[k]), None)}
