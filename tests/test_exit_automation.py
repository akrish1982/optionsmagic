import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from trade_automation.config import Settings
from trade_automation.exit_automation import ExitAutomation
from trade_automation.position_manager import PositionManager
from trade_automation.models import TradeRequest, OptionLeg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_position(
    position_id=1,
    ticker="SPY",
    strategy_type="CSP",
    entry_price=1.50,
    profit_target=0.75,
    stop_loss=3.00,
    quantity=1,
    expiration="2026-09-18",
    contractid="SPY260918P00540000",
    action="Sell",
    status="OPEN",
):
    return {
        "position_id": position_id,
        "request_id": f"req-{position_id}",
        "ticker": ticker,
        "strategy_type": strategy_type,
        "status": status,
        "entry_date": datetime.utcnow().isoformat(),
        "entry_price": entry_price,
        "quantity": quantity,
        "profit_target": profit_target,
        "stop_loss": stop_loss,
        "legs": [
            {
                "contractid": contractid,
                "action": action,
                "quantity": 1,
                "option_type": "put",
                "strike": 540.0,
                "expiration": expiration,
            }
        ],
    }


def _make_vpc_position(
    position_id=2,
    entry_price=0.80,
    profit_target=0.40,
    stop_loss=5.0,
    expiration="2026-09-18",
):
    return {
        "position_id": position_id,
        "request_id": f"req-{position_id}",
        "ticker": "AAPL",
        "strategy_type": "VPC",
        "status": "OPEN",
        "entry_date": datetime.utcnow().isoformat(),
        "entry_price": entry_price,
        "quantity": 1,
        "profit_target": profit_target,
        "stop_loss": stop_loss,
        "legs": [
            {
                "contractid": "AAPL260918P00200000",
                "action": "Sell",
                "quantity": 1,
                "option_type": "put",
                "strike": 200.0,
                "expiration": expiration,
            },
            {
                "contractid": "AAPL260918P00195000",
                "action": "Buy",
                "quantity": 1,
                "option_type": "put",
                "strike": 195.0,
                "expiration": expiration,
            },
        ],
    }


class FakeQueryBuilder:
    """Simulates supabase query chaining."""

    def __init__(self, data):
        self._data = data

    def select(self, _fields):
        return self

    def eq(self, field, value):
        self._data = [r for r in self._data if r.get(field) == value]
        return self

    def order(self, _field, desc=False):
        return self

    def limit(self, _n):
        self._data = self._data[:_n]
        return self

    def update(self, data):
        for row in self._data:
            row.update(data)
        return self

    def insert(self, data):
        self._data = [data]
        return self

    def execute(self):
        resp = MagicMock()
        resp.data = self._data
        return resp


class FakeSupabase:
    """Minimal Supabase stub with configurable option quotes."""

    def __init__(self, option_quotes=None, positions=None, trade_history=None):
        self._option_quotes = option_quotes or []
        self._positions = positions or []
        self._trade_history = trade_history or []

    def table(self, name):
        if name == "options_quotes":
            return FakeQueryBuilder(list(self._option_quotes))
        if name == "positions":
            return FakeQueryBuilder(list(self._positions))
        if name == "trade_history":
            return FakeQueryBuilder(list(self._trade_history))
        return FakeQueryBuilder([])


@pytest.fixture
def configured_env(monkeypatch):
    env = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "test-key",
        "TRADESTATION_ACCOUNT_ID": "SIM-123",
        "TRADESTATION_DRY_RUN": "true",
        "TRADESTATION_ENV": "SIM",
        "TRADE_APPROVAL_BACKENDS": "telegram",
        "TELEGRAM_BOT_TOKEN": "token",
        "TELEGRAM_CHAT_ID": "chat-id",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)


# ---------------------------------------------------------------------------
# _get_cost_to_close tests
# ---------------------------------------------------------------------------

class TestGetCostToClose:
    def test_csp_cost_is_mid_price_of_short_leg(self, configured_env):
        quotes = [
            {"contractid": "SPY260918P00540000", "bid": 0.60, "ask": 0.80, "mark": 0.70, "quote_date": "2026-03-06"},
        ]
        supabase = FakeSupabase(option_quotes=quotes)
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        position = _make_position()
        cost = asyncio.run(ea._get_cost_to_close(position))
        # Sold put: cost to close = mark price of short leg
        assert cost == pytest.approx(0.70)

    def test_vpc_cost_is_short_minus_long(self, configured_env):
        quotes = [
            {"contractid": "AAPL260918P00200000", "bid": 1.00, "ask": 1.20, "mark": 1.10, "quote_date": "2026-03-06"},
            {"contractid": "AAPL260918P00195000", "bid": 0.40, "ask": 0.60, "mark": 0.50, "quote_date": "2026-03-06"},
        ]
        supabase = FakeSupabase(option_quotes=quotes)
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        position = _make_vpc_position()
        cost = asyncio.run(ea._get_cost_to_close(position))
        # Buy back short (1.10) minus sell long (0.50) = 0.60
        assert cost == pytest.approx(0.60)

    def test_returns_none_when_no_quotes(self, configured_env):
        supabase = FakeSupabase(option_quotes=[])
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        position = _make_position()
        cost = asyncio.run(ea._get_cost_to_close(position))
        assert cost is None

    def test_falls_back_to_bid_ask_when_mark_zero(self, configured_env):
        quotes = [
            {"contractid": "SPY260918P00540000", "bid": 0.60, "ask": 0.80, "mark": 0, "quote_date": "2026-03-06"},
        ]
        supabase = FakeSupabase(option_quotes=quotes)
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        position = _make_position()
        cost = asyncio.run(ea._get_cost_to_close(position))
        assert cost == pytest.approx(0.70)  # (0.60 + 0.80) / 2


# ---------------------------------------------------------------------------
# Profit target tests
# ---------------------------------------------------------------------------

class TestProfitTarget:
    def test_triggers_when_profit_exceeds_target(self, configured_env):
        supabase = FakeSupabase()
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        # entry_price=1.50, profit_target=0.75
        # cost_to_close=0.70 -> profit = 1.50 - 0.70 = 0.80 >= 0.75
        position = _make_position(entry_price=1.50, profit_target=0.75)
        assert ea._check_profit_target(position, cost_to_close=0.70) is True

    def test_does_not_trigger_when_below_target(self, configured_env):
        supabase = FakeSupabase()
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        # cost_to_close=1.00 -> profit = 1.50 - 1.00 = 0.50 < 0.75
        position = _make_position(entry_price=1.50, profit_target=0.75)
        assert ea._check_profit_target(position, cost_to_close=1.00) is False


# ---------------------------------------------------------------------------
# Stop loss tests
# ---------------------------------------------------------------------------

class TestStopLoss:
    def test_triggers_when_loss_exceeds_stop(self, configured_env):
        supabase = FakeSupabase()
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        # entry_price=1.50, stop_loss=3.00
        # cost_to_close=5.00 -> loss = 5.00 - 1.50 = 3.50 >= 3.00
        position = _make_position(entry_price=1.50, stop_loss=3.00)
        assert ea._check_stop_loss(position, cost_to_close=5.00) is True

    def test_does_not_trigger_when_below_stop(self, configured_env):
        supabase = FakeSupabase()
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        # cost_to_close=2.00 -> loss = 2.00 - 1.50 = 0.50 < 3.00
        position = _make_position(entry_price=1.50, stop_loss=3.00)
        assert ea._check_stop_loss(position, cost_to_close=2.00) is False


# ---------------------------------------------------------------------------
# Days to expiry tests
# ---------------------------------------------------------------------------

class TestDaysToExpiry:
    def test_triggers_when_within_21_dte(self, configured_env):
        supabase = FakeSupabase()
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        exp = (datetime.utcnow() + timedelta(days=15)).strftime("%Y-%m-%d")
        position = _make_position(expiration=exp)
        assert ea._check_days_to_expiry(position) is True

    def test_does_not_trigger_when_far_from_expiry(self, configured_env):
        supabase = FakeSupabase()
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        exp = (datetime.utcnow() + timedelta(days=45)).strftime("%Y-%m-%d")
        position = _make_position(expiration=exp)
        assert ea._check_days_to_expiry(position) is False


# ---------------------------------------------------------------------------
# Build closing order tests
# ---------------------------------------------------------------------------

class TestBuildClosingOrder:
    def test_reverses_sell_to_buy(self, configured_env):
        supabase = FakeSupabase()
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        position = _make_position()
        order = ea._build_closing_order(position)
        assert order.legs[0].action == "Buy"
        assert order.request_id == "close-1"

    def test_vpc_reverses_both_legs(self, configured_env):
        supabase = FakeSupabase()
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        position = _make_vpc_position()
        order = ea._build_closing_order(position)
        assert len(order.legs) == 2
        # Short leg (Sell) becomes Buy
        assert order.legs[0].action == "Buy"
        # Long leg (Buy) becomes Sell
        assert order.legs[1].action == "Sell"


# ---------------------------------------------------------------------------
# Full evaluate_position integration
# ---------------------------------------------------------------------------

class TestEvaluatePosition:
    def test_profit_exit_triggered(self, configured_env):
        quotes = [
            {"contractid": "SPY260918P00540000", "bid": 0.30, "ask": 0.40, "mark": 0.35, "quote_date": "2026-03-06"},
        ]
        supabase = FakeSupabase(option_quotes=quotes)
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        # entry=1.50, target=0.75, cost_to_close=0.35, profit=1.15 >= 0.75
        far_exp = (datetime.utcnow() + timedelta(days=60)).strftime("%Y-%m-%d")
        position = _make_position(entry_price=1.50, profit_target=0.75, expiration=far_exp)

        should_exit, reason = asyncio.run(ea._evaluate_position(position))
        assert should_exit is True
        assert "profit" in reason.lower()

    def test_stop_loss_exit_triggered(self, configured_env):
        quotes = [
            {"contractid": "SPY260918P00540000", "bid": 4.80, "ask": 5.20, "mark": 5.00, "quote_date": "2026-03-06"},
        ]
        supabase = FakeSupabase(option_quotes=quotes)
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        # entry=1.50, stop_loss=3.00, cost_to_close=5.00, loss=3.50 >= 3.00
        far_exp = (datetime.utcnow() + timedelta(days=60)).strftime("%Y-%m-%d")
        position = _make_position(entry_price=1.50, stop_loss=3.00, expiration=far_exp)

        should_exit, reason = asyncio.run(ea._evaluate_position(position))
        assert should_exit is True
        assert "stop loss" in reason.lower()

    def test_no_exit_when_position_healthy(self, configured_env):
        quotes = [
            {"contractid": "SPY260918P00540000", "bid": 1.10, "ask": 1.30, "mark": 1.20, "quote_date": "2026-03-06"},
        ]
        supabase = FakeSupabase(option_quotes=quotes)
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        # entry=1.50, cost_to_close=1.20
        # profit=0.30 < target 0.75, loss=0 (no loss)
        far_exp = (datetime.utcnow() + timedelta(days=60)).strftime("%Y-%m-%d")
        position = _make_position(entry_price=1.50, profit_target=0.75, stop_loss=3.00, expiration=far_exp)

        should_exit, reason = asyncio.run(ea._evaluate_position(position))
        assert should_exit is False

    def test_dte_takes_priority_over_profit(self, configured_env):
        """DTE check runs first, so even profitable positions exit on 21 DTE."""
        quotes = [
            {"contractid": "SPY260918P00540000", "bid": 0.30, "ask": 0.40, "mark": 0.35, "quote_date": "2026-03-06"},
        ]
        supabase = FakeSupabase(option_quotes=quotes)
        settings = Settings()
        pm = PositionManager(supabase)
        ea = ExitAutomation(settings, supabase, pm)

        near_exp = (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%d")
        position = _make_position(expiration=near_exp)

        should_exit, reason = asyncio.run(ea._evaluate_position(position))
        assert should_exit is True
        assert "21 DTE" in reason


# ---------------------------------------------------------------------------
# Execute exit integration
# ---------------------------------------------------------------------------

class TestExecuteExit:
    def test_places_closing_order_and_updates_position(self, configured_env, monkeypatch):
        quotes = [
            {"contractid": "SPY260918P00540000", "bid": 0.30, "ask": 0.40, "mark": 0.35, "quote_date": "2026-03-06"},
        ]

        closed_positions = []

        class FakePositionMgr:
            def __init__(self, supabase):
                pass

            async def get_open_positions(self, ticker=None):
                return []

            async def close_position(self, position_id, exit_price, exit_reason, realized_pnl):
                closed_positions.append({
                    "position_id": position_id,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "realized_pnl": realized_pnl,
                })

        placed_orders = []

        class FakeTrader:
            def __init__(self, settings):
                pass

            def place_order(self, trade_request):
                placed_orders.append(trade_request)
                return {"dry_run": True}

        supabase = FakeSupabase(option_quotes=quotes)
        settings = Settings()
        pm = FakePositionMgr(supabase)
        ea = ExitAutomation(settings, supabase, pm)
        ea.trader = FakeTrader(settings)

        position = _make_position(entry_price=1.50)

        asyncio.run(ea._execute_exit(position, "50% profit target reached"))

        # Verify closing order was placed
        assert len(placed_orders) == 1
        assert placed_orders[0].legs[0].action == "Buy"  # reversed from Sell

        # Verify position was closed in DB
        assert len(closed_positions) == 1
        assert closed_positions[0]["position_id"] == 1
        assert closed_positions[0]["exit_price"] == pytest.approx(0.35)
        # P&L = (1.50 - 0.35) * 1 * 100 = 115.0
        assert closed_positions[0]["realized_pnl"] == pytest.approx(115.0)

    def test_still_closes_position_when_order_fails(self, configured_env):
        quotes = [
            {"contractid": "SPY260918P00540000", "bid": 0.30, "ask": 0.40, "mark": 0.35, "quote_date": "2026-03-06"},
        ]

        closed_positions = []

        class FakePositionMgr:
            def __init__(self, supabase):
                pass

            async def close_position(self, position_id, exit_price, exit_reason, realized_pnl):
                closed_positions.append({
                    "position_id": position_id,
                    "exit_reason": exit_reason,
                })

        class FailingTrader:
            def __init__(self, settings):
                pass

            def place_order(self, trade_request):
                return {"ok": False, "status": 400, "body": "Insufficient funds"}

        supabase = FakeSupabase(option_quotes=quotes)
        settings = Settings()
        pm = FakePositionMgr(supabase)
        ea = ExitAutomation(settings, supabase, pm)
        ea.trader = FailingTrader(settings)

        position = _make_position(entry_price=1.50)
        asyncio.run(ea._execute_exit(position, "stop loss"))

        # Position still closed in DB despite order failure
        assert len(closed_positions) == 1
        assert "order failed" in closed_positions[0]["exit_reason"]
