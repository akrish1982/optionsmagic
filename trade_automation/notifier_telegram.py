import requests
from typing import List, Dict, Any

from trade_automation.config import Settings


class TelegramNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    def is_configured(self) -> bool:
        return bool(self.settings.telegram_bot_token and self.settings.telegram_chat_id)

    def send_message(self, text: str) -> None:
        if not self.is_configured():
            return
        requests.post(
            f"{self.base_url}/sendMessage",
            json={"chat_id": self.settings.telegram_chat_id, "text": text},
            timeout=15,
        )

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
