"""Consulta manual de modelos; nunca se ejecuta al importar ni expone excepciones."""
import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv


async def main():
    load_dotenv()
    clave = os.getenv('GROQ_API_KEY', '').strip()
    if not clave:
        print('Servicio de IA no configurado.')
        return
    client = None
    try:
        client = AsyncOpenAI(api_key=clave, base_url='https://api.groq.com/openai/v1',
                             timeout=20.0, max_retries=0)
        modelos = await client.models.list()
        print('Modelos permitidos:')
        for modelo in modelos.data:
            print(f'- {modelo.id}')
    except Exception:
        print('Error al consultar: ProviderRequestFailed')
    finally:
        if client is not None:
            try:
                await client.close()
            except Exception:
                print('Error al cerrar cliente: ProviderRequestFailed')


if __name__ == '__main__':
    asyncio.run(main())
