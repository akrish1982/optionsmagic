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
poetry run python data_collection/finviz.py
```

- To run options program every day
```
poetry run data_collection/alphavantage.py
```
#### Future Improvements
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