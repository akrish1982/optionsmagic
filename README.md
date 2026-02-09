### Database local
To start local postgres `sudo brew services start postgresql`

### Application code

- to schedule to run every 15 minutes - Monday to Friday alone
```
/Users/<user>/.local/bin/poetry run python data_collection/finviz.py
```

- To run options program every day
```
/Users/<user>/.local/bin/poetry run python data_collection/tradestation_options.py

```

- To run summarized data every day/hour
```
/Users/<user>/.local/bin/poetry run python data_collection/update_tradeable_options.py

```
- If python packages are not installed or need to be reloaded, use `poetry install`. if you changed pytoml, use `poetry lock`

#### Future Improvements
- schedule to run this locally every 15 minutes and email me if it fails
	- set up email using `security add-generic-password -a <your_email>@gmail.com -s smtp.gmail.com -w 'your_email_password'`
- connect locally to finviz and tradestation options database and update supabase only for tradeable_options
- create alternate from CBOE options data - https://www.cboe.com/delayed_quotes/tsla/quote_table - need to build a scraper, but this will have delta and gamma in addition to tradestation finance data.
    - bid_size and ask_size: Not provided in CBOE data
    - mark: Not directly provided, but can be calculated as average of bid and ask
    - theta, vega, and rho: Still missing from the Greeks
- other options
    - https://www.reddit.com/r/options/wiki/faq/pages/data_sources/

#### Database objects


- All database queries for reference
```

select * from public.stock_quotes ;
  

-- allow anyone (anon + authenticated) to read rows
create policy "public read options_opportunities"
on public.options_opportunities
for select
to anon, authenticated
using (true);




```


#### Scheduling the crons
```
# finviz.py every hour on weekdays (Mon–Fri)
0 9-16 * * 1-5 cd /Users/<user>/code/optionsmagic && /Users/<user>/.local/bin/poetry run python data_collection/finviz.py >> /Users/<user>/code/optionsmagic/logs/finviz.log 2>&1 && touch /Users/<user>/code/optionsmagic/heartbeat/finviz_heartbeat || echo "finviz.py failed" | mail -s "finviz.py CRON Job Failed" <your_email>@gmail.com

# tradestation_options.py every weekday, hourly 9AM–4PM
2 9-16 * * 1-5 cd /Users/<user>/code/optionsmagic && /Users/<user>/.local/bin/poetry run python data_collection/tradestation_options.py >> /Users/<user>/code/optionsmagic/logs/tradestation_options.log 2>&1 && touch /Users/<user>/code/optionsmagic/heartbeat/tradestation_options || echo "tradestation_options.py failed" | mail -s "Options CRON Job Failed" <your_email>@gmail.com

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
