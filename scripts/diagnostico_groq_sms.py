"""Una petición Groq aislada con datos ficticios y salida sin contenido.

No importa el paquete app, no abre la base ni usa proveedores de comunicaciones.
Valida el resultado con el archivo puro de normalización SMS.
El transporte rechaza otros destinos, rutas, redirects y una segunda petición.
"""
import asyncio
import argparse
import json
import logging
import os
import runpy
import tempfile
from pathlib import Path
import warnings

import httpx
from dotenv import dotenv_values
from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError


MODELOS_SEGUROS = frozenset({
    'qwen/qwen3.8-27b',
    'openai/gpt-oss-20b', 'openai/gpt-oss-120b',
    'llama-3.1-8b-instant', 'llama-3.3-70b-versatile',
})
MOTIVOS_SEGUROS = frozenset({'stop', 'length', 'tool_calls', 'function_call', 'content_filter'})


class SoloGroq(httpx.AsyncBaseTransport):
    def __init__(self):
        self.transporte = httpx.AsyncHTTPTransport(retries=0, trust_env=False)
        self.usado = False

    async def handle_async_request(self, request):
        if (self.usado or request.method != 'POST'
                or str(request.url) != 'https://api.groq.com/openai/v1/chat/completions'):
            raise RuntimeError('Destino o petición no permitidos')
        self.usado = True
        return await self.transporte.handle_async_request(request)

    async def aclose(self):
        await self.transporte.aclose()


def numero(valor):
    return valor if type(valor) is int and valor >= 0 else None


async def main(revision_ficticia=False):
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings('ignore')
    configuracion = dotenv_values(Path(__file__).resolve().parents[1] / '.env', interpolate=False)
    clave = os.environ.get('GROQ_API_KEY', configuracion.get('GROQ_API_KEY'))
    modelo = os.environ.get('GROQ_SMS_MODEL', configuracion.get('GROQ_SMS_MODEL') or 'qwen/qwen3.8-27b')
    if not clave or not clave.strip():
        print(json.dumps({'error': 'MissingGroqConfiguration'}))
        return 1

    # Mismos system prompt, envoltura, temperatura y presupuesto que la ruta SMS.
    # El único mensaje de origen es ficticio; no se acepta texto por argumentos.
    # Archivo puro compartido; no carga app/__init__, main ni comunicaciones.
    normalizador = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / 'app/services/mensajes.py'))
    instruccion = normalizador['SMS_INSTRUCCION']
    mensaje = (
        'Devuelve solo la linea SMS derivada de este texto:\n'
        '<mensaje_original>\nSu pago de MXN 500 vence el 10 de octubre.\n</mensaje_original>'
    )
    try:
        # Misma política de reasoning que la ruta SMS, sin importar la aplicación.
        opciones_razonamiento = ({'reasoning_effort': 'none'} if modelo == 'qwen/qwen3.8-27b'
                                else {'reasoning_effort': 'low'} if modelo in
                                {'openai/gpt-oss-20b', 'openai/gpt-oss-120b'} else {})
        async with AsyncOpenAI(
            api_key=clave, base_url='https://api.groq.com/openai/v1',
            timeout=20.0, max_retries=0,
            http_client=httpx.AsyncClient(transport=SoloGroq(), follow_redirects=False,
                                          trust_env=False, timeout=20.0),
        ) as cliente:
            respuesta = await cliente.chat.completions.create(
                model=modelo, messages=[{'role': 'system', 'content': instruccion},
                                       {'role': 'user', 'content': mensaje}],
                temperature=0.2, max_tokens=256,
                **opciones_razonamiento,
            )
    except Exception as exc:
        # Nunca str(exc), traceback, cuerpo, URL ni cabeceras del SDK.
        categoria = ('Timeout' if isinstance(exc, APITimeoutError) else
                     'ConnectionError' if isinstance(exc, APIConnectionError) else
                     'ProviderHttpError' if isinstance(exc, APIStatusError) else
                     'DiagnosticFailed')
        print(json.dumps({'error': categoria}))
        return 1

    choices = respuesta.choices
    opcion = choices[0] if choices else None
    message = getattr(opcion, 'message', None)
    content = getattr(message, 'content', None)
    reasoning = getattr(message, 'reasoning', None)
    motivo = getattr(opcion, 'finish_reason', None)
    usage = getattr(respuesta, 'usage', None)
    detalles = getattr(usage, 'completion_tokens_details', None)
    print(json.dumps({
        'requested_model': modelo if modelo in MODELOS_SEGUROS else 'other',
        'returned_model': respuesta.model if respuesta.model in MODELOS_SEGUROS else 'other',
        'finish_reason': motivo if motivo in MOTIVOS_SEGUROS else 'other',
        'content_length': len(content) if isinstance(content, str) else None,
        'reasoning_length': len(reasoning) if isinstance(reasoning, str) else None,
        'completion_tokens': numero(getattr(usage, 'completion_tokens', None)),
        'reasoning_tokens': numero(getattr(detalles, 'reasoning_tokens', None)),
    }, sort_keys=True))
    # Ejecutar únicamente el normalizador local puro, sin importar el paquete app,
    # su main, DB ni servicios de comunicaciones. No imprimir texto normalizado.
    try:
        sms = normalizador['adaptar_sms'](respuesta)
        normalizador['validar_sms'](sms)
    except ValueError:
        return 2
    if revision_ficticia:
        # Solo esta fixture incorporada; nunca acepta mensajes/clientes por CLI.
        # El texto no sale por stdout y no se guarda reasoning ni prompts.
        descriptor, ruta = tempfile.mkstemp(prefix='groq-sms-ficticio-', suffix='.txt', dir='/tmp')
        with os.fdopen(descriptor, 'w') as archivo:
            archivo.write(sms)
        print(json.dumps({'revision_ficticia_archivo': ruta}))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision-ficticia', action='store_true',
                        help='Guardar solo el SMS ficticio normalizado en un archivo temporal privado.')
    argumentos = parser.parse_args()
    try:
        codigo = asyncio.run(main(revision_ficticia=argumentos.revision_ficticia))
    except Exception:
        print(json.dumps({'error': 'DiagnosticFailed'}))
        codigo = 1
    raise SystemExit(codigo)
