# Trade Automation

This folder adds an approval-based trade execution flow:

1) Pull opportunities from Supabase (`options_opportunities`).
2) Send trade approval requests to Telegram/Discord.
3) On approval, submit orders to TradeStation.

## Files

- `propose_trades.py` - creates approval requests and notifies.
- `approval_worker.py` - polls Telegram/Discord for approve/reject commands and executes trades.
- `tradestation.py` - TradeStation auth + order placement.
- `store.py` - local state file (`trade_automation/state.json`).

## Setup (.env)

Required:
```
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...  # recommended for backend automation
```

TradeStation:
```
TRADESTATION_ACCOUNT_ID=...
TRADESTATION_DRY_RUN=true  # default true; set false to execute live
TRADESTATION_ENV=SIM       # SIM or LIVE (SIM uses sim-api.tradestation.com)
TRADESTATION_ORDER_TYPE=Market
TRADESTATION_TIME_IN_FORCE=DAY
TRADESTATION_LIMIT_PRICE=
```

Optional: override order endpoint if needed
```
TRADESTATION_ORDER_URL=https://api.tradestation.com/v3/orderexecution/orders
```

Telegram approvals:
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_APPROVER_IDS=12345678,87654321
```

Discord approvals:
```
DISCORD_BOT_TOKEN=...
DISCORD_CHANNEL_ID=...
DISCORD_APPROVER_IDS=1111,2222
```

Trade filters:
```
OPPORTUNITIES_LIMIT=10
OPPORTUNITIES_MIN_RETURN_PCT=2
OPPORTUNITIES_MAX_COLLATERAL=0   # 0 disables the filter
OPPORTUNITIES_STRATEGIES=CSP,VPC
TRADE_QUANTITY=1
```

Backends to use:
```
TRADE_APPROVAL_BACKENDS=telegram,discord
```

## Usage

Create approval requests:
```
poetry run python trade_automation/propose_trades.py
```

Run approval worker (polls for /approve or /reject):
```
poetry run python trade_automation/approval_worker.py
```

## Notes

- This uses TradeStation refresh-token auth (same pattern as `data_collection/tradestation_options.py`).
- The TradeStation order payload is intentionally minimal; verify required fields in your TradeStation account.
- Default is `TRADESTATION_DRY_RUN=true` to prevent accidental execution.
- Set `TRADESTATION_ENV=SIM` to use the TradeStation simulation API host for orders.
- Approvals are stored in `trade_automation/state.json` for restartability.

## Discord setup quick steps

1) Create a bot at https://discord.com/developers/applications
2) Enable the bot and copy the token into `DISCORD_BOT_TOKEN`.
3) Invite the bot to your server with message read/send permissions.
4) Right-click the channel → Copy Channel ID → `DISCORD_CHANNEL_ID`.
5) In Discord settings, enable Developer Mode and copy your user ID(s) → `DISCORD_APPROVER_IDS`.

## Testing (Discord)

1) Export env vars and run:
```
poetry run python trade_automation/propose_trades.py
```
2) In Discord channel, reply:
```
approve <request_id>
```
or
```
reject <request_id>
```
3) Run the worker:
```
poetry run python trade_automation/approval_worker.py
```
