import json
import logging
import time
from typing import Dict, Any, List

from trade_automation.config import Settings
from trade_automation.store import load_state, save_state, update_request_status
from trade_automation.notifier_telegram import TelegramNotifier
from trade_automation.notifier_discord import DiscordNotifier
from trade_automation.tradestation import TradeStationTradingClient
from trade_automation.models import TradeRequest, OptionLeg


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/trade_automation.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


def request_from_dict(data: Dict[str, Any]) -> TradeRequest:
    legs = [OptionLeg(**leg) for leg in data.get("legs", [])]
    return TradeRequest(
        request_id=data["request_id"],
        strategy_type=data.get("strategy_type"),
        ticker=data.get("ticker"),
        expiration_date=data.get("expiration_date"),
        strike_price=float(data.get("strike_price")),
        width=data.get("width"),
        net_credit=data.get("net_credit"),
        collateral=data.get("collateral"),
        return_pct=data.get("return_pct"),
        quantity=int(data.get("quantity", 1)),
        legs=legs,
        source_opportunity_id=data.get("source_opportunity_id"),
        created_at=data.get("created_at"),
        status=data.get("status", "pending"),
        notes=data.get("notes", ""),
    )


def _apply_commands(commands: List[Dict[str, str]], state: Dict[str, Any],
                    settings: Settings, notifier) -> None:
    trader = TradeStationTradingClient(settings)

    for cmd in commands:
        request_id = cmd["request_id"]
        action = cmd["action"]

        req = state.get("requests", {}).get(request_id)
        if not req:
            notifier.send_message(f"Unknown request id: {request_id}")
            continue
        if req.get("status") != "pending":
            notifier.send_message(f"Request {request_id} is already {req.get('status')}")
            continue

        if action == "reject":
            update_request_status(state, request_id, "rejected")
            notifier.send_message(f"Rejected {request_id}")
            continue

        if action == "approve":
            update_request_status(state, request_id, "approved")
            trade = request_from_dict(req)
            try:
                result = trader.place_order(trade)
                if result.get("ok") or result.get("dry_run"):
                    update_request_status(state, request_id, "executed")
                    notifier.send_message(f"Executed {request_id}")
                else:
                    update_request_status(state, request_id, "failed", notes=str(result))
                    notifier.send_message(f"Failed {request_id}: {result}")
            except Exception as exc:
                update_request_status(state, request_id, "failed", notes=str(exc))
                notifier.send_message(f"Failed {request_id}: {exc}")


def run_once(settings: Settings, state: Dict[str, Any],
             telegram: TelegramNotifier, discord: DiscordNotifier) -> None:
    commands: List[Dict[str, str]] = []

    if "telegram" in settings.approval_backends:
        last_update_id = state.get("telegram", {}).get("last_update_id", 0)
        updates = telegram.get_updates(offset=last_update_id + 1)
        if updates:
            state.setdefault("telegram", {})["last_update_id"] = updates[-1]["update_id"]
        commands.extend(telegram.parse_commands(updates))

    if "discord" in settings.approval_backends:
        last_message_id = state.get("discord", {}).get("last_message_id", "")
        messages = discord.get_messages()
        if messages:
            newest_id = max(int(msg["id"]) for msg in messages if msg.get("id"))
            state.setdefault("discord", {})["last_message_id"] = str(newest_id)
        commands.extend(discord.parse_commands(messages, last_message_id))

    for cmd in commands:
        if cmd.get("source") == "telegram":
            _apply_commands([cmd], state, settings, telegram)
        elif cmd.get("source") == "discord":
            _apply_commands([cmd], state, settings, discord)


def main():
    settings = Settings()
    telegram = TelegramNotifier(settings)
    discord = DiscordNotifier(settings)

    logger.info("Starting approval worker")
    while True:
        state = load_state()
        run_once(settings, state, telegram, discord)
        save_state(state)
        time.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()
