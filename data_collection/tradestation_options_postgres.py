import os
import datetime
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import time
import json
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Load environment variables from .env
load_dotenv()

# Database configuration
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "ananth")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")

# TradeStation API configuration
TS_CLIENT_ID = os.environ.get("TS_CLIENT_ID")  # Your API Key
TS_CLIENT_SECRET = os.environ.get("TS_CLIENT_SECRET")  # Your API Secret
TS_REDIRECT_URI = os.environ.get("TS_REDIRECT_URI", "http://localhost:8080/callback")
TS_ACCESS_TOKEN = os.environ.get("TS_ACCESS_TOKEN")
TS_REFRESH_TOKEN = os.environ.get("TS_REFRESH_TOKEN")

# TradeStation API endpoints
TS_BASE_URL = "https://api.tradestation.com/v3"
TS_AUTH_URL = "https://signin.tradestation.com/authorize"
TS_TOKEN_URL = "https://signin.tradestation.com/oauth/token"

db_params = {
    'host': DB_HOST,
    'database': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'port': DB_PORT
}

class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback"""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Extract authorization code from URL
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.wfile.write(b'<html><body><h1>Authorization successful!</h1><p>You can close this window.</p></body></html>')
        else:
            self.wfile.write(b'<html><body><h1>Authorization failed!</h1></body></html>')
    
    def log_message(self, format, *args):
        # Suppress log messages
        return
SIGNIN_URL = 'https://signin.tradestation.com/oauth/token'
API_BASE_URL = 'https://api.tradestation.com/v3'

class TradeStationAPI:
    """
    A class to handle authentication and data retrieval from the TradeStation API.
    """

    def __init__(self, config_file='tokens.json'):
        """
        Initializes the API client by loading credentials and tokens.
        """
        self.config_file = config_file
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.refresh_token = None
        self._load_tokens()
    
    def _load_tokens(self):
        """
        Loads client credentials and refresh token from a JSON file.
        """
        if not os.path.exists(self.config_file):
            print(f"Error: {self.config_file} not found. "
                  "Please create this file with your client_id, client_secret, and refresh_token.")
            return

        with open(self.config_file, 'r') as f:
            data = json.load(f)
            self.client_id = data.get('client_id')
            self.client_secret = data.get('client_secret')
            self.refresh_token = data.get('refresh_token')

        if not all([self.client_id, self.client_secret, self.refresh_token]):
            print("Error: Missing client_id, client_secret, or refresh_token in tokens.json.")

    def _save_refresh_token(self, new_refresh_token):
        """
        Saves the new refresh token to the config file after a successful refresh.
        """
        if self.client_id and self.client_secret:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': new_refresh_token
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
            self.refresh_token = new_refresh_token
            print("New refresh token saved successfully.")

    def refresh_access_token(self):
        """
        Refreshes the access token using the stored refresh token.
        """
        if not self.refresh_token:
            print("No refresh token available. Cannot refresh.")
            return False

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token
        }
        
        try:
            response = requests.post(SIGNIN_URL, headers=headers, data=payload)
            response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
            token_data = response.json()
            
            self.access_token = token_data['access_token']
            print("Access token refreshed successfully.")
            
            # The docs say the refresh token is non-expiring by default,
            # but for a rotating setup, you would save the new one.
            # Example: if 'refresh_token' in token_data: self._save_refresh_token(token_data['refresh_token'])
            
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing access token: {e}")
            return False

    def get_options_data(self, symbol):
        """
        Retrieves options data for a given security symbol.
        """
        if not self.access_token:
            if not self.refresh_access_token():
                return None
        
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        # This endpoint is a placeholder. You'll need to find the specific
        # endpoint in the TradeStation API documentation.
        # A common pattern is to get the options chain and then get quotes/greeks.
        endpoint = f'/marketdata/stream/options/chains/{symbol}'
        url = f'{API_BASE_URL}{endpoint}'

        # Additional parameters might be needed for specific expiration dates, etc.
        # For a full implementation, you would need to iterate through all expirations.
        params = {
            'strikePrice': '100', # Example strike price
            'expiry': '2025-12-31' # Example expiration date
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving options data: {e}")
            return None


# class TradeStationAPI:
#     def __init__(self, client_id, client_secret, redirect_uri, access_token=None, refresh_token=None):
#         self.client_id = client_id
#         self.client_secret = client_secret
#         self.redirect_uri = redirect_uri
#         self.access_token = access_token
#         self.refresh_token = refresh_token
#         self.session = requests.Session()
        
#     def get_authorization_url(self):
#         """Generate the authorization URL for OAuth flow"""
#         params = {
#             'response_type': 'code',
#             'client_id': self.client_id,
#             'audience': 'https://api.tradestation.com',
#             'redirect_uri': self.redirect_uri,
#             'scope': 'openid offline_access profile MarketData ReadAccount',
#             'state': 'xyz123'  # You should generate a random state
#         }
        
#         return f"{TS_AUTH_URL}?" + urllib.parse.urlencode(params)
    
#     def get_tokens_from_auth_code(self, auth_code):
#         """Exchange authorization code for access and refresh tokens"""
#         headers = {
#             'Content-Type': 'application/x-www-form-urlencoded'
#         }
        
#         data = {
#             'grant_type': 'authorization_code',
#             'client_id': self.client_id,
#             'client_secret': self.client_secret,
#             'code': auth_code,
#             'redirect_uri': self.redirect_uri
#         }
        
#         response = requests.post(TS_TOKEN_URL, headers=headers, data=data)
#         response.raise_for_status()
        
#         token_data = response.json()
#         self.access_token = token_data['access_token']
#         self.refresh_token = token_data.get('refresh_token')
        
#         print("Tokens obtained successfully!")
#         print(f"Access Token: {self.access_token[:20]}...")
#         print(f"Refresh Token: {self.refresh_token[:20] if self.refresh_token else 'None'}...")
        
#         return token_data
        
#     def refresh_access_token(self):
#         """Refresh the access token using the refresh token"""
#         if not self.refresh_token:
#             raise ValueError("No refresh token available")
            
#         headers = {
#             'Content-Type': 'application/x-www-form-urlencoded'
#         }
        
#         data = {
#             'grant_type': 'refresh_token',
#             'client_id': self.client_id,
#             'client_secret': self.client_secret,
#             'refresh_token': self.refresh_token
#         }
        
#         response = requests.post(TS_TOKEN_URL, headers=headers, data=data)
#         response.raise_for_status()
        
#         token_data = response.json()
#         self.access_token = token_data['access_token']
#         if 'refresh_token' in token_data:
#             self.refresh_token = token_data['refresh_token']
            
#         print("Access token refreshed successfully!")
#         return self.access_token
        
#     def make_request(self, endpoint, params=None):
#         """Make authenticated request to TradeStation API"""
#         headers = {
#             'Authorization': f'Bearer {self.access_token}',
#             'Content-Type': 'application/json'
#         }
        
#         url = f"{TS_BASE_URL}{endpoint}"
        
#         try:
#             response = self.session.get(url, headers=headers, params=params)
            
#             # If token expired, refresh and retry
#             if response.status_code == 401:
#                 print("Access token expired, refreshing...")
#                 self.refresh_access_token()
#                 headers['Authorization'] = f'Bearer {self.access_token}'
#                 response = self.session.get(url, headers=headers, params=params)
                
#             response.raise_for_status()
#             return response.json()
            
#         except requests.exceptions.RequestException as e:
#             print(f"API request failed: {e}")
#             if hasattr(e.response, 'text'):
#                 print(f"Response: {e.response.text}")
#             return None
            
#     def authenticate(self):
#         """Complete OAuth flow to get tokens"""
#         if self.access_token:
#             # Test if current token works
#             test_response = self.make_request("/accounts")
#             if test_response is not None:
#                 print("Existing access token is valid")
#                 return True
        
#         # Need to get new tokens
#         print("Starting OAuth flow...")
#         auth_url = self.get_authorization_url()
#         print(f"Opening browser for authorization: {auth_url}")
        
#         # Start local server to receive callback
#         server = HTTPServer(('localhost', 8080), CallbackHandler)
#         server.auth_code = None
        
#         # Start server in background
#         server_thread = threading.Thread(target=server.serve_forever)
#         server_thread.daemon = True
#         server_thread.start()
        
#         # Open browser for user authentication
#         webbrowser.open(auth_url)
        
#         # Wait for authorization code
#         print("Waiting for authorization...")
#         timeout = 300  # 5 minutes
#         start_time = time.time()
        
#         while server.auth_code is None and (time.time() - start_time) < timeout:
#             time.sleep(1)
        
#         server.shutdown()
        
#         if server.auth_code:
#             # Exchange code for tokens
#             token_data = self.get_tokens_from_auth_code(server.auth_code)
#             return True
#         else:
#             print("Authorization timed out or failed")
#             return False
            
#     def get_option_expirations(self, symbol):
#         """Get available option expiration dates for a symbol"""
#         endpoint = f"/marketdata/options/expirations/{symbol}"
#         return self.make_request(endpoint)
        
#     def get_option_strikes(self, symbol, expiration):
#         """Get available option strikes for a symbol and expiration"""
#         endpoint = f"/marketdata/options/strikes/{symbol}"
#         params = {'expiration': expiration}
#         return self.make_request(endpoint, params)
        
#     def get_option_chains(self, symbol, expiration, spread=None):
#         """Get option chains for a symbol and expiration"""
#         endpoint = f"/marketdata/options/chains/{symbol}"
#         params = {'expiration': expiration}
        
#         if spread:
#             params['spread'] = spread
            
#         return self.make_request(endpoint, params)
        
#     def get_quotes(self, symbols):
#         """Get quotes for multiple symbols"""
#         endpoint = "/marketdata/quotes"
#         # Convert list of symbols to comma-separated string
#         if isinstance(symbols, list):
#             symbols = ','.join(symbols)
#         params = {'symbols': symbols}
#         return self.make_request(endpoint, params)

def get_next_fridays(num_weeks=8):
    """Get the next N Fridays for option expirations"""
    fridays = []
    today = datetime.date.today()
    
    # Find the next Friday
    days_ahead = 4 - today.weekday()  # 4 = Friday
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
        
    next_friday = today + datetime.timedelta(days=days_ahead)
    
    for i in range(num_weeks):
        friday = next_friday + datetime.timedelta(weeks=i)
        fridays.append(friday.strftime('%Y-%m-%d'))
        
    return fridays

def fetch_options_data_for_ticker(ts_api, ticker):
    """Fetch options data for a specific ticker"""
    all_options = []
    
    # Get available expirations
    print(f"Fetching expirations for {ticker}")
    expirations_data = ts_api.get_option_expirations(ticker)
    
    if not expirations_data:
        print(f"No expirations found for {ticker}")
        return []
    
    print(f"Expirations response: {expirations_data}")
    
    # Get next 8 Fridays
    target_fridays = get_next_fridays(8)
    print(f"Target Fridays: {target_fridays}")
    
    # TradeStation API response format may vary - let's handle different formats
    available_expirations = []
    if isinstance(expirations_data, list):
        available_expirations = [exp if isinstance(exp, str) else exp.get('Date', exp.get('ExpirationDate', '')) for exp in expirations_data]
    elif isinstance(expirations_data, dict):
        if 'Expirations' in expirations_data:
            available_expirations = [exp.get('Date', exp.get('ExpirationDate', '')) for exp in expirations_data['Expirations']]
        elif 'expirations' in expirations_data:
            available_expirations = expirations_data['expirations']
    
    print(f"Available expirations: {available_expirations}")
    
    # Filter expirations to only include our target dates
    relevant_expirations = [exp for exp in available_expirations if exp in target_fridays]
    
    if not relevant_expirations:
        print(f"No relevant expirations found for {ticker}")
        return []
    
    # For each expiration, get the option chains
    for expiration in relevant_expirations:
        print(f"Fetching options for {ticker} expiring {expiration}")
        
        # Get option chains
        chains_data = ts_api.get_option_chains(ticker, expiration)
        
        if not chains_data:
            print(f"No options data found for {ticker} expiring {expiration}")
            continue
            
        print(f"Chains response: {chains_data}")
        
        # Process each option contract - handle different response formats
        options_list = []
        if isinstance(chains_data, list):
            options_list = chains_data
        elif isinstance(chains_data, dict):
            if 'Options' in chains_data:
                options_list = chains_data['Options']
            elif 'options' in chains_data:
                options_list = chains_data['options']
            elif 'Calls' in chains_data or 'Puts' in chains_data:
                if 'Calls' in chains_data:
                    options_list.extend(chains_data['Calls'])
                if 'Puts' in chains_data:
                    options_list.extend(chains_data['Puts'])
        
        for option in options_list:
            option_data = parse_tradestation_option(option, ticker, expiration)
            if option_data:
                all_options.append(option_data)
                
        # Rate limiting - be respectful to the API
        time.sleep(0.5)
    
    return all_options

def parse_tradestation_option(option, ticker, expiration):
    """Parse TradeStation option data into our database format"""
    try:
        # Extract option details - handle different response formats
        symbol = option.get('Symbol', option.get('symbol', ''))
        strike = float(option.get('Strike', option.get('strike', 0)))
        
        # Determine option type
        option_type = None
        if 'Type' in option:
            option_type = 'call' if option['Type'].lower() in ['call', 'c'] else 'put'
        elif 'type' in option:
            option_type = 'call' if option['type'].lower() in ['call', 'c'] else 'put'
        elif 'OptionType' in option:
            option_type = 'call' if option['OptionType'].lower() in ['call', 'c'] else 'put'
        else:
            # Try to determine from symbol
            if symbol.endswith('C') or 'C' in symbol[-3:]:
                option_type = 'call'
            elif symbol.endswith('P') or 'P' in symbol[-3:]:
                option_type = 'put'
        
        # Get pricing data - handle nested or flat structure
        bid = ask = last = volume = None
        
        if 'Quote' in option:
            quote = option['Quote']
            bid = float(quote.get('Bid', 0)) if quote.get('Bid') else None
            ask = float(quote.get('Ask', 0)) if quote.get('Ask') else None
            last = float(quote.get('Last', 0)) if quote.get('Last') else None
            volume = int(quote.get('Volume', 0)) if quote.get('Volume') else None
        else:
            # Try flat structure
            bid = float(option.get('Bid', option.get('bid', 0))) if option.get('Bid') or option.get('bid') else None
            ask = float(option.get('Ask', option.get('ask', 0))) if option.get('Ask') or option.get('ask') else None
            last = float(option.get('Last', option.get('last', 0))) if option.get('Last') or option.get('last') else None
            volume = int(option.get('Volume', option.get('volume', 0))) if option.get('Volume') or option.get('volume') else None
        
        # Calculate mark (mid-point)
        mark = (bid + ask) / 2 if bid and ask else None
        
        # Get additional data
        open_interest = None
        if 'OpenInterest' in option:
            open_interest = int(option['OpenInterest']) if option['OpenInterest'] else None
        elif 'open_interest' in option:
            open_interest = int(option['open_interest']) if option['open_interest'] else None
        
        implied_vol = None
        if 'ImpliedVolatility' in option:
            implied_vol = float(option['ImpliedVolatility']) if option['ImpliedVolatility'] else None
        elif 'implied_volatility' in option:
            implied_vol = float(option['implied_volatility']) if option['implied_volatility'] else None
        
        # Greeks (if available)
        delta = gamma = theta = vega = rho = None
        if 'Greeks' in option:
            greeks = option['Greeks']
            delta = float(greeks.get('Delta', 0)) if greeks.get('Delta') else None
            gamma = float(greeks.get('Gamma', 0)) if greeks.get('Gamma') else None
            theta = float(greeks.get('Theta', 0)) if greeks.get('Theta') else None
            vega = float(greeks.get('Vega', 0)) if greeks.get('Vega') else None
            rho = float(greeks.get('Rho', 0)) if greeks.get('Rho') else None
        
        return {
            'contractID': symbol,
            'symbol': ticker,
            'expiration': expiration,
            'strike': strike,
            'type': option_type,
            'last': last,
            'mark': mark,
            'bid': bid,
            'bid_size': None,
            'ask': ask,
            'ask_size': None,
            'volume': volume,
            'open_interest': open_interest,
            'date': datetime.date.today(),
            'implied_volatility': implied_vol,
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho
        }
        
    except (ValueError, TypeError, KeyError) as e:
        print(f"Error parsing option data: {e}")
        print(f"Option data: {option}")
        return None

def insert_options_into_db(db_params, options_data):
    """
    Insert options data into the PostgreSQL database.
    """
    if not options_data:
        return 0
        
    conn = None
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
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
        
        values = []
        for option in options_data:
            values.append((
                option['contractID'], option['symbol'], option['expiration'],
                option['strike'], option['type'], option['last'], option['mark'],
                option['bid'], option['bid_size'], option['ask'], option['ask_size'],
                option['volume'], option['open_interest'], option['date'],
                option['implied_volatility'], option['delta'], option['gamma'],
                option['theta'], option['vega'], option['rho']
            ))
        
        execute_values(cursor, upsert_query, values)
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

def update_all_options_data(ticker, ts_api):
    """Update options data for a given ticker using TradeStation API."""
    try:
        print(f"Fetching options data for {ticker}")
        options_data = fetch_options_data_for_ticker(ts_api, ticker)
        
        if options_data:
            inserted_count = insert_options_into_db(db_params, options_data)
            print(f"Successfully processed {inserted_count} options records for {ticker}")
        else:
            print(f"No options data found for {ticker}")
            
    except Exception as e:
        print(f"Error updating options data for {ticker}: {e}")

def get_latest_tickers():
    """Retrieves a list of distinct ticker symbols from the latest quote date."""
    try:
        conn = psycopg2.connect(**db_params)
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
    # Initialize TradeStation API
    if not all([TS_CLIENT_ID, TS_CLIENT_SECRET]):
        print("Error: Missing TradeStation API credentials")
        print("Please set TS_CLIENT_ID and TS_CLIENT_SECRET environment variables")
        exit(1)
    
    ts_api = TradeStationAPI()
    
    # Get tickers and update options data
    my_tickers = get_latest_tickers()
    
    if my_tickers:
        for ticker in my_tickers:
            update_all_options_data(ticker, ts_api)
            # Add delay between tickers to respect API rate limits
            time.sleep(2)
    else:
        print("No tickers found to process")
