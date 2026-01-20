# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OptionsMagic is a Python-based stock options data collection and analysis system. It scrapes stock and options data from multiple sources (Finviz, Yahoo Finance), stores it in PostgreSQL, and provides a Cloudflare Worker API for accessing filtered options trading opportunities.

## Common Commands

```bash
# Install dependencies
poetry install

# Update lock file after changing pyproject.toml
poetry lock

# Run data collection scripts
poetry run python data_collection/finviz.py                      # Scrape stock quotes from Finviz
poetry run python data_collection/yahoo_finance_options_postgres.py  # Fetch options data from Yahoo Finance
poetry run python data_collection/update_tradeable_options.py    # Generate tradeable_options summary table

# Start local PostgreSQL
brew services start postgresql
```

## Architecture

### Data Flow
1. **finviz.py** - Scrapes stock quotes (price, volume, market cap, sector) for stocks with options from Finviz screener → stores in `stock_quotes` table
2. **yahoo_finance_options_postgres.py** - Fetches options chains (calls/puts for next 8 weeks) from Yahoo Finance for all tickers in `stock_quotes` → stores in `yahoo_finance_options` table. Uses `calculate_option_greeks.py` to compute delta via Black-Scholes since Yahoo doesn't provide Greeks.
3. **update_tradeable_options.py** - Joins stock and options data, filters for attractive put options (strike < price, return > 2%), and populates `tradeable_options` summary table
4. **api/worker.js** - Cloudflare Worker that reads from Supabase (mirrored from local Postgres) and exposes `/api/options` and `/api/expirations` endpoints

### Database Tables (PostgreSQL)
- `stock_quotes` - Daily stock price/volume data, keyed by (ticker, quote_date)
- `yahoo_finance_options` - Options contract data with Greeks, keyed by (contractID, date)
- `tradeable_options` - Pre-filtered put options for trading, keyed by contractid

### Key Module: calculate_option_greeks.py
Implements Black-Scholes delta calculation since Yahoo Finance doesn't provide Greeks. Used by `yahoo_finance_options_postgres.py` to enrich options data.

## Environment Variables

Database connection configured via `.env` file:
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

Cloudflare Worker uses:
- `SUPABASE_URL`, `SUPABASE_KEY`

## Scheduling (Cron)

The scripts are designed to run on weekdays during market hours via cron:
- `finviz.py` - hourly on weekdays
- `yahoo_finance_options_postgres.py` - hourly 9AM-4PM ET on weekdays
- `update_tradeable_options.py` - hourly 9AM-4PM ET on weekdays (runs after yahoo script)
