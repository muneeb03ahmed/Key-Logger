from __future__ import annotations
import requests
import logging

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, discord_webhook: str | None = None, telegram_token: str | None = None, telegram_chat_id: str | None = None):
        self.discord_webhook = discord_webhook or ""
        self.telegram_token = telegram_token or ""
        self.telegram_chat_id = telegram_chat_id or ""

    def post_summary(self, summary: str) -> None:
        # Fail gracefully on network errors
        if self.discord_webhook:
            try:
                resp = requests.post(self.discord_webhook, json={"content": summary}, timeout=5)
                if not resp.ok:
                    logger.warning("Discord webhook returned %s", resp.status_code)
            except Exception as e:
                logger.warning("Discord webhook error: %s", e)
        if self.telegram_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                resp = requests.post(url, json={"chat_id": self.telegram_chat_id, "text": summary}, timeout=5)
                if not resp.ok:
                    logger.warning("Telegram sendMessage returned %s", resp.status_code)
            except Exception as e:
                logger.warning("Telegram error: %s", e)