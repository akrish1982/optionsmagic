import logging
import json
from datetime import datetime

from trade_automation.config import Settings
from trade_automation.opportunities import fetch_opportunities, filter_opportunities, build_trade_request
from trade_automation.store import load_state, save_state, upsert_request
from trade_automation.notifier_telegram import TelegramNotifier
from trade_automation.notifier_discord import DiscordNotifier
from trade_automation.supabase_client import get_supabase_client


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/trade_automation.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


def format_trade_details(trade) -> str:
    """Format additional trade details for the message."""
    legs_info = []
    for leg in trade.legs:
        legs_info.append(f"{leg.action} {leg.quantity} {leg.contractid}")

    if trade.strategy_type == "VPC" and trade.width:
        return f"Spread width: ${trade.width:.2f} | Legs: {', '.join(legs_info)}"
    else:
        return f"Legs: {', '.join(legs_info)}"


def main():
    settings = Settings()
    state = load_state()

    supabase = get_supabase_client(settings)
    opportunities = fetch_opportunities(settings)
    opportunities = filter_opportunities(opportunities, settings)

    if not opportunities:
        logger.info("No opportunities found")
        return

    telegram = TelegramNotifier(settings)
    discord = DiscordNotifier(settings)

    created = 0
    for opp in opportunities:
        trade = build_trade_request(opp, supabase, settings)
        if not trade:
            continue
        if trade.request_id in state.get("requests", {}):
            continue

        trade_dict = json.loads(json.dumps(trade, default=lambda o: o.__dict__))

        # Store created_at for timeout tracking
        trade_dict["created_at"] = datetime.utcnow().isoformat()

        upsert_request(state, trade_dict)
        created += 1

        # Send with inline buttons via Telegram
        if "telegram" in settings.approval_backends and telegram.is_configured():
            details = format_trade_details(trade)
            result = telegram.send_trade_proposal_with_buttons(
                request_id=trade.request_id,
                ticker=trade.ticker,
                strategy=trade.strategy_type,
                expiration=trade.expiration_date,
                strike=trade.strike_price,
                return_pct=trade.return_pct,
                collateral=trade.collateral,
                details=details
            )
            if result:
                # Store message_id for later editing
                trade_dict["telegram_message_id"] = result.get("message_id")
                logger.info(f"Sent Telegram proposal for {trade.request_id}")
            else:
                logger.warning(f"Failed to send Telegram proposal for {trade.request_id}")

        # Send via Discord (text-based for now)
        if "discord" in settings.approval_backends:
            from trade_automation.messages import format_trade_request
            message = format_trade_request(trade)
            discord.send_message(message)

        logger.info("Queued trade request %s for %s", trade.request_id, trade.ticker)

    save_state(state)
    logger.info("Created %s trade requests", created)


if __name__ == "__main__":
    main()
