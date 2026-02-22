import json
import os
from pathlib import Path


def _load_tokens_file():
    """Load TradeStation credentials from tokens.json if it exists."""
    # Try to find tokens.json in project root
    config_dir = Path(__file__).parent.parent
    tokens_path = config_dir / "tokens.json"

    if tokens_path.exists():
        try:
            with open(tokens_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _split_csv(value: str):
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def get_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class Settings:
    def __init__(self):
        # Supabase
        self.supabase_url = os.environ.get("SUPABASE_URL", "")
        self.supabase_key = os.environ.get("SUPABASE_KEY", "")
        self.supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        self.opportunities_table = os.environ.get("OPPORTUNITIES_TABLE", "options_opportunities")

        # TradeStation auth - prefer env vars, fall back to tokens.json
        tokens = _load_tokens_file()
        self.ts_client_id = os.environ.get("TRADESTATION_CLIENT_ID") or tokens.get("client_id", "")
        self.ts_client_secret = os.environ.get("TRADESTATION_CLIENT_SECRET") or tokens.get("client_secret", "")
        self.ts_refresh_token = os.environ.get("TRADESTATION_REFRESH_TOKEN") or tokens.get("refresh_token", "")

        # TradeStation order settings
        self.ts_api_base = os.environ.get("TRADESTATION_API_BASE_URL", "https://api.tradestation.com/v3")
        self.ts_order_url = os.environ.get("TRADESTATION_ORDER_URL", "")
        self.ts_account_id = os.environ.get("TRADESTATION_ACCOUNT_ID", "")
        self.ts_dry_run = get_bool("TRADESTATION_DRY_RUN", True)
        # SIM default is safer for first-time setup.
        self.ts_env = os.environ.get("TRADESTATION_ENV", "SIM").upper()
        self.ts_order_type = os.environ.get("TRADESTATION_ORDER_TYPE", "Market")
        self.ts_time_in_force = os.environ.get("TRADESTATION_TIME_IN_FORCE", "DAY")
        self.ts_limit_price = os.environ.get("TRADESTATION_LIMIT_PRICE", "")

        # Approval backends
        self.approval_backends = _split_csv(os.environ.get("TRADE_APPROVAL_BACKENDS", "telegram"))

        # Telegram
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        self.telegram_approver_ids = _split_csv(os.environ.get("TELEGRAM_APPROVER_IDS", ""))

        # Discord
        self.discord_bot_token = os.environ.get("DISCORD_BOT_TOKEN", "")
        self.discord_channel_id = os.environ.get("DISCORD_CHANNEL_ID", "")
        self.discord_approver_ids = _split_csv(os.environ.get("DISCORD_APPROVER_IDS", ""))

        # Trade filters
        self.opportunities_limit = int(os.environ.get("OPPORTUNITIES_LIMIT", "10"))
        self.min_return_pct = float(os.environ.get("OPPORTUNITIES_MIN_RETURN_PCT", "0"))
        self.max_collateral = float(os.environ.get("OPPORTUNITIES_MAX_COLLATERAL", "0"))
        self.strategy_types = _split_csv(os.environ.get("OPPORTUNITIES_STRATEGIES", ""))

        # Execution
        self.default_quantity = int(os.environ.get("TRADE_QUANTITY", "1"))
        self.poll_interval_seconds = int(os.environ.get("APPROVAL_POLL_SECONDS", "10"))

        # Backward-compatible alias used in older docs/scripts.
        self.tradestation_dry_run = self.ts_dry_run

    def supabase_auth_key(self) -> str:
        return self.supabase_service_role_key or self.supabase_key

    def ts_order_endpoint(self) -> str:
        if self.ts_order_url:
            return self.ts_order_url
        if self.ts_env == "SIM":
            return "https://sim-api.tradestation.com/v3/orderexecution/orders"
        return f"{self.ts_api_base}/orderexecution/orders"
