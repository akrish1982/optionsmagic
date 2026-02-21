import requests
from typing import List, Dict, Any, Optional

from trade_automation.config import Settings


class TelegramNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    def is_configured(self) -> bool:
        return bool(self.settings.telegram_bot_token and self.settings.telegram_chat_id)

    def send_message(self, text: str) -> Optional[Dict[str, Any]]:
        if not self.is_configured():
            return None
        response = requests.post(
            f"{self.base_url}/sendMessage",
            json={"chat_id": self.settings.telegram_chat_id, "text": text},
            timeout=15,
        )
        if response.ok:
            return response.json().get("result")
        return None

    def send_trade_proposal_with_buttons(
        self,
        request_id: str,
        ticker: str,
        strategy: str,
        expiration: str,
        strike: float,
        return_pct: Optional[float],
        collateral: Optional[float],
        details: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Send a trade proposal with inline APPROVE/REJECT buttons.
        Returns the message object for tracking message_id.
        """
        if not self.is_configured():
            return None

        # Format the message
        text = (
            f"📊 <b>Trade Approval Request</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>ID:</b> <code>{request_id}</code>\n"
            f"<b>Strategy:</b> {strategy}\n"
            f"<b>Ticker:</b> {ticker}\n"
            f"<b>Expiration:</b> {expiration}\n"
            f"<b>Strike:</b> ${strike:.2f}\n"
        )

        if return_pct is not None:
            text += f"<b>Return:</b> {return_pct:.2f}%\n"
        if collateral is not None:
            text += f"<b>Collateral:</b> ${collateral:,.2f}\n"

        if details:
            text += f"\n<i>{details}</i>\n"

        text += f"\n⏱️ <i>Auto-reject in 5 minutes</i>"

        # Create inline keyboard with APPROVE/REJECT buttons
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ APPROVE", "callback_data": f"approve:{request_id}"},
                    {"text": "❌ REJECT", "callback_data": f"reject:{request_id}"}
                ]
            ]
        }

        response = requests.post(
            f"{self.base_url}/sendMessage",
            json={
                "chat_id": self.settings.telegram_chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": reply_markup
            },
            timeout=15,
        )

        if response.ok:
            result = response.json().get("result")
            return result
        else:
            print(f"Failed to send message: {response.text}")
            return None

    def edit_message_text(
        self,
        message_id: int,
        text: str,
        reply_markup: Optional[Dict] = None
    ) -> bool:
        """Edit an existing message (used to update after approval/rejection)."""
        if not self.is_configured():
            return False

        payload = {
            "chat_id": self.settings.telegram_chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        response = requests.post(
            f"{self.base_url}/editMessageText",
            json=payload,
            timeout=15,
        )
        return response.ok

    def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> bool:
        """Answer a callback query to stop the loading animation."""
        if not self.is_configured():
            return False

        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text

        response = requests.post(
            f"{self.base_url}/answerCallbackQuery",
            json=payload,
            timeout=15,
        )
        return response.ok

    def get_updates(self, offset: int) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        response = requests.get(
            f"{self.base_url}/getUpdates",
            params={"timeout": 10, "offset": offset},
            timeout=20,
        )
        if not response.ok:
            return []
        data = response.json()
        return data.get("result", [])

    def get_callback_queries(self, offset: int) -> List[Dict[str, Any]]:
        """Get updates and filter for callback queries (button clicks)."""
        updates = self.get_updates(offset)
        callbacks = []
        for update in updates:
            if "callback_query" in update:
                callbacks.append(update)
        return callbacks

    def parse_commands(self, updates: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        commands = []
        for update in updates:
            message = update.get("message", {})
            text = (message.get("text") or "").strip()
            sender_id = str(message.get("from", {}).get("id", ""))
            if not text:
                continue
            if self.settings.telegram_approver_ids and sender_id not in self.settings.telegram_approver_ids:
                continue
            parts = text.split()
            if len(parts) < 2:
                continue
            action = parts[0].lstrip("/").lower()
            request_id = parts[1].strip()
            if action in {"approve", "reject"}:
                commands.append({"action": action, "request_id": request_id, "source": "telegram"})
        return commands

    def parse_callback_queries(self, updates: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Parse callback queries from button clicks."""
        commands = []
        for update in updates:
            callback = update.get("callback_query", {})
            data = callback.get("data", "")
            sender_id = str(callback.get("from", {}).get("id", ""))

            if not data or ":" not in data:
                continue

            # Check if sender is authorized
            if self.settings.telegram_approver_ids and sender_id not in self.settings.telegram_approver_ids:
                continue

            action, request_id = data.split(":", 1)
            if action in {"approve", "reject"}:
                commands.append({
                    "action": action,
                    "request_id": request_id,
                    "source": "telegram",
                    "callback_query_id": callback.get("id"),
                    "message_id": callback.get("message", {}).get("message_id")
                })
        return commands
