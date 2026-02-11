-- Schema Changes for OptionsMagic
-- To be run by Ananth in Supabase SQL Editor
-- Date: 2026-02-11
-- Updated: Added stock_price and trade_score columns

-- 1. Rename column: options_quotes.date → quote_date
-- Reason: Consistency with stock_quotes.quote_date
ALTER TABLE options_quotes RENAME COLUMN date TO quote_date;

-- 2. Add stock_price column to options_opportunities
-- Reason: Display stock price in dashboard header (e.g., "CAT $327.45")
ALTER TABLE options_opportunities ADD COLUMN IF NOT EXISTS stock_price NUMERIC;

-- 3. Add trade_score column to options_opportunities
-- Reason: Letter grade (A+ to F) for trade quality
ALTER TABLE options_opportunities ADD COLUMN IF NOT EXISTS trade_score VARCHAR(2);

-- 4. Add composite index on options_opportunities
-- Reason: Optimize VPC filtering queries (strategy_type + return_pct DESC)
CREATE INDEX IF NOT EXISTS idx_opportunities_strategy_return 
ON options_opportunities (strategy_type, return_pct DESC);

-- 5. Add index on ticker for grouping queries
CREATE INDEX IF NOT EXISTS idx_opportunities_ticker 
ON options_opportunities (ticker);

-- Verify changes:
-- \d options_quotes (check column name)
-- \d options_opportunities (check new columns and indexes)
