# Database Schema Documentation
**Optimized for OptionsMagic Trading System**  
**Last Updated:** 2026-02-10 by Max 👨‍💻

---

## 📊 **Database: Supabase PostgreSQL**

**Retention Policy:** 30 days rolling window  
**Cleanup Schedule:** Weekly (every Sunday at 2 AM)  
**Estimated Size:** ~51MB for 30 days of data

---

## 📋 **Tables Overview**

| Table | Purpose | Records (30d) | Size Est. |
|-------|---------|---------------|-----------|
| stock_quotes | Stock price + technicals | ~2,100 | 200KB |
| options_quotes | Options contracts + Greeks | ~510,000 | 50MB |
| options_opportunities | Filtered trade opportunities | ~9,000 | 1MB |

**Total:** ~521,100 records, ~51MB

---

## 1. **stock_quotes**

**Purpose:** Daily stock price and technical indicators  
**Primary Key:** (ticker, quote_date)  
**Retention:** 30 days

### Fields Used by Trading System:
```sql
ticker           VARCHAR(20)     -- Stock symbol
quote_date       DATE           -- Date of quote
price            NUMERIC(10,2)  -- Current price (CRITICAL for trade decisions)
rsi              NUMERIC(6,2)   -- RSI indicator (strategy filter)
sma50            NUMERIC(10,2)  -- 50-day SMA (trend analysis)
sma200           NUMERIC(10,2)  -- 200-day SMA (trend analysis)
volume           BIGINT         -- Trading volume
market_cap       NUMERIC(20,2)  -- Market capitalization
sector           VARCHAR(100)   -- Stock sector
```

### Fields NOT Currently Used:
```sql
quote_time       TIME           -- Can be removed if not needed
change_percent   NUMERIC(6,2)   -- Daily change (informational only)
relative_volume  NUMERIC(5,2)   -- Relative volume (not in filters)
pe_ratio         NUMERIC(10,2)  -- P/E ratio (not in filters)
eps              NUMERIC(10,2)  -- EPS (not in filters)
dividend_yield   NUMERIC(6,2)   -- Dividend (not in filters)
industry         VARCHAR(100)   -- Industry (sector is enough)
distance_from_support NUMERIC(8,2) -- Not currently used
has_options      BOOLEAN        -- Always true (we filter for this)
last_updated     TIMESTAMP      -- Redundant with quote_date
```

**Optimization Recommendation:**
- ✅ Keep current schema for now
- Consider removing unused fields in future if storage becomes an issue

---

## 2. **options_quotes**

**Purpose:** Options contracts with full Greeks from TradeStation  
**Primary Key:** (contractid, date)  
**Retention:** 30 days

### Fields Used by Trading System:
```sql
contractid        VARCHAR(255)  -- Unique contract ID (PRIMARY KEY)
symbol            VARCHAR(255)  -- Underlying stock
date              DATE         -- Data date (PRIMARY KEY)
expiration        DATE         -- Options expiration (CRITICAL for VPC strategy)
strike            DECIMAL      -- Strike price (CRITICAL for VPC strategy)
type              VARCHAR(10)  -- "call" or "put" (filter for puts only)
bid               DECIMAL      -- Bid price (CRITICAL for premium calculation)
ask               DECIMAL      -- Ask price (CRITICAL for premium calculation)
delta             DECIMAL      -- Delta Greek (strategy filter)
theta             DECIMAL      -- Theta Greek (time decay analysis)
gamma             DECIMAL      -- Gamma Greek (risk analysis)
vega              DECIMAL      -- Vega Greek (IV sensitivity)
implied_volatility DECIMAL     -- IV (strategy filter)
open_interest     INTEGER      -- Liquidity indicator
volume            INTEGER      -- Trading activity
```

### Fields NOT Currently Used:
```sql
last              DECIMAL      -- Last trade price (bid/ask is better)
mark              DECIMAL      -- Mid price (can calculate from bid/ask)
bid_size          INTEGER      -- Bid size (not in strategy yet)
ask_size          INTEGER      -- Ask size (not in strategy yet)
rho               DECIMAL      -- Rho Greek (rarely used)
```

**Optimization Recommendation:**
- ✅ Keep all Greeks (useful for future strategy refinement)
- ✅ Keep bid/ask sizes (may be used for liquidity filtering later)
- Consider removing `last` and `mark` (redundant)

---

## 3. **options_opportunities**

**Purpose:** Pre-filtered trade opportunities (CSP + VPC strategies)  
**Primary Key:** opportunity_id (SERIAL)  
**Retention:** 30 days

### Fields Used by Trading System:
```sql
opportunity_id    SERIAL PRIMARY -- Auto-incrementing ID
ticker            VARCHAR(20)    -- Stock symbol
strategy_type     VARCHAR(10)    -- "CSP" or "VPC" (CRITICAL: filter for VPC only)
expiration_date   DATE          -- Options expiration
strike_price      NUMERIC(10,2) -- Strike price
net_credit        NUMERIC(10,2) -- Premium collected (CRITICAL for P&L)
collateral        NUMERIC(10,2) -- Required capital (CRITICAL for position sizing)
return_pct        NUMERIC(10,2) -- Return % (CRITICAL for opportunity ranking)
annualized_return NUMERIC(10,2) -- Annualized return (strategy filter)
delta             NUMERIC(6,4)  -- Delta (strategy filter)
theta             NUMERIC(6,4)  -- Theta (time decay)
last_updated      TIMESTAMP     -- When opportunity was generated
```

### Fields for VPC Strategy (Vertical Put Credit Spreads):
```sql
width             NUMERIC(10,2) -- Spread width (difference between strikes)
```

### Fields NOT Currently Used:
```sql
rsi_14            NUMERIC(6,2)  -- RSI (already filtered before opportunity generation)
iv_percentile     NUMERIC(6,2)  -- IV percentile (not yet implemented)
price_vs_bb_lower NUMERIC(6,2)  -- Bollinger Band distance (not yet implemented)
above_sma_200     BOOLEAN       -- SMA filter (already applied before)
```

**Optimization Recommendation:**
- ✅ Keep all fields (opportunities are lightweight, ~1MB for 30 days)
- Filter `strategy_type = 'VPC'` in queries (no CSPs for now)

---

## 📈 **Data Flow**

```
1. finviz.py
   └─> stock_quotes (70 stocks/day)

2. tradestation_options.py
   └─> options_quotes (~17,000 contracts/day)

3. generate_options_opportunities.py
   └─> options_opportunities (~300 opportunities/day)

4. cleanup_old_data.py (weekly)
   └─> DELETE records older than 30 days from all tables
```

---

## 🔧 **Indexes**

**stock_quotes:**
```sql
PRIMARY KEY (ticker, quote_date)
INDEX idx_stock_quotes_ticker ON stock_quotes (ticker)
INDEX idx_stock_quotes_date ON stock_quotes (quote_date)
```

**options_quotes:**
```sql
PRIMARY KEY (contractid, date)
INDEX idx_options_quotes_symbol ON options_quotes (symbol)
INDEX idx_options_quotes_date ON options_quotes (date)
INDEX idx_options_quotes_expiration ON options_quotes (expiration)
```

**options_opportunities:**
```sql
PRIMARY KEY (opportunity_id)
INDEX idx_opportunities_ticker ON options_opportunities (ticker)
INDEX idx_opportunities_strategy ON options_opportunities (strategy_type)
INDEX idx_opportunities_return ON options_opportunities (return_pct DESC)
INDEX idx_opportunities_rsi ON options_opportunities (rsi_14)
```

**Optimization Recommendation:**
- ✅ Current indexes are well-optimized for our queries
- Consider composite index: `(strategy_type, return_pct DESC)` for VPC filtering

---

## 💾 **Storage Estimates**

**Current (1 day of data):**
- Stock quotes: 70 rows ≈ 7KB
- Options quotes: 17,000 rows ≈ 1.7MB
- Opportunities: 300 rows ≈ 30KB
- **Total: ~1.74MB/day**

**30-day retention:**
- Stock quotes: 2,100 rows ≈ 200KB
- Options quotes: 510,000 rows ≈ 50MB
- Opportunities: 9,000 rows ≈ 1MB
- **Total: ~51MB**

**Supabase Free Tier:** 500MB database  
**Usage:** 51MB (10% of free tier) ✅  
**Headroom:** 449MB (88x current usage)

---

## 🧹 **Cleanup Policy**

**Script:** `data_collection/cleanup_old_data.py`  
**Frequency:** Weekly (every Sunday at 2 AM)  
**Retention:** 30 days  
**Dry-run test:** `poetry run python data_collection/cleanup_old_data.py --dry-run`  
**Execute:** `poetry run python data_collection/cleanup_old_data.py`

**Cron schedule:**
```bash
0 2 * * 0 cd /home/openclaw/.openclaw/workspace/optionsmagic && $HOME/.local/bin/poetry run python data_collection/cleanup_old_data.py >> logs/cleanup.log 2>&1
```

---

## ✅ **Optimization Status**

- ✅ 30-day retention policy implemented
- ✅ Weekly cleanup scheduled
- ✅ Schema documented
- ✅ Storage estimated (well within free tier)
- ✅ No schema changes needed
- ✅ Supabase is cost-effective for this use case

**Next review:** After 1 month of live trading data

---

**Created by:** Max 👨‍💻  
**Date:** 2026-02-10  
**Status:** Optimized ✅
