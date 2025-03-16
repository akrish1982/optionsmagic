import yfinance as yf

def get_eod_options_yfinance(ticker, next_friday_expiration=None):
    """
    Gets the option chain from Yahoo Finance, focuses on the calls/puts
    for the specified expiration date, and filters strikes around ±20% 
    of current price.
    """
    # Download ticker data
    stock = yf.Ticker(ticker)
    
    # Current stock price
    current_price = stock.history(period="5d")['Close'][-1]
    print(current_price)
    
    # If you don't specify an expiration, you can pull all available expirations, 
    # then pick the next Friday. Something like:
    if not next_friday_expiration:
        expirations = stock.options
        # Sort or figure out which one is the immediate next Friday
        # For demonstration, let's just take the first if we assume it's the nearest
        next_friday_expiration = expirations[0]
    
    # Get option chain for that expiration
    opt = stock.option_chain(next_friday_expiration)
    calls = opt.calls
    puts = opt.puts
    
    # Filter by ±20% strikes
    lower_strike = 0.8 * current_price
    upper_strike = 1.2 * current_price
    
    calls_filtered = calls[(calls['strike'] >= lower_strike) & (calls['strike'] <= upper_strike)]
    puts_filtered  = puts[(puts['strike']  >= lower_strike) & (puts['strike']  <= upper_strike)]
    
    return calls_filtered, puts_filtered
if __name__ == "__main__":
    # Example usage for multiple tickers
    # tickers = ["NVDA", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "TSM", "LLY"]
    tickers = ["NVDA"]
    for t in tickers:
        try:
            calls, puts = get_eod_options_yfinance(t)
            print(f"---- {t} ----")
            print("Calls:")
            print(calls.head())
            print("\nPuts:")
            print(puts.head())
        except Exception as e:
            print(f"Error fetching data for {t}: {e}")
