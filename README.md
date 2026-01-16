### Database local
To start local postgres `brew services start postgresql`
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

- alphavantage
```
CREATE TABLE alpha_vantage_options (
    contractID VARCHAR(255),
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
    date DATE,
    implied_volatility DECIMAL,
    delta DECIMAL,
    gamma DECIMAL,
    theta DECIMAL,
    vega DECIMAL,
    rho DECIMAL,
    PRIMARY KEY (contractID, date)
);
```

- All database queries for reference
```

select * from public.stock_quotes ;

CREATE TABLE alpha_vantage_options (
    contractID VARCHAR(255),
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
    date DATE,
    implied_volatility DECIMAL,
    delta DECIMAL,
    gamma DECIMAL,
    theta DECIMAL,
    vega DECIMAL,
    rho DECIMAL,
    PRIMARY KEY (contractID, date)
);

CREATE TABLE yahoo_finance_options (
    contractID VARCHAR(255),
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
    date DATE,
    implied_volatility DECIMAL,
    delta DECIMAL,
    gamma DECIMAL,
    theta DECIMAL,
    vega DECIMAL,
    rho DECIMAL,
    PRIMARY KEY (contractID, date)
);

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
0 * * * 1-5 cd /Users/<user>/code/optionsmagic && /Users/<user>/.local/bin/poetry run python data_collection/finviz.py >> /Users/<user>/code/optionsmagic/logs/finviz.log 2>&1 && touch /Users/<user>/code/optionsmagic/heartbeat/finviz_heartbeat || echo "finviz.py failed" | mail -s "finviz.py CRON Job Failed" <your_email>@gmail.com

# yahoo_finance_options_postgres.py every weekday, hourly 9AM–4PM
2 9-16 * * 1-5 cd /Users/<user>/code/optionsmagic && /Users/<user>/.local/bin/poetry run python data_collection/yahoo_finance_options_postgres.py >> /Users/<user>/code/optionsmagic/logs/yahoo_finance.log 2>&1 && touch /Users/<user>/code/optionsmagic/heartbeat/yahoo_heartbeat || echo "yahoo_finance_options_postgres.py failed" | mail -s "Options CRON Job Failed" <your_email>@gmail.com

# update_tradeable_options.py every weekday, hourly 9AM–4PM
12 9-16 * * 1-5 cd /Users/<user>/code/optionsmagic && /Users/<user>/.local/bin/poetry run python data_collection/update_tradeable_options.py >> /Users/<user>/code/optionsmagic/logs/tradeable.log 2>&1 && touch /Users/<user>/code/optionsmagic/heartbeat/tradeable_heartbeat || echo "update_tradeable_options.py failed" | mail -s "Tradeable Options Job Failed" <your_email>@gmail.com
```

#### Running the program from command line

```
cd /Users/<user>/code/optionsmagic 
poetry run python data_collection/finviz.py >> /Users/<user>/code/optionsmagic/logs/finviz.log
poetry run python data_collection/yahoo_finance_options_postgres.py >> /Users/<user>/code/optionsmagic/logs/yahoo_finance.log
poetry run python data_collection/update_tradeable_options.py >> /Users/<user>/code/optionsmagic/logs/tradeable.log
```
how to run without logs

```
cd /Users/<user>/code/optionsmagic 
poetry run python data_collection/finviz.py
poetry run python data_collection/yahoo_finance_options_postgres.py
poetry run python data_collection/update_tradeable_options.py
```


### Supabase options query API

curl 'https://cqsbeacrzfpnukwpdvhc.supabase.co/rest/v1/tradeable_options?select=collateral&limit=10' \
-H "apikey: <secret>" \
-H "Authorization: Bearer <secret>"
=======
