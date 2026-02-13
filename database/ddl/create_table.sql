
 CREATE TABLE IF NOT EXISTS stock_quotes (
    ticker VARCHAR(20) NOT NULL,
    quote_date DATE NOT NULL,
    quote_time TIME NOT NULL,
    price NUMERIC(10, 2),
    change_percent NUMERIC(6, 2),
    volume BIGINT,
    relative_volume NUMERIC(5, 2),
    market_cap NUMERIC(20, 2),
    pe_ratio NUMERIC(10, 2),
    eps NUMERIC(10, 2),
    dividend_yield NUMERIC(6, 2),
    sector VARCHAR(100),
    industry VARCHAR(100),
    has_options BOOLEAN DEFAULT TRUE,
    rsi NUMERIC(6, 2),
    sma50 NUMERIC(10, 2),
    sma200 NUMERIC(10, 2),
    distance_from_support NUMERIC(8, 2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, quote_date)
);

CREATE INDEX IF NOT EXISTS idx_stock_quotes_ticker ON stock_quotes (ticker);
CREATE INDEX IF NOT EXISTS idx_stock_quotes_date ON stock_quotes (quote_date);

CREATE TABLE IF NOT EXISTS options_quotes (                                                                                         
      contractid VARCHAR(255) NOT NULL,                                                                                               
      symbol VARCHAR(255),                                                                                                            
      expiration DATE,                                                                                                                
      strike DECIMAL,                                                                                                                 
      type VARCHAR(10),                                                                                                               
      last DECIMAL,                                                                                                                   
      mark DECIMAL,                                                                                                                   
      bid DECIMAL,                                                                                                                    
      bid_size INTEGER,                                                                                                               
      ask DECIMAL,                                                                                                                    
      ask_size INTEGER,                                                                                                               
      volume INTEGER,                                                                                                                 
      open_interest INTEGER,                                                                                                          
      quote_date DATE NOT NULL,                                                                                                             
      implied_volatility DECIMAL,                                                                                                     
      delta DECIMAL,                                                                                                                  
      gamma DECIMAL,                                                                                                                  
      theta DECIMAL,                                                                                                                  
      vega DECIMAL,                                                                                                                   
      rho DECIMAL,                                                                                                             
PRIMARY KEY (contractid, quote_date)                                                                                                  
  );                                                                                                                                  
                                                                                                                                      
  -- Create indexes for common queries                                                                                                
  CREATE INDEX IF NOT EXISTS idx_options_quotes_symbol ON options_quotes (symbol);                                                    
  CREATE INDEX IF NOT EXISTS idx_options_quotes_date ON options_quotes (quote_date);                                                        
  CREATE INDEX IF NOT EXISTS idx_options_quotes_expiration ON options_quotes (expiration);  
-- Create options_opportunities table                                                                                               
  CREATE TABLE IF NOT EXISTS options_opportunities (                                                                                  
      opportunity_id SERIAL PRIMARY KEY,                                                                                              
      ticker VARCHAR(20),                                                                                                             
      strategy_type VARCHAR(10),  -- 'CSP' or 'VPC'                                                                                   
                                                                                                                                      
      -- Option Specifics                                                                                                             
      expiration_date DATE,                                                                                                           
      strike_price NUMERIC(10, 2),                                                                                                    
      width NUMERIC(10, 2),       -- For VPCs (difference between strikes)                                                            
      net_credit NUMERIC(10, 2),  -- Premium collected                                                                                
      collateral NUMERIC(10, 2),  -- Required buying power                                                                            
      return_pct NUMERIC(10, 2),  -- (Net Credit / Collateral) * 100                                                                  
      annualized_return NUMERIC(10, 2),                                                                                     
                                                                                                                                      
      -- Technical Filters (Long Bias)                                                                                                
      rsi_14 NUMERIC(6, 2),                                                                                                           
      iv_percentile NUMERIC(6, 2),                                                                                                    
      price_vs_bb_lower NUMERIC(6, 2),  -- % distance from Lower Bollinger Band                                                       
      above_sma_200 BOOLEAN,            -- Long-only trend filter                                                                     
                                                                                                                                      
      -- Greeks                                                                                                                       
      delta NUMERIC(6, 4),                                                                                                            
      theta NUMERIC(6, 4),                                                                                                            
                                                                                                                                      
      last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP                                                                 
  );                                                                                                                                  
                                                                                                                                      
  -- Create indexes for UI queries                                                                                                    
  CREATE INDEX IF NOT EXISTS idx_opportunities_ticker ON options_opportunities (ticker);                                              
  CREATE INDEX IF NOT EXISTS idx_opportunities_strategy ON options_opportunities (strategy_type);                                     
  CREATE INDEX IF NOT EXISTS idx_opportunities_return ON options_opportunities (return_pct DESC);                                     
  CREATE INDEX IF NOT EXISTS idx_opportunities_rsi ON options_opportunities (rsi_14);   