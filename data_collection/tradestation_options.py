"""
TradeStation Options Data Collection

Fetches options data from TradeStation API v3 and stores in Supabase.
Similar functionality to yahoo_finance_options_postgres.py but uses TradeStation
which provides full Greeks (delta, gamma, theta, vega, rho) directly.

Usage:
    poetry run python data_collection/tradestation_options.py
"""

import os
import logging
import json
import time
from datetime import date
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/tradestation_options.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# TradeStation API configuration
SIGNIN_URL = 'https://signin.tradestation.com/oauth/token'
API_BASE_URL = 'https://api.tradestation.com/v3'

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Table to store options data (same schema as yahoo_finance_options)
OPTIONS_TABLE = "options_quotes"

# Import Supabase client
from supabase import create_client


class TradeStationAPI:
    """TradeStation API v3 client for options data."""

    def __init__(self, config_file='tokens.json'):
        self.config_file = config_file
        self.client_id = os.environ.get('TRADESTATION_CLIENT_ID')
        self.client_secret = os.environ.get('TRADESTATION_CLIENT_SECRET')
        self.refresh_token = os.environ.get('TRADESTATION_REFRESH_TOKEN')
        self.access_token = None

        # Fall back to config file
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            self._load_tokens()

    def _load_tokens(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                self.client_id = self.client_id or data.get('client_id')
                self.client_secret = self.client_secret or data.get('client_secret')
                self.refresh_token = self.refresh_token or data.get('refresh_token')

    def refresh_access_token(self):
        """Get a fresh access token."""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False

        response = requests.post(
            SIGNIN_URL,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token
            }
        )

        if response.ok:
            data = response.json()
            self.access_token = data['access_token']
            scopes = data.get('scope', 'unknown')
            logger.info(f"Access token refreshed successfully. Scopes: {scopes}")
            if 'OptionSpreads' not in scopes:
                logger.warning("WARNING: OptionSpreads scope not in token!")
            return True
        else:
            logger.error(f"Token refresh failed: {response.text}")
            return False

    def _get_headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}

    def _ensure_auth(self):
        if not self.access_token:
            return self.refresh_access_token()
        return True

    def _request(self, method, url, **kwargs):
        """Request wrapper that refreshes token once on 401."""
        if not self._ensure_auth():
            raise RuntimeError("TradeStation auth failed: no access token")

        response = requests.request(method, url, headers=self._get_headers(), **kwargs)

        if response.status_code == 401:
            logger.warning("Access token expired, refreshing...")
            if not self.refresh_access_token():
                raise RuntimeError("TradeStation auth failed: refresh token rejected")
            response = requests.request(method, url, headers=self._get_headers(), **kwargs)

        return response

    def get_option_expirations(self, symbol):
        """Get available option expiration dates."""
        url = f'{API_BASE_URL}/marketdata/options/expirations/{symbol}'
        logger.debug(f"Requesting: {url}")
        logger.debug(f"Token (first 20 chars): {self.access_token[:20] if self.access_token else 'None'}...")

        response = self._request("GET", url, timeout=15)

        if response.ok:
            data = response.json()
            return data.get('Expirations', [])
        else:
            logger.error(f"Failed to get expirations for {symbol}: {response.status_code}")
            logger.error(f"Response body: {response.text[:500]}")
            return None

    def get_option_strikes(self, symbol, expiration):
        """Get available strikes for a symbol and expiration."""
        url = f'{API_BASE_URL}/marketdata/options/strikes/{symbol}'
        params = {'expiration': expiration}
        response = self._request("GET", url, params=params, timeout=15)

        if response.ok:
            data = response.json()
            return data.get('Strikes', [])
        else:
            logger.error(f"Failed to get strikes: {response.status_code}")
            return None

    def get_option_chain(self, symbol, expiration, strike_proximity=15, _retry=False):
        """
        Get option chain with quotes and Greeks.
        Uses the streaming endpoint to get full data.
        """
        url = f'{API_BASE_URL}/marketdata/stream/options/chains/{symbol}'
        params = {
            'expiration': expiration,
            'optionType': 'All',
            'strikeProximity': strike_proximity
        }

        try:
            # Use a session with shorter timeouts for streaming
            response = self._request(
                "GET",
                url,
                params=params,
                timeout=(5, 10),  # (connect timeout, read timeout)
                stream=True,
            )

            if not response.ok:
                logger.error(f"Option chain request failed: {response.status_code} - {response.text[:200]}")
                return None

            options = []
            start_time = time.time()
            max_wait = 8  # Max seconds to wait for data

            for line in response.iter_lines():
                # Timeout check
                if time.time() - start_time > max_wait:
                    logger.info(f"Reached time limit, got {len(options)} contracts")
                    break

                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        # Each line is an option contract
                        if 'Symbol' in data or 'Legs' in data:
                            options.append(data)
                        # Also check for Heartbeat to know stream is alive
                        if 'Heartbeat' in data:
                            continue
                        # Limit to avoid huge responses
                        if len(options) >= 100:
                            break
                    except json.JSONDecodeError:
                        continue

            # Close the streaming connection
            response.close()

            logger.info(f"Retrieved {len(options)} contracts for {symbol} exp {expiration}")
            return options

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout getting option chain for {symbol} {expiration}")
            return []
        except Exception as e:
            logger.error(f"Error getting option chain: {e}")
            return None


def get_supabase_client():
    """Get Supabase client."""
    key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
    if not SUPABASE_URL or not key:
        raise ValueError("SUPABASE_URL and (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY) must be set")
    return create_client(SUPABASE_URL, key)


def get_stock_price(supabase, symbol):
    """Get current stock price from stock_quotes table."""
    try:
        response = supabase.table('stock_quotes').select('price').eq('ticker', symbol).order('quote_date', desc=True).limit(1).execute()
        if response.data:
            return float(response.data[0]['price'])
    except Exception as e:
        logger.warning(f"Could not get stock price for {symbol}: {e}")
    return None


def safe_float(value):
    """Safely convert a value to float, handling strings and None."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value):
    """Safely convert a value to int, handling strings and None."""
    if value is None:
        return None
    try:
        return int(float(value))  # Handle "1041" or 1041
    except (ValueError, TypeError):
        return None


def parse_option_contract(contract, underlying, expiration_date, stock_price):
    """
    Parse a TradeStation option contract into database format.
    Matches yahoo_finance_options schema.

    TradeStation response structure:
    - Greeks at root level: Delta, Theta, Gamma, Rho, Vega, ImpliedVolatility (as strings)
    - Quotes at root level: Ask, Bid, Mid, Last, Volume, AskSize, BidSize (as strings)
    - DailyOpenInterest for open interest
    - Side: "Call" or "Put"
    - Legs[0].Symbol: contract symbol (e.g., "AAPL 260123C245")
    - Legs[0].StrikePrice: strike price
    """
    try:
        # Get the contract symbol from Legs
        legs = contract.get('Legs', [])
        if not legs:
            return None

        leg = legs[0]
        symbol = leg.get('Symbol', '')
        if not symbol:
            return None

        # Get strike price from leg
        strike = safe_float(leg.get('StrikePrice', 0))

        # Determine option type from Side field (at root level)
        side = contract.get('Side', '').lower()
        opt_type = 'call' if side == 'call' else 'put'

        # Get quote data from ROOT level (not nested)
        bid = safe_float(contract.get('Bid'))
        ask = safe_float(contract.get('Ask'))
        last = safe_float(contract.get('Last'))
        bid_size = safe_int(contract.get('BidSize'))
        ask_size = safe_int(contract.get('AskSize'))
        volume = safe_int(contract.get('Volume'))
        open_interest = safe_int(contract.get('DailyOpenInterest'))

        # Calculate mark (Mid is also provided directly)
        mark = safe_float(contract.get('Mid'))
        if mark is None and bid is not None and ask is not None:
            mark = (bid + ask) / 2

        # Get Greeks from ROOT level (not nested, and they're strings!)
        implied_volatility = safe_float(contract.get('ImpliedVolatility'))
        delta = safe_float(contract.get('Delta'))
        gamma = safe_float(contract.get('Gamma'))
        theta = safe_float(contract.get('Theta'))
        vega = safe_float(contract.get('Vega'))
        rho = safe_float(contract.get('Rho'))

        return {
            'contractid': symbol,  # lowercase for Supabase
            'symbol': underlying,
            'expiration': expiration_date,
            'strike': strike,
            'type': opt_type,
            'last': last,
            'mark': mark,
            'bid': bid,
            'bid_size': bid_size,
            'ask': ask,
            'ask_size': ask_size,
            'volume': volume,
            'open_interest': open_interest,
            'date': str(date.today()),
            'implied_volatility': implied_volatility,
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho
        }

    except Exception as e:
        logger.warning(f"Error parsing contract: {e}")
        return None


def upsert_options_to_supabase(supabase, options_data, table_name=OPTIONS_TABLE):
    """Upsert options data to Supabase."""
    if not options_data:
        return 0

    try:
        # Deduplicate within this batch to avoid ON CONFLICT affecting same row twice
        deduped = {}
        for row in options_data:
            key = (row.get("contractid"), row.get("date"))
            if None in key:
                continue
            deduped[key] = row  # keep last occurrence
        if len(deduped) != len(options_data):
            logger.info(
                f"Deduped options batch: {len(options_data)} -> {len(deduped)} rows"
            )

        options_data = list(deduped.values())

        batch_size = 100
        total = 0

        for i in range(0, len(options_data), batch_size):
            batch = options_data[i:i + batch_size]
            supabase.table(table_name).upsert(
                batch,
                on_conflict='contractid,date'
            ).execute()
            total += len(batch)

        logger.info(f"Upserted {total} options to {table_name}")
        return total

    except Exception as e:
        logger.error(f"Error upserting to Supabase: {e}")
        raise


def fetch_options_for_ticker(api, supabase, ticker, max_days=90):
    """
    Fetch options data for a ticker and store in Supabase.
    Similar to yahoo_finance_options_postgres.py flow.

    Args:
        api: TradeStationAPI instance
        supabase: Supabase client
        ticker: Stock ticker symbol
        max_days: Maximum days to expiration (default 90)
    """
    total_stored = 0
    today = date.today()

    # Get stock price for reference
    stock_price = get_stock_price(supabase, ticker)
    logger.info(f"Processing {ticker} (price: {stock_price})")

    # Get available expirations
    expirations = api.get_option_expirations(ticker)
    if not expirations:
        logger.warning(f"No expirations found for {ticker}")
        return 0

    # Filter expirations within max_days
    valid_expirations = []
    for exp in expirations:
        exp_date_str = exp.get('Date', '')
        if not exp_date_str:
            continue

        # Format date (remove time portion if present)
        if 'T' in exp_date_str:
            exp_date_str = exp_date_str.split('T')[0]

        # Parse and check days to expiration
        try:
            from datetime import datetime
            exp_date_obj = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
            days_to_exp = (exp_date_obj - today).days

            if 0 < days_to_exp <= max_days:
                valid_expirations.append(exp_date_str)
        except ValueError:
            continue

    logger.info(f"Found {len(valid_expirations)} expirations within {max_days} days for {ticker}")

    # Process each valid expiration
    for exp_date in valid_expirations:
        logger.info(f"Fetching {ticker} options for {exp_date}")

        # Get option chain
        contracts = api.get_option_chain(ticker, exp_date)
        if not contracts:
            continue

        # Parse contracts
        parsed = []
        for contract in contracts:
            option_data = parse_option_contract(contract, ticker, exp_date, stock_price)
            if option_data:
                parsed.append(option_data)

        # Store in Supabase
        if parsed:
            stored = upsert_options_to_supabase(supabase, parsed)
            total_stored += stored

        # Rate limiting
        time.sleep(0.5)

    return total_stored


def get_tickers_from_supabase(supabase):
    """Get list of tickers from stock_quotes table."""
    try:
        # Get most recent quote_date
        response = supabase.table('stock_quotes').select('quote_date').order('quote_date', desc=True).limit(1).execute()
        if not response.data:
            return []

        latest_date = response.data[0]['quote_date']

        # Get all tickers for that date
        response = supabase.table('stock_quotes').select('ticker').eq('quote_date', latest_date).execute()
        tickers = sorted(set(row['ticker'] for row in response.data))
        return tickers

    except Exception as e:
        logger.error(f"Error getting tickers: {e}")
        return []


PROGRESS_FILE = "tradestation_progress.json"


def load_progress():
    """Load progress from file to resume from last successful ticker."""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load progress file: {e}")
    return {"last_completed_ticker": None, "date": None}


def save_progress(ticker):
    """Save progress after successfully processing a ticker."""
    try:
        progress = {
            "last_completed_ticker": ticker,
            "date": str(date.today()),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f)
    except Exception as e:
        logger.warning(f"Could not save progress: {e}")


def clear_progress():
    """Clear progress file after successful completion."""
    try:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            logger.info("Progress file cleared")
    except Exception as e:
        logger.warning(f"Could not clear progress file: {e}")


def main(resume=True):
    """
    Main function to fetch options data for all tracked tickers.

    Args:
        resume: If True, resume from last successful ticker (default True)
    """
    logger.info("Starting TradeStation options data collection")

    # Initialize API client
    api = TradeStationAPI()
    if not api.refresh_access_token():
        logger.error("Failed to authenticate with TradeStation")
        return

    # Initialize Supabase client
    supabase = get_supabase_client()

    # Get tickers to process
    tickers = get_tickers_from_supabase(supabase)
    logger.info(f"Found {len(tickers)} tickers to process")

    if not tickers:
        logger.warning("No tickers found in stock_quotes")
        return

    # Check for resume point
    start_index = 0
    if resume:
        progress = load_progress()
        if progress["last_completed_ticker"] and progress["date"] == str(date.today()):
            last_ticker = progress["last_completed_ticker"]
            if last_ticker in tickers:
                start_index = tickers.index(last_ticker) + 1
                logger.info(f"Resuming from ticker #{start_index + 1} (after {last_ticker})")

    if start_index >= len(tickers):
        logger.info("All tickers already processed today")
        return

    # Process each ticker
    total_options = 0
    for i, ticker in enumerate(tickers[start_index:], start=start_index):
        logger.info(f"Processing {ticker} ({i+1}/{len(tickers)})")
        try:
            count = fetch_options_for_ticker(api, supabase, ticker, max_days=90)
            total_options += count

            # Save progress after each successful ticker
            save_progress(ticker)

        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            logger.info("Progress not advanced for this ticker; rerun to retry.")
            continue

        # Rate limiting between tickers
        time.sleep(1)

    # Clear progress file on successful completion
    clear_progress()
    logger.info(f"Completed. Total options stored: {total_options}")


if __name__ == "__main__":
    main()
