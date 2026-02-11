# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OptionsMagic is a Python-based stock options data collection and analysis system. It scrapes stock and options data from Finviz and TradeStation, stores it in Supabase, and generates filtered options trading opportunities (CSP and VPC strategies). Trade automation via Telegram approval is in development under `trade_automation/`.

## Common Commands

```bash
# Install dependencies
poetry install

# Update lock file after changing pyproject.toml
poetry lock

# Run the full production pipeline (3 steps with timeouts and locking)
bash run_pipeline_v2.sh

# Run individual data collection scripts
poetry run python data_collection/finviz.py                        # Step 1: Scrape stock quotes from Finviz
poetry run python data_collection/tradestation_options.py          # Step 2: Fetch options data from TradeStation API
poetry run python data_collection/generate_opportunities_simple.py # Step 3: Generate CSP/VPC opportunities

# Weekly cleanup (database + logs)
poetry run python data_collection/cleanup_old_data.py
poetry run python data_collection/cleanup_old_data.py --dry-run    # Preview what would be deleted

# One-time TradeStation OAuth setup
poetry run python data_collection/tradestation_oauth_setup.py
```

## Architecture

### Pipeline (`run_pipeline_v2.sh`)

The pipeline runs three scripts sequentially with per-step timeouts, a directory-based lock to prevent concurrent runs, and heartbeat files to track successful completions:

1. **finviz.py** (6 min timeout) - Scrapes stock quotes (price, volume, market cap, sector, RSI, SMA50, SMA200) from Finviz screener -> stores in `stock_quotes` table
2. **tradestation_options.py** (30 min timeout) - Fetches options chains with full Greeks from TradeStation API v3 -> stores in `options_quotes` table. Requires `tokens.json` for authentication.
3. **generate_opportunities_simple.py** (6 min timeout) - Joins stock and options data, filters for attractive CSP and VPC opportunities, upserts to `options_opportunities` table

### Weekly Maintenance

**cleanup_old_data.py** runs via cron on Sundays at 2 AM ET:
- Deletes database records older than 30 days from all tables
- Truncates all log files in `logs/`

### Database Tables (Supabase)

- `stock_quotes` - Daily stock price/volume data with technical indicators (RSI, SMA50, SMA200), keyed by (ticker, quote_date)
- `options_quotes` - Options contract data with Greeks from TradeStation API
- `options_opportunities` - Pre-filtered CSP and VPC opportunities

### Key Directories

- `data_collection/` - All pipeline scripts (finviz, tradestation, opportunities, cleanup)
- `trade_automation/` - Upcoming trade execution with Telegram approval (not yet wired into pipeline)
- `heartbeat/` - Timestamp files updated on successful pipeline step completion
- `locks/` - Directory-based lock to prevent concurrent pipeline runs (stale after 4 hours)
- `logs/` - Per-step log files, truncated weekly by cleanup script

## Environment Variables

Supabase (required):
- `SUPABASE_URL`, `SUPABASE_KEY`

TradeStation API credentials are read from `tokens.json`:
- `client_id`, `client_secret`, `refresh_token`

Optional (finviz.py supports local Postgres as alternate backend):
- `STORAGE_BACKEND` - "supabase" (default) or "postgres"
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

## Scheduling (Cron)

Run `scripts/setup_cron_jobs.sh` to install:
- Hourly pipeline: Mon-Fri, 9 AM - 4 PM ET
- Weekly cleanup: Sunday 2 AM ET
