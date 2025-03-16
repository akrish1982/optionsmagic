import requests
import psycopg2
from datetime import datetime
import time
from collections import defaultdict

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
# print(json.dumps(schema, indent=2))

DB_NAME = "ananth"
DB_USER = "ananth"
DB_PASSWORD = ""
DB_HOST = "localhost"
DB_PORT = "5432"



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
            print(f"Processed {count} record(s) for ticker: {sym}")

    except Exception as e:
        conn.rollback()
        print("Error during upsert:", e)
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
    print(f"Found {len(data)} records in the data array.")
    # Insert/Upsert into Postgres
    insert_option_data(data)
    print("Upsert completed.")

if __name__ == "__main__":
    my_tickers = [ "NVDA", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "TSM", "LLY"]
    # my_tickers = []
    for ticker in my_tickers:
        print(f"Fetching options data for {ticker}")
        url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={ticker}&apikey=4YCZQ62CY2TFUPTQ"
        r = requests.get(url)
        if r.status_code == 200:
            # Parse response JSON or text as needed
            data = r.json()
            print("Success! Data received")
            upsert_into_database(data)
        else:
            # Handle specific status codes or general errors
            print(f"API call failed. Status Code: {r.status_code}")
            print("Response text:", r.text)
        time.sleep(10)  # Sleep for 10s  before next API call
        