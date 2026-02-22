# Trade Automation

Approval-based trade execution flow for OptionsMagic.

## Overview

1. **Pipeline Step 4** (`propose_trades.py`) - Runs after opportunity generation
2. **Approval Worker** (`approval_worker.py`) - Background service polling for approvals
3. **Trade Execution** - On approval, submits orders to TradeStation

## Architecture

```
Pipeline:
  Step 1: finviz.py → stock_quotes
  Step 2: tradestation_options.py → options_quotes
  Step 3: generate_opportunities_simple.py → options_opportunities
  Step 4: propose_trades.py → Telegram/Discord proposals

Background Worker:
  approval_worker.py (always running)
    ↓
  Polls for button clicks/text commands
    ↓
  On APPROVE → TradeStation order
  On REJECT → Mark rejected
  On timeout (5 min) → Auto-reject
```

## Quick Start

### 1. Configure Environment

Add to `.env`:
```bash
# Telegram (for approvals)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_APPROVER_IDS=your_user_id
TRADE_APPROVAL_BACKENDS=telegram

# TradeStation (for execution)
TRADESTATION_ACCOUNT_ID=your_account_id
TRADESTATION_DRY_RUN=true  # Set to false for live trading
TRADESTATION_ENV=SIM       # SIM or LIVE
```

### 2. Start the Approval Worker

**Option A: Using the worker script**
```bash
bash trade_automation/worker.sh start
bash trade_automation/worker.sh status
bash trade_automation/worker.sh logs
```

**Option B: Using systemd**
```bash
# Copy service file
sudo cp trade_automation/optionsmagic-worker.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start and enable
sudo systemctl start optionsmagic-worker
sudo systemctl enable optionsmagic-worker
sudo systemctl status optionsmagic-worker
```

**Option C: Manual (for testing)**
```bash
poetry run python trade_automation/approval_worker.py
```

### 3. Run the Pipeline

```bash
bash run_pipeline_v2.sh
```

Step 4 will send trade proposals to your Telegram with APPROVE/REJECT buttons.

## How It Works

### Step 4: Propose Trades

Runs automatically as part of the pipeline:
- Fetches top opportunities from `options_opportunities`
- Filters by return %, collateral, strategy type
- Sends each as a Telegram message with inline buttons
- Stores request in `state.json`

### Approval Worker

Always-running background process:
- Polls Telegram every 10 seconds
- Checks for button clicks (callback queries)
- Also supports text commands: `approve {id}` / `reject {id}`
- Auto-rejects after 5 minutes

### User Interaction

**Via Telegram Buttons:**
1. Pipeline sends proposal with ✅ APPROVE / ❌ REJECT buttons
2. You click a button
3. Worker processes immediately
4. Message updates to show result

**Via Text Commands:**
```
approve abc123def456
reject abc123def456
```

### Trade Execution

On approval:
1. Worker submits order to TradeStation
2. Order status logged to `state.json`
3. Telegram message updated with result
4. If dry-run: Simulated execution (no real money)

## Files

| File | Purpose |
|------|---------|
| `propose_trades.py` | Pipeline step 4 - sends proposals |
| `approval_worker.py` | Background worker - processes approvals |
| `notifier_telegram.py` | Telegram bot integration |
| `notifier_discord.py` | Discord bot integration (optional) |
| `tradestation.py` | TradeStation API client |
| `store.py` | Local state persistence |
| `models.py` | TradeRequest/OptionLeg data classes |
| `opportunities.py` | Opportunity fetching/filtering |
| `worker.sh` | Worker process manager |
| `optionsmagic-worker.service` | systemd service file |
| `state.json` | Pending/executed trade state |

## State Management

`state.json` tracks:
```json
{
  "requests": {
    "abc123": {
      "request_id": "abc123",
      "status": "pending",
      "created_at": "2026-02-22T10:00:00",
      "telegram_message_id": 12345
    }
  },
  "telegram": {"last_update_id": 987654},
  "discord": {"last_message_id": "1234567890"}
}
```

## Safety Features

1. **Dry Run Mode** - `TRADESTATION_DRY_RUN=true` (default)
2. **Authorized Approvers Only** - Only `TELEGRAM_APPROVER_IDS` can approve
3. **5-Minute Timeout** - Auto-reject if no response
4. **SIM Environment** - Use `TRADESTATION_ENV=SIM` for paper trading

## Environment Variables

### Required
- `SUPABASE_URL`, `SUPABASE_KEY` - Database access
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` - Telegram notifications
- `TRADESTATION_ACCOUNT_ID` - TradeStation account

### Optional
- `TRADE_APPROVAL_BACKENDS` - `telegram` or `discord` or both
- `TELEGRAM_APPROVER_IDS` - Comma-separated list of allowed user IDs
- `TRADESTATION_DRY_RUN` - `true` (default) or `false`
- `TRADESTATION_ENV` - `SIM` (default) or `LIVE`
- `OPPORTUNITIES_LIMIT` - Max proposals per run (default 10)
- `OPPORTUNITIES_MIN_RETURN_PCT` - Minimum return filter
- `OPPORTUNITIES_MAX_COLLATERAL` - Maximum collateral filter
- `OPPORTUNITIES_STRATEGIES` - `CSP,VPC` or either one

## Troubleshooting

**Worker not responding:**
```bash
bash trade_automation/worker.sh restart
```

**Check logs:**
```bash
tail -f logs/approval_worker.log
tail -f logs/propose_trades.log
```

**State stuck:**
```bash
rm trade_automation/state.json  # Reset state
bash trade_automation/worker.sh restart
```

**Test Telegram connection:**
```bash
poetry run python -c "
from trade_automation.config import Settings
from trade_automation.notifier_telegram import TelegramNotifier
settings = Settings()
tg = TelegramNotifier(settings)
tg.send_message('Test message from OptionsMagic')
"
```
