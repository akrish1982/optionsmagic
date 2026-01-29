import math
import datetime
from scipy.stats import norm
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs/finviz_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def calculate_option_delta(row, risk_free_rate=0.05):
    try:
        S = row['price']  # Current stock price
        K = row['strike']
        r = risk_free_rate
        sigma = row['implied_volatility']

        # Calculate time to expiration in years
        today = datetime.datetime.combine(row['date'], datetime.time())
        expiration = datetime.datetime.strptime(row['expiration'], "%Y-%m-%d")
        T = (expiration - today).days / 365.0

        if sigma is None or T <= 0 or sigma <= 0:
            logger.info(f"Invalid parameters for delta calculation: T={T}, sigma={sigma}")
            return None  # Option is expired or invalid volatility

        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        if row['type'].lower() == 'call':
            delta = norm.cdf(d1)
        else:  # put
            delta = norm.cdf(d1) - 1
        return round(delta, 4)
    except Exception as e:
        logger.error(f"Error in delta calculation module for {row['symbol']}: {e}")
        logger.error(f"Values: S={row['price']}, K={row['strike']}, r={risk_free_rate}, sigma={row['implied_volatility']}, T={T}")
        return None
