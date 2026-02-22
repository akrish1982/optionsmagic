import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

from trade_automation.config import Settings
from trade_automation.store import load_state, save_state, update_request_status
from trade_automation.notifier_telegram import TelegramNotifier
from trade_automation.notifier_discord import DiscordNotifier
from trade_automation.tradestation import TradeStationTradingClient
from trade_automation.position_manager import PositionManager
from trade_automation.supabase_client import get_supabase_client
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

# Timeout for trade approval (5 minutes)
APPROVAL_TIMEOUT_MINUTES = 5


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


def is_expired(created_at: str, timeout_minutes: int = APPROVAL_TIMEOUT_MINUTES) -> bool:
    """Check if a trade request has exceeded the approval timeout."""
    try:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        expiry = created + timedelta(minutes=timeout_minutes)
        return datetime.utcnow() > expiry
    except Exception as e:
        logger.warning(f"Could not parse created_at '{created_at}': {e}")
        return False


def check_and_expire_requests(state: Dict[str, Any], notifier) -> None:
    """Check for expired requests and auto-reject them."""
    requests = state.get("requests", {})
    expired_count = 0

    for request_id, req in requests.items():
        if req.get("status") == "pending":
            created_at = req.get("created_at", "")
            if is_expired(created_at):
                update_request_status(state, request_id, "rejected", notes="Auto-rejected: timeout")
                notifier.send_message(f"⏱️ Request {request_id} auto-rejected (5 min timeout)")
                expired_count += 1

    if expired_count > 0:
        logger.info(f"Auto-rejected {expired_count} expired requests")


def _apply_commands(
    commands: List[Dict[str, str]],
    state: Dict[str, Any],
    settings: Settings,
    notifier,
    supabase_client,
    is_callback: bool = False
) -> None:
    """Process approve/reject commands (from text or callback)."""
    trader = TradeStationTradingClient(settings)
    position_mgr = PositionManager(supabase_client)

    for cmd in commands:
        request_id = cmd["request_id"]
        action = cmd["action"]
        message_id = cmd.get("message_id")

        req = state.get("requests", {}).get(request_id)
        if not req:
            if is_callback:
                notifier.answer_callback_query(cmd.get("callback_query_id"), "❌ Request not found")
            notifier.send_message(f"❌ Unknown request id: {request_id}")
            continue

        if req.get("status") != "pending":
            msg = f"Request {request_id} is already {req.get('status')}"
            if is_callback:
                notifier.answer_callback_query(cmd.get("callback_query_id"), msg)
            notifier.send_message(msg)
            continue

        # Check if expired
        if is_expired(req.get("created_at", "")):
            update_request_status(state, request_id, "rejected", notes="Auto-rejected: timeout")
            msg = f"⏱️ Request {request_id} expired and was auto-rejected"
            if is_callback:
                notifier.answer_callback_query(cmd.get("callback_query_id"), "⏱️ Request expired")
            notifier.send_message(msg)
            if message_id:
                notifier.edit_message_text(
                    message_id,
                    f"❌ <b>REJECTED (Expired)</b>\n\nID: <code>{request_id}</code>\n"
                    f"Ticker: {req.get('ticker')}\n<i>Auto-rejected after 5 minutes</i>"
                )
            continue

        if action == "reject":
            update_request_status(state, request_id, "rejected")
            if is_callback:
                notifier.answer_callback_query(cmd.get("callback_query_id"), "❌ Trade rejected")
            notifier.send_message(f"❌ Rejected {request_id}")
            if message_id:
                notifier.edit_message_text(
                    message_id,
                    f"❌ <b>REJECTED</b>\n\nID: <code>{request_id}</code>\n"
                    f"Ticker: {req.get('ticker')}\nStrategy: {req.get('strategy_type')}"
                )
            continue

        if action == "approve":
            update_request_status(state, request_id, "approved")
            if is_callback:
                notifier.answer_callback_query(cmd.get("callback_query_id"), "✅ Trade approved! Executing...")
            notifier.send_message(f"✅ Approved {request_id} - Executing...")

            trade = request_from_dict(req)
            try:
                result = trader.place_order(trade)
                if result.get("ok") or result.get("dry_run"):
                    update_request_status(state, request_id, "executed")
                    
                    # Create position record in database
                    try:
                        entry_price = result.get("execution_price", req.get("net_credit", 0))
                        quantity = int(req.get("quantity", 1))
                        position = position_mgr.create_position(
                            trade,
                            entry_price=entry_price,
                            quantity=quantity,
                            execution_data=result
                        )
                        notifier.send_message(
                            f"✅ Executed {request_id}\n"
                            f"Position ID: {position.get('position_id')}"
                        )
                    except Exception as pos_exc:
                        logger.error(f"Failed to create position for {request_id}: {pos_exc}")
                        notifier.send_message(
                            f"⚠️ Trade executed but position tracking failed: {pos_exc}"
                        )
                    
                    if message_id:
                        notifier.edit_message_text(
                            message_id,
                            f"✅ <b>APPROVED & EXECUTED</b>\n\nID: <code>{request_id}</code>\n"
                            f"Ticker: {req.get('ticker')}\nStrategy: {req.get('strategy_type')}\n"
                            f"<i>Trade has been submitted</i>"
                        )
                else:
                    update_request_status(state, request_id, "failed", notes=str(result))
                    notifier.send_message(f"❌ Failed {request_id}: {result}")
                    if message_id:
                        notifier.edit_message_text(
                            message_id,
                            f"⚠️ <b>APPROVED BUT FAILED</b>\n\nID: <code>{request_id}</code>\n"
                            f"Error: {result}"
                        )
            except Exception as exc:
                update_request_status(state, request_id, "failed", notes=str(exc))
                notifier.send_message(f"❌ Failed {request_id}: {exc}")
                if message_id:
                    notifier.edit_message_text(
                        message_id,
                        f"⚠️ <b>APPROVED BUT ERROR</b>\n\nID: <code>{request_id}</code>\n"
                        f"Error: {exc}"
                    )


def run_once(settings: Settings, state: Dict[str, Any],
             telegram: TelegramNotifier, discord: DiscordNotifier) -> None:
    # Initialize Supabase client
    try:
        supabase = get_supabase_client(settings)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        supabase = None
    
    # First, check for expired requests
    if "telegram" in settings.approval_backends:
        check_and_expire_requests(state, telegram)
    if "discord" in settings.approval_backends:
        check_and_expire_requests(state, discord)

    # Process callback queries (button clicks) first
    if "telegram" in settings.approval_backends:
        last_update_id = state.get("telegram", {}).get("last_update_id", 0)

        # Get callback queries
        callback_updates = telegram.get_callback_queries(offset=last_update_id + 1)
        if callback_updates:
            state.setdefault("telegram", {})["last_update_id"] = callback_updates[-1]["update_id"]
            callbacks = telegram.parse_callback_queries(callback_updates)
            if callbacks:
                logger.info(f"Processing {len(callbacks)} Telegram callbacks")
                _apply_commands(callbacks, state, settings, telegram, supabase, is_callback=True)

        # Also check for text commands (backward compatibility)
        updates = telegram.get_updates(offset=last_update_id + 1)
        if updates:
            state.setdefault("telegram", {})["last_update_id"] = updates[-1]["update_id"]
            commands = telegram.parse_commands(updates)
            if commands:
                logger.info(f"Processing {len(commands)} Telegram text commands")
                _apply_commands(commands, state, settings, telegram, supabase, is_callback=False)

    if "discord" in settings.approval_backends:
        last_message_id = state.get("discord", {}).get("last_message_id", "")
        messages = discord.get_messages()
        if messages:
            newest_id = max(int(msg["id"]) for msg in messages if msg.get("id"))
            state.setdefault("discord", {})["last_message_id"] = str(newest_id)
        commands = discord.parse_commands(messages, last_message_id)
        if commands:
            logger.info(f"Processing {len(commands)} Discord commands")
            _apply_commands(commands, state, settings, discord, supabase, is_callback=False)


def main():
    settings = Settings()
    telegram = TelegramNotifier(settings)
    discord = DiscordNotifier(settings)

    logger.info("Starting approval worker")
    logger.info(f"Approval timeout: {APPROVAL_TIMEOUT_MINUTES} minutes")

    while True:
        state = load_state()
        run_once(settings, state, telegram, discord)
        save_state(state)
        time.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()
