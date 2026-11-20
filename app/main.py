import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.services.telegram_service import TelegramService
from app.services.hn_scanner import HNScanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("security-guardian")

telegram_service = TelegramService()
hn_scanner = HNScanner(min_score=settings.HN_MIN_SCORE)
scheduler = AsyncIOScheduler()


async def run_security_scan():
    """Performs full scan and notifies via Telegram if new stories or alerts found."""
    logger.info("🛡️ Iniciando escaneo de seguridad...")
    stories = await hn_scanner.fetch_security_stories()
    logger.info(f"HN Scanner encontró {len(stories)} historias relevantes.")

    for story in stories:
        msg = (
            f"🔥 <b>Alerta Hacker News — Seguridad</b>\n\n"
            f"<b>Título:</b> {story['title']}\n"
            f"<b>Puntuación:</b> ⭐ {story['points']} pts | 💬 {story['num_comments']} comentarios\n"
        )
        buttons = [
            {"text": "💬 Debate en HN", "url": story["hn_url"]},
        ]
        if story["url"] != story["hn_url"]:
            buttons.append({"text": "🔗 Leer Artículo", "url": story["url"]})

        sent = await telegram_service.send_message(text=msg, buttons=buttons)
        if sent:
            hn_scanner.mark_as_seen(story["id"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: configure scheduler
    logger.info("Iniciando Security Guardian...")
    scheduler.add_job(
        run_security_scan,
        "interval",
        hours=settings.CHECK_INTERVAL_HOURS,
        id="hn_security_scan"
    )
    scheduler.start()
    logger.info(f"Scheduler activo. Intervalo: cada {settings.CHECK_INTERVAL_HOURS} horas.")

    # Send a startup notification to Telegram if credentials are set
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        await telegram_service.send_message(
            text=(
                "🛡️ <b>Security Guardian iniciado</b> 🚀\n\n"
                f"• <b>Servidor:</b> RHEL 10.1 (K8s Cluster)\n"
                f"• <b>Vigilancia:</b> Cada {settings.CHECK_INTERVAL_HOURS}h\n"
                f"• <b>Filtro HN:</b> Score ≥ {settings.HN_MIN_SCORE} pts\n"
            )
        )
        # Run first scan right away
        await run_security_scan()

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Security Guardian detenido.")


app = FastAPI(
    title="Security Guardian",
    version="1.0.0",
    description="Sentinel microservice for infrastructure security alerts",
    lifespan=lifespan
)


@app.get("/")
def read_root():
    return {
        "service": "Security Guardian",
        "status": "online",
        "interval_hours": settings.CHECK_INTERVAL_HOURS,
        "min_hn_score": settings.HN_MIN_SCORE,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger an immediate scan."""
    background_tasks.add_task(run_security_scan)
    return {"message": "Escaneo iniciado en segundo plano"}
