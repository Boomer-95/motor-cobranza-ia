import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"), 
    base_url="https://api.groq.com/openai/v1"
)

async def main():
    try:
        modelos = await client.models.list()
        print("✅ Modelos permitidos para tu API Key:")
        for m in modelos.data:
            print(f"- {m.id}")
    except Exception as e:
        print(f"Error al consultar: {e}")

asyncio.run(main())