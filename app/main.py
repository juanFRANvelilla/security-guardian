import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.services.telegram_service import TelegramService
from app.services.hn_scanner import HNScanner
from app.services.rhel_scanner import RHELScanner
from app.services.alert_store import alert_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("security-guardian")

telegram_service = TelegramService()
hn_scanner = HNScanner(min_score=settings.HN_MIN_SCORE)
rhel_scanner = RHELScanner()
scheduler = AsyncIOScheduler()


async def scan_rhel_host():
    """Checks host RHEL 10 for official pending security updates via DNF."""
    if not settings.ENABLE_HOST_INSPECTION or not settings.HOST_SSH_PASSWORD:
        return

    logger.info("🛡️ Comprobando parches de seguridad del host RHEL 10...")
    # Run sync paramiko call in executor to not block event loop
    loop = asyncio.get_running_loop()
    updates = await loop.run_in_executor(None, rhel_scanner.check_security_updates)

    critical = updates.get("critical", [])
    important = updates.get("important", [])

    if not critical and not important:
        logger.info("No hay nuevos parches de seguridad para el host RHEL 10.")
        return

    msg = "🛡️ <b>RHEL 10 — Nuevos Parches de Seguridad Oficiales</b>\n\n"
    msg += "Se han detectado nuevos parches oficiales en los repositorios de tu servidor:\n\n"

    all_to_mark = []

    if critical:
        msg += "🔴 <b>CRÍTICOS:</b>\n"
        for item in critical[:5]:
            msg += f"• <code>{item['package']}</code> ({item['rhsa']})\n"
            all_to_mark.append(item['id'])
        msg += "\n"

    if important:
        msg += "🟠 <b>IMPORTANTES:</b>\n"
        for item in important[:8]:
            msg += f"• <code>{item['package']}</code> ({item['rhsa']})\n"
            all_to_mark.append(item['id'])
        if len(important) > 8:
            msg += f"<i>... y {len(important) - 8} paquetes más.</i>\n"
        msg += "\n"

    msg += "<b>Comando para aplicar solo seguridad:</b>\n"
    msg += "👉 <code>sudo dnf upgrade --security</code>"

    buttons = [
        {"text": "📖 Red Hat Advisories", "url": "https://access.redhat.com/security/security-updates/#/security-advisories"}
    ]

    sent = await telegram_service.send_message(text=msg, buttons=buttons)
    if sent:
        for aid in all_to_mark:
            alert_store.mark_seen(aid)


async def scan_hacker_news():
    """Scans Hacker News strictly filtered for Linux, Kernel, K8s, and server components."""
    logger.info("🔥 Escaneando Hacker News (filtro estricto para Linux / K8s)...")
    stories = await hn_scanner.fetch_security_stories()

    for story in stories:
        msg = (
            f"🔥 <b>Alerta Crítica — Hacker News</b>\n\n"
            f"<b>Vulnerabilidad / Noticia:</b> {story['title']}\n"
            f"<b>Impacto:</b> ⭐ {story['points']} pts | 💬 {story['num_comments']} comentarios\n"
        )
        buttons = [
            {"text": "💬 Debate en HN", "url": story["hn_url"]},
        ]
        if story["url"] != story["hn_url"]:
            buttons.append({"text": "🔗 Leer Artículo", "url": story["url"]})

        sent = await telegram_service.send_message(text=msg, buttons=buttons)
        if sent:
            hn_scanner.mark_as_seen(story["id"])


async def run_security_scan():
    """Performs full scan: Host RHEL 10 + Hacker News."""
    logger.info("🛡️ Iniciando escaneo completo de Security Guardian...")
    await scan_rhel_host()
    await scan_hacker_news()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Security Guardian...")
    scheduler.add_job(
        run_security_scan,
        "interval",
        hours=settings.CHECK_INTERVAL_HOURS,
        id="full_security_scan"
    )
    scheduler.start()
    logger.info(f"Scheduler activo. Intervalo: cada {settings.CHECK_INTERVAL_HOURS} horas.")

    # Startup scan
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        asyncio.create_task(run_security_scan())

    yield

    scheduler.shutdown()
    logger.info("Security Guardian detenido.")


app = FastAPI(
    title="Security Guardian",
    version="1.1.0",
    description="Sentinel microservice for RHEL 10 & Kubernetes security alerts",
    lifespan=lifespan
)


@app.get("/")
def read_root():
    return {
        "service": "Security Guardian",
        "status": "online",
        "interval_hours": settings.CHECK_INTERVAL_HOURS,
        "min_hn_score": settings.HN_MIN_SCORE,
        "host_inspection": settings.ENABLE_HOST_INSPECTION,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger an immediate scan."""
    background_tasks.add_task(run_security_scan)
    return {"message": "Escaneo iniciado en segundo plano"}
