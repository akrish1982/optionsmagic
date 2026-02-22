-- Positions Table: Track all open and closed positions
CREATE TABLE IF NOT EXISTS positions (
    position_id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) UNIQUE,  -- Link back to trade request
    ticker VARCHAR(20) NOT NULL,
    strategy_type VARCHAR(10),       -- 'CSP' or 'VPC'
    status VARCHAR(20) DEFAULT 'OPEN',  -- OPEN, CLOSED, EXPIRED
    
    -- Entry Details
    entry_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    entry_price NUMERIC(10, 2),      -- Average execution price
    quantity INTEGER,
    
    -- Exit Details
    exit_date TIMESTAMP WITH TIME ZONE,
    exit_price NUMERIC(10, 2),       -- Average exit price
    exit_reason VARCHAR(50),          -- 'profit_target', 'stop_loss', '21dte', 'manual', 'expired'
    
    -- P&L Tracking
    unrealized_pnl NUMERIC(10, 2),
    realized_pnl NUMERIC(10, 2),
    pnl_percent NUMERIC(10, 2),      -- (Realized P&L / Collateral) * 100
    
    -- Position Details
    stop_loss NUMERIC(10, 2),         -- Stop loss price or % of credit for spreads
    profit_target NUMERIC(10, 2),     -- 50% profit target
    days_held INTEGER,
    
    -- Legs (stored as JSON for flexibility)
    legs JSONB,                        -- [{"contractid": "...", "action": "Sell", "qty": 1, ...}]
    
    -- Metadata
    tradestation_position_id VARCHAR(255),
    notes TEXT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions (ticker);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions (status);
CREATE INDEX IF NOT EXISTS idx_positions_entry_date ON positions (entry_date);
CREATE INDEX IF NOT EXISTS idx_positions_request_id ON positions (request_id);

-- Trade History Table: Log all executed trades
CREATE TABLE IF NOT EXISTS trade_history (
    trade_id SERIAL PRIMARY KEY,
    request_id VARCHAR(255),          -- Link to original trade request
    position_id INTEGER REFERENCES positions (position_id),
    
    -- Trade Identification
    ticker VARCHAR(20) NOT NULL,
    strategy_type VARCHAR(10),        -- 'CSP' or 'VPC'
    
    -- Execution Details
    entry_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    entry_price NUMERIC(10, 2),
    quantity INTEGER,
    
    -- Exit Details
    exit_date TIMESTAMP WITH TIME ZONE,
    exit_price NUMERIC(10, 2),
    
    -- P&L Results
    pnl_realized NUMERIC(10, 2),      -- Actual profit/loss
    pnl_percent NUMERIC(10, 2),       -- P&L as % of collateral
    win_loss VARCHAR(10),             -- 'WIN' or 'LOSS'
    
    -- Trade Attributes
    collateral_required NUMERIC(10, 2),
    max_risk NUMERIC(10, 2),
    target_return NUMERIC(10, 2),
    
    -- Metadata
    status VARCHAR(20),               -- 'OPEN', 'CLOSED', 'EXPIRED'
    executed_by VARCHAR(20),          -- 'auto' or 'manual'
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_trade_history_ticker ON trade_history (ticker);
CREATE INDEX IF NOT EXISTS idx_trade_history_entry_date ON trade_history (entry_date);
CREATE INDEX IF NOT EXISTS idx_trade_history_status ON trade_history (status);
CREATE INDEX IF NOT EXISTS idx_trade_history_win_loss ON trade_history (win_loss);

-- Create a view for daily P&L summaries
CREATE OR REPLACE VIEW v_daily_pnl AS
SELECT 
    DATE(entry_date) as trade_date,
    ticker,
    COUNT(*) as trades_count,
    SUM(CASE WHEN win_loss = 'WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN win_loss = 'LOSS' THEN 1 ELSE 0 END) as losses,
    ROUND(100.0 * SUM(CASE WHEN win_loss = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
    SUM(pnl_realized) as total_pnl,
    AVG(pnl_realized) as avg_pnl,
    SUM(CASE WHEN pnl_realized > 0 THEN pnl_realized ELSE 0 END) as total_wins,
    SUM(CASE WHEN pnl_realized < 0 THEN pnl_realized ELSE 0 END) as total_losses
FROM trade_history
WHERE status IN ('CLOSED', 'EXPIRED')
GROUP BY DATE(entry_date), ticker
ORDER BY DATE(entry_date) DESC;

-- Create a view for overall performance metrics
CREATE OR REPLACE VIEW v_performance_metrics AS
SELECT 
    COUNT(*) as total_trades,
    SUM(CASE WHEN win_loss = 'WIN' THEN 1 ELSE 0 END) as total_wins,
    SUM(CASE WHEN win_loss = 'LOSS' THEN 1 ELSE 0 END) as total_losses,
    ROUND(100.0 * SUM(CASE WHEN win_loss = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
    SUM(pnl_realized) as total_pnl,
    ROUND(AVG(pnl_realized), 2) as avg_pnl_per_trade,
    ROUND(MIN(pnl_realized), 2) as max_loss,
    ROUND(MAX(pnl_realized), 2) as max_win,
    ROUND(STDDEV(pnl_realized), 2) as pnl_stddev
FROM trade_history
WHERE status IN ('CLOSED', 'EXPIRED');
