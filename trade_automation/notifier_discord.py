import requests
from typing import List, Dict, Any

from trade_automation.config import Settings


class DiscordNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = "https://discord.com/api/v10"

    def is_configured(self) -> bool:
        return bool(self.settings.discord_bot_token and self.settings.discord_channel_id)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bot {self.settings.discord_bot_token}"}

    def send_message(self, text: str) -> None:
        if not self.is_configured():
            return
        requests.post(
            f"{self.base_url}/channels/{self.settings.discord_channel_id}/messages",
            json={"content": text},
            headers=self._headers(),
            timeout=15,
        )

    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        response = requests.get(
            f"{self.base_url}/channels/{self.settings.discord_channel_id}/messages",
            params={"limit": limit},
            headers=self._headers(),
            timeout=15,
        )
        if not response.ok:
            return []
        return response.json()

    def parse_commands(self, messages: List[Dict[str, Any]], last_message_id: str) -> List[Dict[str, str]]:
        commands = []
        last_seen = int(last_message_id) if last_message_id else 0
        for message in messages:
            message_id = message.get("id")
            if message_id and int(message_id) <= last_seen:
                continue
            author_id = str(message.get("author", {}).get("id", ""))
            if self.settings.discord_approver_ids and author_id not in self.settings.discord_approver_ids:
                continue
            content = (message.get("content") or "").strip()
            if not content:
                continue
            parts = content.split()
            if len(parts) < 2:
                continue
            action = parts[0].lower()
            request_id = parts[1].strip()
            if action in {"approve", "reject"}:
                commands.append({"action": action, "request_id": request_id, "source": "discord"})
        return commands
