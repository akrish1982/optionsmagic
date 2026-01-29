### Database local
To start local postgres `sudo brew services start postgresql`
- to use UI:
```
SELECT strike * 100 as collateral, bid*100 as income, bid/strike*100 as return_pct,contractid, 
symbol, expiration, strike, type, last, mark, bid, bid_size, ask, ask_size, opt.volume, open_interest, 
date, implied_volatility, delta, gamma, theta, vega, rho
	FROM public.alpha_vantage_options opt
	left join public.stock_quotes stcks on opt.symbol = stcks.ticker
	where date = (
		select max(date)  FROM public.alpha_vantage_options
	)
	and stcks.quote_date = (select max(quote_date)  FROM public.stock_quotes)
	-- and symbol = 'NVDA' 
	and type = 'put'
	and expiration = '2025-04-17'
	and delta <= -0.3
	and strike <= stcks.price
	order by return_pct desc
	;
```
- here are some other useful SQLs
```
select * from public.stock_quotes ;

select max(date) from public.alpha_vantage_options;

select distinct stcks.ticker from public.stock_quotes stcks
where stcks.ticker not in (select distinct opt.symbol from public.alpha_vantage_options opt where date = '2025-03-14')
```

### Application code

- to schedule to run every 15 minutes
```
/Users/<user>/.local/bin/poetry run python data_collection/finviz.py
```

- To run options program every day
```
/Users/<user>/.local/bin/poetry run python data_collection/yahoo_finance_options_postgres.py

```

- To run summarized data every day/hour
```
/Users/<user>/.local/bin/poetry run python data_collection/update_tradeable_options.py

```
- If python packages are not installed or need to be reloaded, use `poetry install`. if you changed pytoml, use `poetry lock`

#### Future Improvements
- schedule to run this locally every 15 minutes and email me if it fails
	- set up email using `security add-generic-password -a <your_email>@gmail.com -s smtp.gmail.com -w 'your_email_password'`
- connect locally to finviz and yahoo options database and update supabase only for tradeable_options

- Alphavantage fails after 25 stocks. To go away from it, i may create 2 id's and use 50 stocks at a time
- create alternate from Yahoo finance scraping, but this seems to miss the delta, rho theta and one other field, but this code has been gathered but not tested
    - bid_size and ask_size are not provided
    - Greeks (delta, gamma, theta, vega, rho) are not provided
- create alternate from CBOE options data - https://www.cboe.com/delayed_quotes/tsla/quote_table - need to build a scraper, but this will have delta and gamma in addition to yahoo finance data.
    - bid_size and ask_size: Not provided in CBOE data
    - mark: Not directly provided, but can be calculated as average of bid and ask
    - theta, vega, and rho: Still missing from the Greeks
- other options
    - https://www.reddit.com/r/options/wiki/faq/pages/data_sources/

#### Database objects


- All database queries for reference
```

select * from public.stock_quotes ;

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
      date DATE NOT NULL,                                                                                                             
      implied_volatility DECIMAL,                                                                                                     
      delta DECIMAL,                                                                                                                  
      gamma DECIMAL,                                                                                                                  
      theta DECIMAL,                                                                                                                  
      vega DECIMAL,                                                                                                                   
      rho DECIMAL,                                                                                                             
PRIMARY KEY (contractid, date)                                                                                                  
  );                                                                                                                                  
                                                                                                                                      
  -- Create indexes for common queries                                                                                                
  CREATE INDEX IF NOT EXISTS idx_options_quotes_symbol ON options_quotes (symbol);                                                    
  CREATE INDEX IF NOT EXISTS idx_options_quotes_date ON options_quotes (date);                                                        
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
      return_pct TYPE NUMERIC(10, 2),  -- (Net Credit / Collateral) * 100                                                                  
      annualized_return TYPE NUMERIC(10, 2)                                                                                     
                                                                                                                                      
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

-- allow anyone (anon + authenticated) to read rows
create policy "public read options_opportunities"
on public.options_opportunities
for select
to anon, authenticated
using (true);


SELECT strike * 100 as collateral, bid*100 as income, bid/strike*100 as return_pct,contractid, 
symbol, expiration, strike, type, last, mark, bid, bid_size, ask, ask_size, opt.volume, open_interest, 
date, implied_volatility, delta, gamma, theta, vega, rho
	FROM public.alpha_vantage_options opt
	left join public.stock_quotes stcks on opt.symbol = stcks.ticker
	where date = (
		select max(date)  FROM public.alpha_vantage_options
	)
	and stcks.quote_date = (select max(quote_date)  FROM public.stock_quotes)
	-- and symbol = 'NVDA' 
	and type = 'put'
	and expiration = '2025-04-17'
	and delta >= -0.3
	and strike <= stcks.price
	order by return_pct desc
	;
select * from  public.yahoo_finance_options opt;

SELECT strike * 100 as collateral, bid*100 as income, bid/strike*100 as return_pct,contractid, 
symbol, expiration, strike, type, last, mark, bid, bid_size, ask, ask_size, opt.volume, open_interest, 
date, implied_volatility, delta, gamma, theta, vega, rho
	FROM public.yahoo_finance_options opt
	left join public.stock_quotes stcks on opt.symbol = stcks.ticker
	where date = (
		select max(date)  FROM public.yahoo_finance_options
	)
	and stcks.quote_date = (select max(quote_date)  FROM public.stock_quotes)
	-- and symbol = 'NVDA' 
	and type = 'put'
	and expiration = '2025-04-11'
	--and delta >= -0.3
	and strike <= stcks.price
	order by return_pct desc
	;



```


#### Scheduling the crons
```
# finviz.py every hour on weekdays (Mon–Fri)
0 9-16 * * 1-5 cd /Users/<user>/code/optionsmagic && /Users/<user>/.local/bin/poetry run python data_collection/finviz.py >> /Users/<user>/code/optionsmagic/logs/finviz.log 2>&1 && touch /Users/<user>/code/optionsmagic/heartbeat/finviz_heartbeat || echo "finviz.py failed" | mail -s "finviz.py CRON Job Failed" <your_email>@gmail.com

# tradestation_options.py every weekday, hourly 9AM–4PM
2 9-16 * * 1-5 cd /Users/<user>/code/optionsmagic && /Users/<user>/.local/bin/poetry run python data_collection/tradestation_options.py >> /Users/<user>/code/optionsmagic/logs/yahoo_finance.log 2>&1 && touch /Users/<user>/code/optionsmagic/heartbeat/yahoo_heartbeat || echo "tradestation_options.py failed" | mail -s "Options CRON Job Failed" <your_email>@gmail.com

# update_tradeable_options.py every weekday, hourly 9AM–4PM
12 9-16 * * 1-5 cd /Users/<user>/code/optionsmagic && /Users/<user>/.local/bin/poetry run python data_collection/update_tradeable_options.py >> /Users/<user>/code/optionsmagic/logs/tradeable.log 2>&1 && touch /Users/<user>/code/optionsmagic/heartbeat/tradeable_heartbeat || echo "update_tradeable_options.py failed" | mail -s "Tradeable Options Job Failed" <your_email>@gmail.com
```

#### Running the program from command line

```
cd /Users/<user>/code/optionsmagic 
poetry run python data_collection/finviz.py >> /Users/<user>/code/optionsmagic/logs/finviz.log
poetry run python data_collection/tradestation_options.py  >> /Users/<user>/code/optionsmagic/logs/tradestation_options.log
poetry run python data_collection/generate_options_opportunities.py >> /Users/<user>/code/optionsmagic/logs/tradeable.log
```
how to run without logs

```
cd /Users/<user>/code/optionsmagic 
poetry run python data_collection/finviz.py
poetry run python data_collection/tradestation_options.py
poetry run python data_collection/generate_options_opportunities.py   
```
### Logic for filter
What it does:                                                                                                                       
  ┌─────────────┬─────────────────────────────────────────────────┐                                                                   
  │    Step     │                     Action                      │                                                                   
  ├─────────────┼─────────────────────────────────────────────────┤                                                                   
  │ 1. Truncate │ Clears old opportunities                        │                                                                   
  ├─────────────┼─────────────────────────────────────────────────┤                                                                   
  │ 2. Filter   │ Finds stocks with RSI 30-48, price > SMA200     │                                                                   
  ├─────────────┼─────────────────────────────────────────────────┤                                                                   
  │ 3. CSP Calc │ Finds puts with delta < 0.30, calculates yield  │                                                                   
  ├─────────────┼─────────────────────────────────────────────────┤                                                                   
  │ 4. VPC Calc │ Pairs puts for credit spreads, calculates yield │                                                                   
  ├─────────────┼─────────────────────────────────────────────────┤                                                                   
  │ 5. Upsert   │ Inserts top 5 opportunities per ticker          │                                                                   
  └─────────────┴─────────────────────────────────────────────────┘                                                                   
  Strategy Logic:                                                                                                                     
                                                                                                                                      
  CSP (Cash-Secured Put):                                                                                                             
  - Return % = (Bid / Strike) × 100                                                                                                   
  - Collateral = Strike × 100                                                                                                         
  - Filter: Delta < 0.30                                                                                                              
                                                                                                                                      
  VPC (Vertical Put Credit Spread):                                                                                                   
  - Net Credit = Short Bid - Long Ask                                                                                                 
  - Max Risk = Width - Net Credit                                                                                                     
  - Return % = (Net Credit / Max Risk) × 100   

### Supabase options query API

curl 'https://xxxxxxxx.supabase.co/rest/v1/tradeable_options?select=collateral&limit=10' \
-H "apikey: <secret>" \
-H "Authorization: Bearer <secret>"
=======
