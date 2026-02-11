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

The production pipeline is `run_pipeline_v2.sh`. It runs three steps sequentially with timeouts, locking, and heartbeat tracking:

| Step | Script | Timeout | Description |
|------|--------|---------|-------------|
| 1 | `data_collection/finviz.py` | 6 min | Scrape stock quotes (price, volume, RSI, SMA50, SMA200) from Finviz |
| 2 | `data_collection/tradestation_options.py` | 30 min | Fetch options chains with Greeks from TradeStation API |
| 3 | `data_collection/generate_opportunities_simple.py` | 6 min | Filter and score CSP/VPC opportunities, upsert to Supabase |

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
  run_pipeline_v2.sh              # Production pipeline (3 steps)
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
  trade_automation/               # Trade execution (in development)
  database/ddl/                   # SQL schema definitions
  scripts/                        # Cron setup helpers
  heartbeat/                      # Pipeline health tracking files
  locks/                          # Concurrency lock directory
  logs/                           # Pipeline log files (truncated weekly)
```

## Trade Automation (Upcoming)

The `trade_automation/` folder contains an approval-based trade execution system currently in development. Once complete, it will be added as a step in the pipeline after opportunity generation.

**Planned workflow:**
1. `propose_trades.py` selects the top 2-3 opportunities and sends trade proposals to Telegram for approval
2. A user reviews and approves/rejects each trade via Telegram commands
3. On approval, orders are submitted to TradeStation (simulation mode by default, with a dry-run safety flag)

**Key features:**
- Telegram integration for real-time trade approval notifications
- TradeStation order execution (SIM and LIVE environments)
- Dry-run mode enabled by default to prevent accidental trades
- Supports CSP and VPC strategies with configurable filters (min return %, max collateral)

See `trade_automation/README.md` for setup details and environment variables.
