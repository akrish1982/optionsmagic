# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OptionsMagic is a Python-based stock options data collection and analysis system. It scrapes stock and options data from multiple sources (Finviz, TradeStation), stores it in Supabase/PostgreSQL, and provides a Cloudflare Worker API for accessing filtered options trading opportunities. It is starting trade automation on a trial basis to try buys option chains on Tradestation account.

## Common Commands

```bash
# Install dependencies
poetry install

# Update lock file after changing pyproject.toml
poetry lock

# Run data collection scripts
poetry run python data_collection/finviz.py                      # Scrape stock quotes from Finviz
poetry run python data_collection/yahoo_finance_options_postgres.py  # Fetch options data from Yahoo Finance
poetry run python data_collection/tradestation_api_access.py     # Fetch options data from TradeStation API (alternative)
poetry run python data_collection/update_tradeable_options.py    # Generate tradeable_options summary table

# Start local PostgreSQL
sudo brew services start postgresql
```

## Architecture

### Data Flow
1. **finviz.py** - Scrapes stock quotes (price, volume, market cap, sector, RSI, SMA50, SMA200) for stocks with options from Finviz screener → stores in `stock_quotes` table (Supabase by default, local PostgreSQL optional)
2. **tradestation_options.py** - Fetches options chains (calls/puts for next 8 weeks) from tradestation Finance for all tickers in `stock_quotes` → stores in `tradestation_options` table.
2b. **tradestation_api_access.py** - Alternative to Yahoo Finance. Fetches options data with full Greeks from TradeStation API v3 → stores in `tradestation_options` table. Requires TradeStation API credentials.
3. **update_tradeable_options.py** - Joins stock and options data, filters for attractive put options (strike < price, return > 2%), and populates `tradeable_options` summary table
4. **api/worker.js** - Cloudflare Worker that reads from Supabase (mirrored from local Postgres) and exposes `/api/options` and `/api/expirations` endpoints

### Database Tables (PostgreSQL/Supabase)
- `stock_quotes` - Daily stock price/volume data with technical indicators (RSI, SMA50, SMA200, distance_from_support), keyed by (ticker, quote_date)
- `tradestation_options` - Options contract data with Greeks from TradeStation API, keyed by (contractID, date)
- `tradeable_options` - Pre-filtered put options for trading, keyed by contractid


## Environment Variables

Storage backend selection:
- `STORAGE_BACKEND` - "supabase" (default) or "postgres"

Supabase configuration (default backend):
- `SUPABASE_URL`, `SUPABASE_KEY`

Local PostgreSQL configuration (when `STORAGE_BACKEND=postgres`):
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

TradeStation API (for tradestation_api_access.py):
- `TRADESTATION_CLIENT_ID`, `TRADESTATION_CLIENT_SECRET`, `TRADESTATION_REFRESH_TOKEN`
- Or use `tokens.json` file with `client_id`, `client_secret`, `refresh_token`

To use local PostgreSQL instead of Supabase:
```bash
export STORAGE_BACKEND=postgres
```

## Scheduling (Cron)

The scripts are designed to run on weekdays during market hours via cron:
- `finviz.py` - hourly on weekdays
- `yahoo_finance_options_postgres.py` - hourly 9AM-4PM ET on weekdays
- `update_tradeable_options.py` - hourly 9AM-4PM ET on weekdays (runs after yahoo script)
