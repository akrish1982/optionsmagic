import asyncio
from datetime import datetime, timedelta

import pytest

from trade_automation import approval_worker, propose_trades, store
from trade_automation.config import Settings
from trade_automation.models import OptionLeg, TradeRequest
from trade_automation.opportunities import OpportunitiesFetcher


@pytest.fixture
def configured_env(monkeypatch, tmp_path):
    env = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_KEY": "test-key",
        "TRADESTATION_ACCOUNT_ID": "SIM-123",
        "TRADESTATION_DRY_RUN": "true",
        "TRADESTATION_ENV": "SIM",
        "TRADE_APPROVAL_BACKENDS": "telegram",
        "TELEGRAM_BOT_TOKEN": "token",
        "TELEGRAM_CHAT_ID": "chat-id",
        "TELEGRAM_APPROVER_IDS": "42",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    state_path = tmp_path / "state.json"
    monkeypatch.setattr(store, "STATE_PATH", str(state_path))
    return state_path


def _sample_trade(request_id: str = "req-123") -> TradeRequest:
    return TradeRequest(
        request_id=request_id,
        strategy_type="CSP",
        ticker="SPY",
        expiration_date="2026-06-19",
        strike_price=540.0,
        width=None,
        net_credit=1.5,
        collateral=54000.0,
        return_pct=0.28,
        quantity=1,
        legs=[
            OptionLeg(
                contractid="SPY260619P00540000",
                action="Sell",
                quantity=1,
                option_type="put",
                strike=540.0,
                expiration="2026-06-19",
            )
        ],
        source_opportunity_id=1,
    )


class FakeProposalTelegram:
    def __init__(self, settings):
        self.settings = settings
        self.proposals = []

    def is_configured(self):
        return True

    def send_trade_proposal_with_buttons(self, **kwargs):
        self.proposals.append(kwargs)
        return {"message_id": 9001}


class FakeWorkerTelegram:
    def __init__(self, request_id, message_id):
        self.request_id = request_id
        self.message_id = message_id
        self.sent_messages = []
        self.callback_answers = []
        self.edited_messages = []

    def get_callback_queries(self, offset):
        return [
            {
                "update_id": 100,
                "callback_query": {
                    "id": "cb-1",
                    "from": {"id": 42},
                    "data": f"approve:{self.request_id}",
                    "message": {"message_id": self.message_id},
                },
            }
        ]

    def parse_callback_queries(self, updates):
        return [
            {
                "action": "approve",
                "request_id": self.request_id,
                "source": "telegram",
                "callback_query_id": "cb-1",
                "message_id": self.message_id,
            }
        ]

    def get_updates(self, offset):
        return []

    def parse_commands(self, updates):
        return []

    def send_message(self, text):
        self.sent_messages.append(text)
        return {"message_id": self.message_id}

    def answer_callback_query(self, callback_query_id, text=None):
        self.callback_answers.append((callback_query_id, text))
        return True

    def edit_message_text(self, message_id, text, reply_markup=None):
        self.edited_messages.append((message_id, text, reply_markup))
        return True


class FakeDiscord:
    def get_messages(self):
        return []

    def parse_commands(self, messages, last_message_id):
        return []


def test_end_to_end_propose_then_approve_executes_trade(monkeypatch, configured_env):
    trade = _sample_trade()

    monkeypatch.setattr(propose_trades, "get_supabase_client", lambda settings: object())
    monkeypatch.setattr(
        propose_trades,
        "fetch_opportunities",
        lambda settings: [
            {
                "opportunity_id": 1,
                "ticker": "SPY",
                "strategy_type": "CSP",
                "expiration_date": "2026-06-19",
                "strike_price": 540.0,
                "return_pct": 0.28,
                "collateral": 54000.0,
            }
        ],
    )
    monkeypatch.setattr(propose_trades, "filter_opportunities", lambda opps, settings: opps)
    monkeypatch.setattr(propose_trades, "build_trade_request", lambda opp, supabase, settings: trade)
    monkeypatch.setattr(propose_trades, "TelegramNotifier", FakeProposalTelegram)
    monkeypatch.setattr(propose_trades, "DiscordNotifier", lambda settings: FakeDiscord())

    propose_trades.main()
    state = store.load_state()
    assert state["requests"][trade.request_id]["status"] == "pending"
    assert state["requests"][trade.request_id]["telegram_message_id"] == 9001

    class FakeTrader:
        def __init__(self, settings):
            self.settings = settings

        def place_order(self, trade_request):
            return {"dry_run": True, "execution_price": 1.42}

    class FakePositionManager:
        def __init__(self, supabase_client):
            self.supabase_client = supabase_client

        async def create_position(self, request, entry_price, quantity, execution_data):
            return {"position_id": 77}

    monkeypatch.setattr(approval_worker, "get_supabase_client", lambda settings: object())
    monkeypatch.setattr(approval_worker, "TradeStationTradingClient", FakeTrader)
    monkeypatch.setattr(approval_worker, "PositionManager", FakePositionManager)

    worker_state = store.load_state()
    worker_telegram = FakeWorkerTelegram(trade.request_id, 9001)
    settings = Settings()
    approval_worker.run_once(settings, worker_state, worker_telegram, FakeDiscord())

    assert worker_state["requests"][trade.request_id]["status"] == "executed"
    assert worker_telegram.callback_answers
    assert any("Executed" in msg for msg in worker_telegram.sent_messages)
    assert any("Position ID: 77" in msg for msg in worker_telegram.sent_messages)
    assert worker_telegram.edited_messages


def test_auto_reject_marks_expired_requests(monkeypatch, configured_env):
    old_time = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
    state = {
        "requests": {
            "req-old": {
                "request_id": "req-old",
                "status": "pending",
                "created_at": old_time,
            }
        }
    }

    class Notifier:
        def __init__(self):
            self.messages = []

        def send_message(self, text):
            self.messages.append(text)

    notifier = Notifier()
    approval_worker.check_and_expire_requests(state, notifier)

    req = state["requests"]["req-old"]
    assert req["status"] == "rejected"
    assert "timeout" in req["notes"].lower()
    assert any("auto-rejected" in msg for msg in notifier.messages)


def test_opportunities_fetcher_applies_filters(monkeypatch, configured_env):
    class Query:
        def __init__(self, data):
            self._data = data
            self._limit = len(data)

        def select(self, _fields):
            return self

        def order(self, _field, desc=False):
            return self

        def limit(self, value):
            self._limit = value
            return self

        def execute(self):
            class Response:
                def __init__(self, data):
                    self.data = data

            return Response(self._data[: self._limit])

    class SupabaseStub:
        def __init__(self, data):
            self._data = data

        def table(self, _name):
            return Query(self._data)

    settings = Settings()
    raw = [
        {"ticker": "SPY", "strategy_type": "CSP", "return_pct": 0.25, "collateral": 2000},
        {"ticker": "QQQ", "strategy_type": "VPC", "return_pct": 0.35, "collateral": 2200},
        {"ticker": "IWM", "strategy_type": "CSP", "return_pct": 0.05, "collateral": 7000},
    ]

    fetcher = OpportunitiesFetcher(settings, SupabaseStub(raw))
    result = asyncio.run(
        fetcher.fetch_opportunities(
            limit=10,
            min_return_pct=0.1,
            max_collateral=5000,
            strategy_types=["CSP"],
        )
    )

    assert [item["ticker"] for item in result] == ["SPY"]
