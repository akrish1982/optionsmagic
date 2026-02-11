-- Schema Changes for OptionsMagic
-- To be run by Ananth in Supabase SQL Editor
-- Date: 2026-02-11

-- 1. Rename column: options_quotes.date → quote_date
-- Reason: Consistency with stock_quotes.quote_date
ALTER TABLE options_quotes RENAME COLUMN date TO quote_date;

-- 2. Add composite index on options_opportunities
-- Reason: Optimize VPC filtering queries (strategy_type + return_pct DESC)
CREATE INDEX IF NOT EXISTS idx_opportunities_strategy_return 
ON options_opportunities (strategy_type, return_pct DESC);

-- Verify changes:
-- \d options_quotes (check column name)
-- \d options_opportunities (check indexes)
