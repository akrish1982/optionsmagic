import requests
import json
from datetime import datetime
import os

# Base URLs for TradeStation API
# Note: This example uses the simulator. For live data, change the base URLs.
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

def parse_and_print_data(raw_data, symbol):
    """
    Parses the raw JSON response and prints it in a format
    matching the SQL table schema.
    """
    if not raw_data:
        print("No data to parse.")
        return

    # This parsing logic is a best-effort based on the SQL schema.
    # You will need to adjust it to match the exact JSON structure of the API.
    # Assumed structure: {"Contracts": [{"Symbol": "...", "GreekValues": {"Delta": ...}}]}
    
    options = raw_data.get('Contracts', [])
    if not options:
        print(f"No options data found for symbol {symbol}.")
        return

    print(f"Data for {symbol} collected at {datetime.now().isoformat()}")
    print("-" * 50)

    for option in options:
        try:
            contract_id = option.get('ContractID', 'N/A')
            option_symbol = option.get('Symbol', 'N/A')
            expiration = option.get('ExpirationDate', 'N/A')
            strike = option.get('StrikePrice', 'N/A')
            type = option.get('Type', 'N/A')
            last = option.get('Last', 'N/A')
            mark = option.get('Mark', 'N/A')
            bid = option.get('Bid', 'N/A')
            bid_size = option.get('BidSize', 'N/A')
            ask = option.get('Ask', 'N/A')
            ask_size = option.get('AskSize', 'N/A')
            volume = option.get('Volume', 'N/A')
            open_interest = option.get('OpenInterest', 'N/A')
            
            greeks = option.get('GreekValues', {})
            implied_volatility = greeks.get('ImpliedVolatility', 'N/A')
            delta = greeks.get('Delta', 'N/A')
            gamma = greeks.get('Gamma', 'N/A')
            theta = greeks.get('Theta', 'N/A')
            vega = greeks.get('Vega', 'N/A')
            rho = greeks.get('Rho', 'N/A')

            print(f"Contract ID: {contract_id}")
            print(f"Symbol: {option_symbol}")
            print(f"Expiration: {expiration}")
            print(f"Strike: {strike}")
            print(f"Type: {type}")
            print(f"Last: {last}, Mark: {mark}")
            print(f"Bid: {bid} (Size: {bid_size}), Ask: {ask} (Size: {ask_size})")
            print(f"Volume: {volume}, Open Interest: {open_interest}")
            print(f"Greeks: Delta={delta}, Gamma={gamma}, Theta={theta}, Vega={vega}, Rho={rho}")
            print("-" * 20)

        except Exception as e:
            print(f"Failed to parse data for an option contract. Error: {e}")


if __name__ == "__main__":
    # Define the list of securities you want to track
    securities = ['AAPL', 'MSFT', 'GOOG']
    
    api_client = TradeStationAPI()

    for security_symbol in securities:
        print(f"Fetching options data for {security_symbol}...")
        raw_options_data = api_client.get_options_data(security_symbol)
        parse_and_print_data(raw_options_data, security_symbol)
        print("\n" + "="*50 + "\n")
