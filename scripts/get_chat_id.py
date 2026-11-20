import asyncio
import sys
import os
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config import settings


async def main():
    token = sys.argv[1] if len(sys.argv) > 1 else settings.TELEGRAM_BOT_TOKEN
    if not token:
        print("❌ Faltó el BOT_TOKEN. Pásalo como argumento o ponlo en .env")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()

    results = data.get("result", [])
    if not results:
        print("⚠️ No hay mensajes recientes. Abre tu bot en Telegram y dale a 'Iniciar' o escribe cualquier mensaje.")
        return

    print("🔎 Últimos chats detectados:")
    for item in results:
        msg = item.get("message") or item.get("channel_post")
        if msg:
            chat = msg.get("chat", {})
            user = msg.get("from", {})
            print(f" -> Chat ID: {chat.get('id')} | De: {user.get('first_name')} (@{user.get('username')})")


if __name__ == "__main__":
    asyncio.run(main())
