import logging
from typing import List, Dict, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        buttons: Optional[List[Dict[str, str]]] = None,
        disable_web_page_preview: bool = True
    ) -> bool:
        """
        Sends a message to Telegram.
        `buttons` should be a list of dicts like:
        [{"text": "Ver en HN", "url": "https://..."}, ...]
        """
        if not self.token or not self.chat_id:
            logger.error("Telegram BOT token or Chat ID is missing!")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }

        if buttons:
            inline_keyboard = [[{"text": b["text"], "url": b["url"]} for b in buttons]]
            payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    logger.info("Telegram message sent successfully.")
                    return True
                else:
                    logger.error(
                        f"Failed to send Telegram message: {response.status_code} - {response.text}"
                    )
                    return False
        except Exception as e:
            logger.exception(f"Exception sending message to Telegram: {e}")
            return False

    async def get_bot_info(self) -> Optional[dict]:
        """Verify bot token and return bot user info."""
        if not self.token:
            return None
        url = f"{self.base_url}/getMe"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return res.json().get("result")
        except Exception as e:
            logger.error(f"Error fetching bot info: {e}")
        return None
