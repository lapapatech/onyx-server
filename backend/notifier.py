"""Telegram notifications when targets become active."""

import logging
import os
from typing import Optional

import httpx

log = logging.getLogger("onyx.notifier")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Hours of inactivity after which we re-notify (default 24h)
INACTIVITY_HOURS = int(os.getenv("ONYX_NOTIFY_INACTIVITY_HOURS", "24"))


class TelegramNotifier:
    """Send alerts via Telegram bot when targets are active."""

    def __init__(self):
        self.token = os.getenv("ONYX_TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("ONYX_TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.token and self.chat_id)

    async def send(self, text: str) -> bool:
        """Send message to Telegram. Returns True if sent."""
        if not self.enabled:
            return False

        url = TELEGRAM_API.format(token=self.token)
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    log.info("Telegram notification sent: %s", text[:80])
                    return True
                else:
                    log.warning("Telegram send failed: HTTP %s — %s", resp.status_code, resp.text[:200])
                    return False
        except Exception as e:
            log.error("Telegram send error: %s", e)
            return False

    async def notify_active(
        self,
        user_name: str,
        model: str,
        message_preview: str,
        is_new_user: bool = False,
        is_returning: bool = False,
        hours_away: Optional[int] = None,
        session_count: Optional[int] = None,
        total_messages: Optional[int] = None,
    ) -> bool:
        """Send notification about active target.

        Returns True if notification was sent.
        """
        if not self.enabled:
            return False

        tag = ""
        if is_new_user:
            tag = " 🆕 NEW TARGET"
        elif is_returning and hours_away:
            tag = f" 🔄 BACK after {hours_away}h"

        stats = ""
        if session_count is not None:
            stats += f"Sessions: {session_count}"
        if total_messages is not None:
            stats += f" | Messages: {total_messages}"

        text = (
            f"<b>⬡ Onyx Activity{tag}</b>\n\n"
            f"<b>User:</b> {_escape(user_name)}\n"
            f"<b>Model:</b> {model}\n"
            f"<b>Message:</b> {_escape(message_preview[:200])}\n"
        )
        if stats:
            text += f"\n{stats}"

        return await self.send(text)


def _escape(text: str) -> str:
    """Escape HTML special chars."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Singleton
notifier = TelegramNotifier()
