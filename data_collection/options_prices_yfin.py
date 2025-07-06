from yahoo_fin import stock_info as si
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

def get_eod_options_yahoo_fin(ticker):
    # Get current price
    current_price = si.get_live_price(ticker)
    logger.info(current_price)

    # Retrieve all options chains for the ticker
    # yahoo_fin provides a list of expiration dates:
    expiration_dates = si.get_expiration_dates(ticker)

    # Let's assume the nearest Friday is the first date in the list:
    next_friday = expiration_dates[0]

    # Get the option chain for that date
    option_chain = si.get_options_chain(ticker, next_friday)
    calls = option_chain['calls']
    puts = option_chain['puts']

    # Filter for ±20% around the current price
    lower_strike = 0.8 * current_price
    upper_strike = 1.2 * current_price

    calls_filtered = calls[(calls['Strike'] >= lower_strike) & (calls['Strike'] <= upper_strike)]
    puts_filtered  = puts[(puts['Strike']  >= lower_strike) & (puts['Strike']  <= upper_strike)]

    return calls_filtered, puts_filtered

# Example usage
if __name__ == "__main__":
    # my_tickers = ["NVDA", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "TSM", "LLY"]
    my_tickers = ["NVDA"]
    for t in my_tickers:
        try:
            calls, puts = get_eod_options_yahoo_fin(t)
            logger.info(f"---- {t} ----")
            logger.info("Calls:")
            logger.info(calls.head())
            logger.info("\nPuts:")
            logger.info(puts.head())
        except Exception as e:
            logger.info(f"Error fetching data for {t}: {e}")
