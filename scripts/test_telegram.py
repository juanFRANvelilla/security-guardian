import asyncio
import sys
import os

# Add parent dir to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.telegram_service import TelegramService
from app.config import settings


async def main():
    token = sys.argv[1] if len(sys.argv) > 1 else settings.TELEGRAM_BOT_TOKEN
    chat_id = sys.argv[2] if len(sys.argv) > 2 else settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("❌ Error: Faltan credenciales.")
        print("Uso:")
        print("  python3 scripts/test_telegram.py <BOT_TOKEN> <CHAT_ID>")
        print("o define TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en un archivo .env")
        sys.exit(1)

    print(f"📡 Probando conexión con el bot...")
    service = TelegramService(token=token, chat_id=chat_id)

    bot_info = await service.get_bot_info()
    if not bot_info:
        print("❌ No se pudo conectar con el bot. Revisa que el BOT_TOKEN sea correcto.")
        sys.exit(1)

    bot_username = bot_info.get("username", "Desconocido")
    print(f"✅ Bot identificado correctamente: @{bot_username}")
    print(f"📨 Enviando mensaje de prueba al chat ID: {chat_id}...")

    msg = (
        "🛡️ <b>Security Guardian — Prueba de Conexión</b>\n\n"
        "¡Hola Juanfran! Si estás leyendo esto, la integración con Telegram funciona a la perfección. 🚀\n\n"
        "<b>Servidor monitorizado:</b> <code>192.168.0.176</code> (RHEL 10.1 / K8s Cluster)\n"
        "<b>Estado del guardián:</b> Listo para vigilar vulnerabilidades y Hacker News."
    )

    buttons = [
        {"text": "🔥 Hacker News", "url": "https://news.ycombinator.com"},
        {"text": "🛡️ CISA KEV", "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"}
    ]

    ok = await service.send_message(text=msg, buttons=buttons)
    if ok:
        print("🎉 ¡Mensaje enviado con éxito! Revisa tu Telegram.")
    else:
        print("❌ Falló el envío del mensaje. Asegúrate de haber presionado 'Iniciar' o '/start' en el chat con el bot.")


if __name__ == "__main__":
    asyncio.run(main())
