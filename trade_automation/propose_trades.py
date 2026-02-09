import logging
import json

from trade_automation.config import Settings
from trade_automation.opportunities import fetch_opportunities, filter_opportunities, build_trade_request
from trade_automation.store import load_state, save_state, upsert_request
from trade_automation.messages import format_trade_request
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
        upsert_request(state, trade_dict)
        created += 1

        message = format_trade_request(trade)
        if "telegram" in settings.approval_backends:
            telegram.send_message(message)
        if "discord" in settings.approval_backends:
            discord.send_message(message)

        logger.info("Queued trade request %s for %s", trade.request_id, trade.ticker)

    save_state(state)
    logger.info("Created %s trade requests", created)


if __name__ == "__main__":
    main()
