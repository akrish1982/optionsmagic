# OptionsMagic

Python-based stock options data collection and analysis system. Scrapes stock and options data from Finviz and TradeStation, stores it in Supabase, and generates filtered options trading opportunities (CSP and VPC strategies).

## Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/)
- Supabase project with tables created (see `database/ddl/create_table.sql`)
- TradeStation API credentials in `tokens.json` (`client_id`, `client_secret`, `refresh_token`)

## Setup

```bash
poetry install
```

Create a `.env` file with:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-key
```

TradeStation auth is read from `tokens.json` at the project root:
```json
{
  "client_id": "...",
  "client_secret": "...",
  "refresh_token": "..."
}
```

## Pipeline

The production pipeline is `run_pipeline_v2.sh`. It runs four steps sequentially with timeouts, locking, and heartbeat tracking:

| Step | Script | Timeout | Description |
|------|--------|---------|-------------|
| 1 | `data_collection/finviz.py` | 6 min | Scrape stock quotes (price, volume, RSI, SMA50, SMA200) from Finviz |
| 2 | `data_collection/tradestation_options.py` | 30 min | Fetch options chains with Greeks from TradeStation API |
| 3 | `data_collection/generate_opportunities_simple.py` | 6 min | Filter and score CSP/VPC opportunities, upsert to Supabase |
| 4 | `trade_automation/propose_trades.py` | 2 min | Send trade proposals to Telegram/Discord for approval |

Run manually:
```bash
bash run_pipeline_v2.sh
```

Or run individual scripts:
```bash
poetry run python data_collection/finviz.py
poetry run python data_collection/tradestation_options.py
poetry run python data_collection/generate_opportunities_simple.py
```

## Scheduling (Cron)

Use `scripts/setup_cron_jobs.sh` to install cron jobs:

```bash
bash scripts/setup_cron_jobs.sh
```

This sets up:
- **Hourly pipeline** (Mon-Fri, 9 AM - 4 PM ET) via `run_pipeline_v2.sh`
- **Weekly cleanup** (Sunday 2 AM ET) via `data_collection/cleanup_old_data.py` - deletes database records older than 30 days and truncates log files

## Opportunity Filter Logic

```
1. Truncate  - Clears old opportunities
2. Filter    - Finds stocks with RSI 30-48, price > SMA200
3. CSP Calc  - Finds puts with delta < 0.30, calculates yield
4. VPC Calc  - Pairs puts for credit spreads, calculates yield
5. Upsert    - Inserts top 5 opportunities per ticker
```

**CSP (Cash-Secured Put):** Return % = (Bid / Strike) x 100, Collateral = Strike x 100, Filter: Delta < 0.30

**VPC (Vertical Put Credit Spread):** Net Credit = Short Bid - Long Ask, Max Risk = Width - Net Credit, Return % = (Net Credit / Max Risk) x 100

## Database Tables (Supabase)

- `stock_quotes` - Daily stock price/volume data with technical indicators, keyed by (ticker, quote_date)
- `options_quotes` - Options contract data with Greeks from TradeStation API
- `options_opportunities` - Pre-filtered CSP and VPC opportunities

## Project Structure

```
optionsmagic/
  run_pipeline_v2.sh              # Production pipeline (4 steps)
  tokens.json                     # TradeStation API credentials (gitignored)
  .env                            # Supabase credentials (gitignored)
  pyproject.toml                  # Python dependencies
  data_collection/
    finviz.py                     # Step 1: stock quote scraping
    tradestation_options.py       # Step 2: options data from TradeStation
    generate_opportunities_simple.py  # Step 3: opportunity generation
    generate_options_opportunities.py # Full opportunity generator (alternate)
    cleanup_old_data.py           # Weekly DB + log cleanup
    tradestation_oauth_setup.py   # One-time OAuth token setup
  trade_automation/               # Trade execution (Step 4)
    propose_trades.py             # Send trade proposals for approval
    approval_worker.py            # Background worker (always running)
    notifier_telegram.py          # Telegram bot integration
    notifier_discord.py           # Discord bot integration
    tradestation.py               # TradeStation order execution
    worker.sh                     # Worker process manager
    optionsmagic-worker.service   # systemd service file
  database/ddl/                   # SQL schema definitions
  scripts/                        # Cron setup helpers
  heartbeat/                      # Pipeline health tracking files
  locks/                          # Concurrency lock directory
  logs/                           # Pipeline log files (truncated weekly)
```

## Trade Automation

The `trade_automation/` folder contains an approval-based trade execution system. Step 4 of the pipeline sends trade proposals via Telegram (or Discord) with inline APPROVE/REJECT buttons.

**Workflow:**
1. Pipeline Step 4 (`propose_trades.py`) sends top opportunities to Telegram with ✅/❌ buttons
2. You review and click APPROVE or REJECT (or let auto-reject after 5 minutes)
3. `approval_worker.py` (background service) processes your response
4. On approval, orders are submitted to TradeStation (SIM by default)

**Setup:**
```bash
# 1. Configure Telegram in .env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
TELEGRAM_APPROVER_IDS=...

# 2. Start the approval worker
bash trade_automation/worker.sh start

# 3. Run pipeline (Step 4 sends proposals)
bash run_pipeline_v2.sh
```

**Key features:**
- ✅/❌ Inline buttons for instant approval/rejection
- ⏱️ 5-minute auto-reject timeout
- 📱 Telegram notifications with trade details
- 🔒 Dry-run mode by default (`TRADESTATION_DRY_RUN=true`)
- 🧪 SIM environment support (`TRADESTATION_ENV=SIM`)
- 👤 Only authorized approver IDs can interact

See `trade_automation/README.md` for full setup details.
