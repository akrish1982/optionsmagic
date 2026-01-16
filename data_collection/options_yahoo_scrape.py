import os
import requests
import random
import psycopg2
from datetime import datetime
import time
from collections import defaultdict
import json
import re
import ast
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("finviz_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# Database configuration - set these as environment variables in your production environment
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "<user>")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

def parse_options_data(file_path):
    """
    Parse the Yahoo Finance options data from a text file.
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract calls and puts sections
    calls_match = re.search(r'Calls: (\[.*?\])\s*Puts:', content, re.DOTALL)
    puts_match = re.search(r'Puts: (\[.*?\])', content, re.DOTALL)
    
    if not calls_match or not puts_match:
        raise ValueError("Could not find Calls or Puts sections in the file")
    
    # Convert from Python-style dict to JSON
    calls_str = calls_match.group(1).replace("'", '"')
    puts_str = puts_match.group(1).replace("'", '"')
    
    # Parse as Python literals since JSON conversion might be problematic
    calls = ast.literal_eval(calls_match.group(1))
    puts = ast.literal_eval(puts_match.group(1))
    
    return calls, puts

def map_option_to_db_schema(option_data, option_type):
    """
    Map a single option contract to the database schema.
    
    Args:
        option_data: Dictionary containing Yahoo Finance option data
        option_type: 'call' or 'put'
    
    Returns:
        Dictionary with mapped values ready for database insertion
    """
    # Extract data from contract name: e.g., NVDA250417C00005000
    contract_name = option_data['Contract Name']
    
    # Extract symbol (NVDA)
    symbol_match = re.match(r'^[A-Z]+', contract_name)
    if not symbol_match:
        raise ValueError(f"Could not parse symbol from contract name: {contract_name}")
    
    symbol = symbol_match.group(0)
    
    # Extract expiration date (YYMMDD format in the contract name)
    date_start = len(symbol)
    date_code = contract_name[date_start:date_start+6]  # 250417
    
    exp_year = f"20{date_code[0:2]}"
    exp_month = date_code[2:4]
    exp_day = date_code[4:6]
    expiration = f"{exp_year}-{exp_month}-{exp_day}"
    
    # Verify option type from contract name
    type_from_contract = contract_name[date_start+6]
    if (type_from_contract == 'C' and option_type != 'call') or (type_from_contract == 'P' and option_type != 'put'):
        logger.info(f"Warning: Option type mismatch for {contract_name}. Expected {option_type}, found {type_from_contract}")
    
    # Extract strike price (divide by 1000 to get actual value)
    strike_str = contract_name[date_start+7:]
    strike = float(strike_str) / 1000
    
    # Parse last trade date
    last_trade_str = option_data['Last Trade Date (EDT)']
    date_time_parts = last_trade_str.split('  ')  # Double space separator
    date_part = date_time_parts[0]
    
    month, day, year = date_part.split('/')
    trade_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    # Remove commas from numeric strings and parse
    last_price = float(option_data['Last Price'])
    bid = float(option_data['Bid'])
    ask = float(option_data['Ask'])
    
    # Calculate mark as average of bid and ask
    mark = (bid + ask) / 2
    
    # Parse volume and open interest
    volume = int(option_data['Volume'].replace(',', ''))
    open_interest = int(option_data['Open Interest'].replace(',', ''))
    
    # Parse implied volatility (convert from percentage)
    implied_vol_str = option_data['Implied Volatility'].replace('%', '')
    implied_vol = float(implied_vol_str) / 100 if implied_vol_str != "0.00" else None
    
    # Map to database schema
    return {
        'contractID': contract_name,
        'symbol': symbol,
        'expiration': expiration,
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
        'date': trade_date,
        'implied_volatility': implied_vol,
        'delta': None,  # Not available in Yahoo Finance data
        'gamma': None,  # Not available in Yahoo Finance data
        'theta': None,  # Not available in Yahoo Finance data
        'vega': None,   # Not available in Yahoo Finance data
        'rho': None     # Not available in Yahoo Finance data
    }

def insert_options_into_db(db_config, options_data):
    """
    Insert options data into the database.
    
    Args:
        db_config: Dictionary with database connection parameters
        options_data: List of option data dictionaries
    """
    conn = None
    try:
        # Connect to the database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # SQL for insertion with UPSERT
        upsert_query = """
            INSERT INTO alpha_vantage_options (
                contractID, symbol, expiration, strike, type,
                last, mark, bid, bid_size, ask, ask_size,
                volume, open_interest, date, implied_volatility,
                delta, gamma, theta, vega, rho
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
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
        
        # Batch insert options
        for option in options_data:
            cursor.execute(upsert_query, (
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
        
        # Commit the transaction
        conn.commit()
        logger.info(f"Successfully inserted {len(options_data)} options into the database")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.info(f"Database error: {e}")
        
    finally:
        if conn:
            cursor.close()
            conn.close()

def main():
    # Configuration
    file_path = 'paste.txt'  # Path to the Yahoo Finance options data file
    db_config = {
        'host': DB_HOST,
        'database': DB_NAME,
        'user': DB_USER,
        'password': DB_PASSWORD
    }
    
    try:
        # Parse options data
        calls, puts = parse_options_data(file_path)
        
        # Map options to database schema
        call_options = [map_option_to_db_schema(call, 'call') for call in calls]
        put_options = [map_option_to_db_schema(put, 'put') for put in puts]
        
        # Combine calls and puts
        all_options = call_options + put_options
        
        # Print sample for verification
        logger.info(f"Processed {len(all_options)} options")
        logger.info("Sample mapped option:")
        logger.info(json.dumps(all_options[0], indent=2))
        
        # Insert into database
        # Uncomment when ready to insert
        # insert_options_into_db(db_config, all_options)
        
    except Exception as e:
        logger.info(f"Error processing options data: {e}")

def generate_jsonschema(json_data):
    """Generate a jsonschema from a JSON object."""
    def _infer_type(value):
        if isinstance(value, dict):
            return "object"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, bool):
            return "boolean"
        elif value is None:
            return "null"
        else:
            return "unknown"

    def _infer_properties(data):
        if isinstance(data, dict):
            properties = {}
            for key, value in data.items():
                properties[key] = {"type": _infer_type(value)}
                if properties[key]["type"] == "object":
                    properties[key]["properties"] = _infer_properties(value)
                elif properties[key]["type"] == "array" and value:
                    properties[key]["items"] = {"type": _infer_type(value[0])}
                    if properties[key]["items"]["type"] == "object":
                        properties[key]["items"]["properties"] = _infer_properties(value[0])
            return properties
        else:
            return {}

    schema = {"type": _infer_type(json_data)}
    if schema["type"] == "object":
        schema["properties"] = _infer_properties(json_data)
    elif schema["type"] == "array" and json_data:
        schema["items"] = {"type": _infer_type(json_data[0])}
        if schema["items"]["type"] == "object":
            schema["items"]["properties"] = _infer_properties(json_data[0])

    return schema

# schema = generate_jsonschema(data) - THIS IS NEEDED ONLY ONCE TO GENERATE THE SCHEMA
# logger.info(json.dumps(schema, indent=2))

def extract_option_tables(soup):
    """
    Extracts call and put option tables from an HTML string.

    Args:
        soup: The HTML string containing the option tables.

    Returns:
        A tuple containing two lists of dictionaries, representing the call and put tables, respectively.
        Each dictionary represents a row in the table, with keys corresponding to the table headers.
    """

    options_section = soup.find('section', {'data-testid': 'options-list-table'})
    table_sections = options_section.find_all('div', class_='tableContainer yf-wurt5d')
    title_sections = options_section.find_all('div', class_='optionsHeader yf-wurt5d')

    tables, table_titles = [], []
    for table_section in table_sections:
        tables.append(table_section.find('table'))
    for title_section in title_sections:
        table_titles.append(title_section.find('h3').text.strip())

    call_table_data = []
    put_table_data = []

    for table, table_title in zip(tables, table_titles):

        headers = [th.text.strip() for th in table.find_all('th')]
        rows = table.find_all('tr')[1:]  # Skip header row

        table_data = []
        for row in rows:
            cells = row.find_all('td')
            row_data = {}
            for i, cell in enumerate(cells):
                row_data[headers[i]] = cell.text.strip()
            table_data.append(row_data)

        if table_title == 'Calls':
            call_table_data = table_data
        elif table_title == 'Puts':
            put_table_data = table_data

    return call_table_data, put_table_data

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
        logger.info(f"Error retrieving tickers: {e}")
        return None

def insert_option_data(data_list):
    """
    Insert or update (UPSERT) a list of option-data dictionaries into 
    the alpha_vantage_options table, tracking how many records were
    processed per ticker and printing the results.
    """
    # Fetch DB credentials from environment variables (or None if not set)

    upsert_query = """
        INSERT INTO alpha_vantage_options (
            contractID, symbol, expiration, strike, type,
            last, mark, bid, bid_size, ask, ask_size,
            volume, open_interest, date, implied_volatility,
            delta, gamma, theta, vega, rho
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
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
    
    # Connect to the database
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    # Dictionary to track how many records per ticker
    processed_counts = defaultdict(int)

    try:
        # Helper function for safe float conversion
        def to_float(s):
            try:
                return float(s)
            except:
                return None

        for record in data_list:
            contract_id = record.get('contractID', '')
            symbol      = record.get('symbol', '')

            # convert 'expiration' and 'date'
            expiration_str = record.get('expiration', '1900-01-01')
            if expiration_str:
                expiration_val = datetime.strptime(expiration_str, "%Y-%m-%d").date()
            else:
                expiration_val = None

            date_str = record.get('date', '1900-01-01')
            if date_str:
                date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                date_val = None

            # numeric fields
            strike_val = to_float(record.get('strike', '0.0'))
            last_val   = to_float(record.get('last', '0.0'))
            mark_val   = to_float(record.get('mark', '0.0'))
            bid_val    = to_float(record.get('bid', '0.0'))
            ask_val    = to_float(record.get('ask', '0.0'))

            bid_size_val = int(record.get('bid_size', '0')) if record.get('bid_size', '0') else 0
            ask_size_val = int(record.get('ask_size', '0')) if record.get('ask_size', '0') else 0
            volume_val   = int(record.get('volume', '0')) if record.get('volume', '0') else 0
            oi_val       = int(record.get('open_interest', '0')) if record.get('open_interest', '0') else 0

            iv_val    = to_float(record.get('implied_volatility', '0.0'))
            delta_val = to_float(record.get('delta', '0.0'))
            gamma_val = to_float(record.get('gamma', '0.0'))
            theta_val = to_float(record.get('theta', '0.0'))
            vega_val  = to_float(record.get('vega', '0.0'))
            rho_val   = to_float(record.get('rho', '0.0'))

            opt_type = record.get('type', '')

            # Construct the parameter tuple
            values_tuple = (
                contract_id, symbol, expiration_val, strike_val, opt_type,
                last_val, mark_val, bid_val, bid_size_val, ask_val, ask_size_val,
                volume_val, oi_val, date_val, iv_val,
                delta_val, gamma_val, theta_val, vega_val, rho_val
            )
            
            cursor.execute(upsert_query, values_tuple)

            # Track how many records we processed for this ticker
            processed_counts[symbol] += 1

        conn.commit()

        # After commit, print out how many records processed for each symbol
        for sym, count in processed_counts.items():
            logger.info(f"Processed {count} record(s) for ticker: {sym}")

    except Exception as e:
        conn.rollback()
        logger.info("Error during upsert:", e)
    finally:
        cursor.close()
        conn.close()

def upsert_into_database(response):
    """
    Example main function showing how to parse the entire JSON response,
    extract the data array, and pass it to insert_option_data().
    """
    # Parse the JSON
    # json_obj = json.loads(response)
    # Extract the "data" array
    data = response.get("data", [])
    logger.info(f"Found {len(data)} records in the data array.")
    # Insert/Upsert into Postgres
    insert_option_data(data)
    logger.info("Upsert completed.")


# if __name__ == "__main__":
#     # my_tickers = [ "NVDA", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "TSM", "LLY"]
#     my_tickers = get_latest_tickers()
#     logger.info(f"Found {len(my_tickers)} tickers.")
#     logger.info(my_tickers)
    # for ticker in my_tickers:
    #     logger.info(f"Fetching options data for {ticker}")
    #     url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={ticker}&apikey={API_KEY}"
    #     r = requests.get(url)
    #     if r.status_code == 200:
    #         # Parse response JSON or text as needed
    #         data = r.json()
    #         logger.info("Success! Data received")
    #         upsert_into_database(data)
    #     else:
    #         # Handle specific status codes or general errors
    #         logger.info(f"API call failed. Status Code: {r.status_code}")
    #         logger.info("Response text:", r.text)
    #     time.sleep(10)  # Sleep for 10s  before next API call

    # for index, ticker in enumerate(my_tickers):
    #     logger.info(f"Fetching options data for {ticker}")
    #     url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={ticker}&apikey={API_KEY}"
    #     try:
    #         r = requests.get(url)
    #         r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
    #         data = r.json()
    #         logger.info("Success! Data received")
    #         upsert_into_database(data)
    #         logger.info(f"Response text: {r.text}")

    #     except requests.exceptions.RequestException as e:
    #         logger.info(f"API call failed: {e}")
    #         if r is not None:
    #             logger.info(f"Status Code: {r.status_code}")
    #             logger.info(f"Response text: {r.text}")
    #         else:
    #             logger.info("No response object available.")

    #     # Delay logic:
    #     random_delay = random.randint(10, 120)
    #     logger.info(f"Sleeping for {random_delay} seconds...")
    #     time.sleep(random_delay)

    #     if (index + 1) % 10 == 0:  # Check if 10 stocks have been processed
    #         logger.info("Processing 10 stocks, sleeping for 300 seconds...")
    #         time.sleep(300)
    #     logger.info("Continuing with next ticker.")
        