import os
import re
import datetime
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlparse, parse_qs
from dateutil import parser as date_parser
import pytz
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
# Database configuration - set these as environment variables in your production environment
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "ananth")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")

db_params = {
    'host': DB_HOST,
    'database': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD
}


def generate_yahoo_options_urls(ticker):
    """
    Generates a list of Yahoo Finance options URLs for the next 8 Fridays.

    Args:
        ticker (str): The stock ticker symbol (e.g., "NVDA").

    Returns:
        tuple: A tuple containing (list of URLs, list of expiration dates).
    """
    urls, expiration_dates = [], []
    today = datetime.date.today()
    friday_count = 0
    
    # Yahoo uses timestamps for 8:00 PM ET the day BEFORE expiration
    eastern = pytz.timezone('US/Eastern')

    for i in range(365):  # Check for Fridays within a year
        current_date = today + datetime.timedelta(days=i)
        if current_date.weekday() == 4:  # Friday is weekday 4
            # Get the day before expiration
            day_before = current_date - datetime.timedelta(days=1)
            
            # Create datetime at 20:00 (8:00 PM) Eastern Time for day before expiration
            market_timestamp = eastern.localize(
                datetime.datetime.combine(day_before, datetime.time(20, 0, 0))
            )
            
            # Convert to Unix timestamp (seconds since epoch)
            unix_timestamp = int(market_timestamp.timestamp())
            
            urls.append(f"https://finance.yahoo.com/quote/{ticker}/options/?date={unix_timestamp}")
            expiration_dates.append(current_date.strftime("%Y-%m-%d"))
            friday_count += 1
            if friday_count == 8:
                break
                
    return urls, expiration_dates


def get_options_table_from_url(url):
    """
    Fetches the HTML content from a Yahoo Finance options URL and extracts the options table.

    Args:
        url (str): The Yahoo Finance options URL.

    Returns:
        str or None: The HTML content of the options table as a string, or None if an error occurs.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')
        options_table_section = soup.find('section', {'data-testid': 'options-list-table'})

        if options_table_section:
            return str(options_table_section)  # Return the table's HTML
        else:
            return None  # Table not found

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None  # Handle request errors
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def parse_options_table_html(table, ticker, expiration_date, option_type):
    """
    Parse the Yahoo Finance options HTML table and extract call and put options data.
    
    Args:
        html_content: HTML content containing options tables
        
    Returns:
        Dictionary with extracted calls and puts data
    """
    # Process tables (first table is calls, second is puts)
    all_options = []

    
    # Extract headers to get column indices
    headers = []
    header_row = table.find('thead').find('tr')
    for th in header_row.find_all('th'):
        headers.append(th.text.strip())
    
    # Get column indices
    col_indices = {
        'contract_name': headers.index('Contract Name') if 'Contract Name' in headers else None,
        'last_trade_date': headers.index('Last Trade Date (EDT)') if 'Last Trade Date (EDT)' in headers else None,
        'strike': headers.index('Strike') if 'Strike' in headers else None,
        'last_price': headers.index('Last Price') if 'Last Price' in headers else None,
        'bid': headers.index('Bid') if 'Bid' in headers else None,
        'ask': headers.index('Ask') if 'Ask' in headers else None,
        'volume': headers.index('Volume') if 'Volume' in headers else None,
        'open_interest': headers.index('Open Interest') if 'Open Interest' in headers else None,
        'implied_volatility': headers.index('Implied Volatility') if 'Implied Volatility' in headers else None
    }
    
    # Process rows
    rows = table.find('tbody').find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        
        # Extract data from cells
        contract_name = cells[col_indices['contract_name']].text.strip() if col_indices['contract_name'] is not None else None
        
        # Skip if no contract name
        if not contract_name:
            continue
        
        # Extract symbol and contract-specific expiration date from contract name
        # Example: NVDA250417P00005000
        symbol_match = re.match(r'^([A-Z]+)', contract_name)
        symbol = symbol_match.group(1) if symbol_match else None
        
        contract_type = contract_name[len(symbol)+6] if symbol and len(contract_name) > len(symbol)+6 else None
        option_type_from_code = 'call' if contract_type == 'C' else 'put' if contract_type == 'P' else None
        
        # If option_type_from_code doesn't match our expected option_type, log a warning
        if option_type_from_code and option_type_from_code != option_type:
            print(f"Warning: Option type mismatch for {contract_name}. Expected {option_type}, found {option_type_from_code}")
        
        # Extract strike price
        strike_part = contract_name[len(symbol)+7:] if symbol else None
        strike = float(strike_part) / 1000 if strike_part else None
        
        # Extract and clean numeric values
        try:
            last_price = float(cells[col_indices['last_price']].text.strip().replace(',', '').replace('-','0')) if col_indices['last_price'] is not None else None
            bid = float(cells[col_indices['bid']].text.strip().replace(',', '').replace('-','0')) if col_indices['bid'] is not None else None
            ask = float(cells[col_indices['ask']].text.strip().replace(',', '').replace('-','0')) if col_indices['ask'] is not None else None
            volume = int(cells[col_indices['volume']].text.strip().replace(',', '').replace('-','0')) if col_indices['volume'] is not None else None
            open_interest = int(cells[col_indices['open_interest']].text.strip().replace(',', '').replace('-','0')) if col_indices['open_interest'] is not None else None
            
            # Implied volatility is given as a percentage, convert to decimal
            implied_vol_str = cells[col_indices['implied_volatility']].text.strip() if col_indices['implied_volatility'] is not None else None
            implied_volatility = float(implied_vol_str.replace('%', '')) / 100 if implied_vol_str and implied_vol_str != '0.00%' else None
            
            # Calculate mark (average of bid and ask)
            mark = (bid + ask) / 2 if bid is not None and ask is not None else None
            
            # Create a dictionary with the extracted data
            option_data = {
                'contractID': contract_name,
                'symbol': symbol,
                'expiration': expiration_date,
                'strike': strike,
                'type': option_type,
                'last': last_price,
                'mark': mark,
                'bid': bid,
                'bid_size': None,  # Not available in Yahoo Finance data
                'ask': ask,
                'ask_size': None,  # Not available in Yahoo Finance data
                'volume': volume,
                'open_interest': open_interest,
                'date': datetime.date.today(),  # Use last trade date or today if not available
                'implied_volatility': implied_volatility,
                'delta': None,  # Not available in Yahoo Finance HTML
                'gamma': None,  # Not available in Yahoo Finance HTML
                'theta': None,  # Not available in Yahoo Finance HTML
                'vega': None,   # Not available in Yahoo Finance HTML
                'rho': None     # Not available in Yahoo Finance HTML
            }
            
            all_options.append(option_data)
            
        except (ValueError, TypeError, IndexError) as e:
            print(f"Warning: Error parsing numeric values for {contract_name}: {e}")
    
    return all_options

def insert_options_into_db(db_params, options_data):
    """
    Insert options data into the PostgreSQL database.
    
    Args:
        db_params: Dictionary with database connection parameters
        options_data: List of option data dictionaries
    
    Returns:
        Number of rows inserted/updated
    """
    conn = None
    try:
        # Connect to the database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # SQL for insertion with UPSERT
        upsert_query = """
            INSERT INTO yahoo_finance_options (
                contractID, symbol, expiration, strike, type,
                last, mark, bid, bid_size, ask, ask_size,
                volume, open_interest, date, implied_volatility,
                delta, gamma, theta, vega, rho
            )
            VALUES %s
            ON CONFLICT (contractID, date)
            DO UPDATE SET
                symbol = EXCLUDED.symbol,
                expiration = EXCLUDED.expiration,
                strike = EXCLUDED.strike,
                type = EXCLUDED.type,
                last = EXCLUDED.last,
                mark = EXCLUDED.mark,
                bid = EXCLUDED.bid,
                bid_size = EXCLUDED.bid_size,
                ask = EXCLUDED.ask,
                ask_size = EXCLUDED.ask_size,
                volume = EXCLUDED.volume,
                open_interest = EXCLUDED.open_interest,
                implied_volatility = EXCLUDED.implied_volatility,
                delta = EXCLUDED.delta,
                gamma = EXCLUDED.gamma,
                theta = EXCLUDED.theta,
                vega = EXCLUDED.vega,
                rho = EXCLUDED.rho
        """
        
        # Prepare data for batch insert
        values = []
        for option in options_data:
            values.append((
                option['contractID'],
                option['symbol'],
                option['expiration'],
                option['strike'],
                option['type'],
                option['last'],
                option['mark'],
                option['bid'],
                option['bid_size'],
                option['ask'],
                option['ask_size'],
                option['volume'],
                option['open_interest'],
                option['date'],
                option['implied_volatility'],
                option['delta'],
                option['gamma'],
                option['theta'],
                option['vega'],
                option['rho']
            ))
        
        # Use execute_values for efficient batch insertion
        execute_values(cursor, upsert_query, values)
        
        # Commit the transaction
        conn.commit()
        
        return len(values)
        
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
        
    finally:
        if conn:
            cursor.close()
            conn.close()

def process_options_from_html(html_content, ticker, expiration_date, option_type):
    """
    Process options data from HTML content and insert into database.
    
    Args:
        html_content: HTML content with options tables
        url: URL from which the content was fetched
        db_params: Database connection parameters
    
    Returns:
        Number of records processed
    """
    # Parse options data from HTML
    options_data = parse_options_table_html(html_content, ticker, expiration_date, option_type)
    
    # Insert data into database
    inserted_count = insert_options_into_db(db_params, options_data)
    
    return inserted_count

def update_all_options_data(ticker):
    """
    Update options data for a given ticker.
    
    Args:
        ticker (str): The stock ticker symbol"
    """
    urls, expiration_dates = generate_yahoo_options_urls(ticker)

    if urls:
        for url, expiration_date in zip(urls, expiration_dates): 
            print(f"Fetching data from: {url} for date: {expiration_date}")
            table_html = get_options_table_from_url(url)
            if table_html:
                soup_table = BeautifulSoup(table_html, 'html.parser')
                tables = soup_table.find_all('table')
                for idx,table in enumerate(tables):
                    # check if table class is <table class="yf-wurt5d">
                    if 'yf-wurt5d' in table.get('class', []):
                        try:
                            option_type = 'call' if idx == 0 else 'put'
                            inserted_count = process_options_from_html(table, ticker, expiration_date, option_type)
                            print(f"Successfully processed {inserted_count} options records")
                            
                        except Exception as e:
                            print(f"Error processing options data: {e}")
            else:
                print("Failed to retrieve options table.")
    else:
        print('Failed to generate urls.')


def get_latest_tickers():
    """
    Retrieves a list of distinct ticker symbols from the latest quote date.

    Returns:
        A list of ticker symbols, or None if an error occurs.
    """

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        query = """
            SELECT DISTINCT ticker
            FROM public.stock_quotes
            WHERE quote_date = (SELECT MAX(quote_date) FROM public.stock_quotes)
            ORDER BY ticker ASC
        """

        cur.execute(query)
        tickers = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

        return tickers

    except (psycopg2.Error, Exception) as e:
        print(f"Error retrieving tickers: {e}")
        return None

if __name__ == "__main__":
    my_tickers = get_latest_tickers()
    for ticker in my_tickers:
        update_all_options_data(ticker)
