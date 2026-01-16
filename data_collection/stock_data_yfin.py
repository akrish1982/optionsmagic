import os
import time
import logging
from datetime import datetime
import pytz
import pandas as pd
import yfinance as yf
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_collector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database configuration - set these as environment variables in your production environment
DB_NAME = os.environ.get("DB_NAME", "<user>")
DB_USER = os.environ.get("DB_USER", "<user>")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")

def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def create_table_if_not_exists(conn):
    """Create the stock_quotes table if it doesn't exist."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_quotes (
                    ticker VARCHAR(20) NOT NULL,
                    quote_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
                    price NUMERIC(10, 2),
                    volume BIGINT,
                    open_price NUMERIC(10, 2),
                    high_price NUMERIC(10, 2),
                    low_price NUMERIC(10, 2),
                    prev_close NUMERIC(10, 2),
                    market_cap NUMERIC(20, 2),
                    pe_ratio NUMERIC(10, 2),
                    dividend_yield NUMERIC(10, 4),
                    has_options BOOLEAN,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ticker, quote_datetime)
                );
                
                CREATE INDEX IF NOT EXISTS idx_stock_quotes_ticker ON stock_quotes (ticker);
                CREATE INDEX IF NOT EXISTS idx_stock_quotes_datetime ON stock_quotes (quote_datetime);
            """)
            conn.commit()
            logger.info("Table stock_quotes created or already exists")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating table: {str(e)}")
        raise

def get_us_tickers_with_options():
    """
    Get a list of US stock tickers that have options enabled.
    This is a simplified version - in production, you might want to use a more
    robust source or API.
    """
    try:
        return ["AAPL", "MSFT", "AMZN", "GOOG", "META", "TSLA", "NVDA", "AMD"]
        ### TEMP - NEEDS TO BE REPLACED AS BELOW
        # First, get a list of all US stock tickers
        # For demonstration, let's use a simple approach using pandas_datareader
        # In production, you might want to use a more robust source
        
        # Method 1: Using yfinance to get S&P 500 stocks (as a starting point)
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        tickers = sp500['Symbol'].tolist()
        
        # For a more comprehensive list, you might want to use other sources
        # such as NASDAQ's or NYSE's official lists
        
        # Filter tickers that have options
        tickers_with_options = []
        
        # Process in smaller batches to avoid rate limiting
        batch_size = 20
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]
            for ticker in batch:
                try:
                    stock = yf.Ticker(ticker)
                    # Attempt to fetch options expiration dates
                    # If options are available, this will return a list of dates
                    options = stock.options
                    
                    if options and len(options) > 0:
                        tickers_with_options.append(ticker)
                        logger.info(f"Ticker {ticker} has options")
                    else:
                        logger.info(f"Ticker {ticker} does not have options")
                except Exception as e:
                    logger.warning(f"Error checking options for {ticker}: {str(e)}")
                
                # Avoid hitting API limits
                time.sleep(0.5)
        
        logger.info(f"Found {len(tickers_with_options)} US stocks with options")
        return tickers_with_options
    
    except Exception as e:
        logger.error(f"Error fetching tickers with options: {str(e)}")
        # In case of error, return a small list of well-known stocks that likely have options
        return ["AAPL", "MSFT", "AMZN", "GOOG", "META", "TSLA", "NVDA", "AMD"]

def fetch_stock_data(tickers):
    """
    Fetch basic stock information for the given tickers.
    Returns a list of dictionaries with stock data.
    """
    stock_data = []
    current_time = datetime.now(pytz.timezone('America/New_York'))
    
    # Process tickers in smaller batches to avoid rate limiting
    batch_size = 20
    
    for i in range(0, len(tickers), batch_size):
        batch_tickers = tickers[i:i+batch_size]
        try:
            # Use yfinance to get stock data for the batch
            batch_data = yf.download(
                tickers=batch_tickers,
                period="5d",
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                prepost=True,
                threads=True,
                proxy=None
            )
            
            # Handle case when only one ticker is in the batch
            if len(batch_tickers) == 1:
                ticker = batch_tickers[0]
                if not batch_data.empty:
                    latest = batch_data.iloc[-1]
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    stock_data.append({
                        'ticker': ticker,
                        'quote_datetime': current_time,
                        'price': latest['Close'] if 'Close' in latest else None,
                        'volume': latest['Volume'] if 'Volume' in latest else None,
                        'open_price': latest['Open'] if 'Open' in latest else None,
                        'high_price': latest['High'] if 'High' in latest else None,
                        'low_price': latest['Low'] if 'Low' in latest else None,
                        'prev_close': info.get('previousClose'),
                        'market_cap': info.get('marketCap'),
                        'pe_ratio': info.get('trailingPE'),
                        'dividend_yield': info.get('dividendYield'),
                        'has_options': True  # We already filtered for stocks with options
                    })
            else:
                # Handle multiple tickers
                for ticker in batch_tickers:
                    if ticker in batch_data.columns.levels[0]:
                        ticker_data = batch_data[ticker]
                        if not ticker_data.empty:
                            latest = ticker_data.iloc[-1]
                            stock = yf.Ticker(ticker)
                            info = stock.info
                            
                            stock_data.append({
                                'ticker': ticker,
                                'quote_datetime': current_time,
                                'price': latest['Close'] if 'Close' in latest.index else None,
                                'volume': latest['Volume'] if 'Volume' in latest.index else None,
                                'open_price': latest['Open'] if 'Open' in latest.index else None,
                                'high_price': latest['High'] if 'High' in latest.index else None,
                                'low_price': latest['Low'] if 'Low' in latest.index else None,
                                'prev_close': info.get('previousClose'),
                                'market_cap': info.get('marketCap'),
                                'pe_ratio': info.get('trailingPE'),
                                'dividend_yield': info.get('dividendYield'),
                                'has_options': True  # We already filtered for stocks with options
                            })
            
            # Avoid hitting API limits
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error fetching data for batch {batch_tickers}: {str(e)}")
    
    logger.info(f"Fetched data for {len(stock_data)} stocks")
    return stock_data

def upsert_stock_data(conn, stock_data):
    """
    Upsert stock data into the database.
    """
    if not stock_data:
        logger.warning("No stock data to upsert")
        return
    
    try:
        with conn.cursor() as cur:
            # Define the columns we want to insert/update
            columns = [
                'ticker', 'quote_datetime', 'price', 'volume', 'open_price',
                'high_price', 'low_price', 'prev_close', 'market_cap',
                'pe_ratio', 'dividend_yield', 'has_options', 'last_updated'
            ]
            
            # Prepare values in the format expected by execute_values
            values = [
                (
                    data['ticker'],
                    data['quote_datetime'],
                    data['price'],
                    data['volume'],
                    data['open_price'],
                    data['high_price'],
                    data['low_price'],
                    data['prev_close'],
                    data['market_cap'],
                    data['pe_ratio'],
                    data['dividend_yield'],
                    data['has_options'],
                    datetime.now(pytz.utc)
                )
                for data in stock_data
            ]
            
            # Build the SQL query for upserting data
            insert_stmt = sql.SQL("""
                INSERT INTO stock_quotes ({})
                VALUES %s
                ON CONFLICT (ticker, quote_datetime) DO UPDATE SET
                    price = EXCLUDED.price,
                    volume = EXCLUDED.volume,
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    prev_close = EXCLUDED.prev_close,
                    market_cap = EXCLUDED.market_cap,
                    pe_ratio = EXCLUDED.pe_ratio,
                    dividend_yield = EXCLUDED.dividend_yield,
                    has_options = EXCLUDED.has_options,
                    last_updated = EXCLUDED.last_updated
            """).format(
                sql.SQL(', ').join(map(sql.Identifier, columns))
            )
            
            # Execute the query
            execute_values(cur, insert_stmt, values)
            conn.commit()
            
            logger.info(f"Successfully upserted data for {len(stock_data)} stocks")
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error upserting stock data: {str(e)}")
        raise

def is_market_open():
    """
    Check if the US stock market is currently open.
    Returns True if the market is open, False otherwise.
    """
    ny_time = datetime.now(pytz.timezone('America/New_York'))
    
    # Market is closed on weekends
    if ny_time.weekday() >= 7:  # 5 is Saturday, 6 is Sunday
        ### TEMP - NEEDS TO BE REPLACED AS 5
        return False
    
    # Regular market hours: 9:30 AM to 4:00 PM Eastern Time
    market_open = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = ny_time.replace(hour=16, minute=30, second=0, microsecond=0)
    
    # Check for holidays (simplified - in production use a proper calendar library)
    # This is a simplified approach, consider using a library like pandas_market_calendars
    # for accurate holiday schedules
    
    return market_open <= ny_time <= market_close

def main():
    """Main function to run the stock data collection."""
    try:
        # Check if market is open
        if not is_market_open():
            logger.info("Market is closed. Exiting.")
            return
        
        # Get database connection
        conn = get_db_connection()
        
        # Create table if it doesn't exist
        create_table_if_not_exists(conn)
        
        # Get list of tickers with options
        tickers = get_us_tickers_with_options()
        
        # Fetch stock data
        stock_data = fetch_stock_data(tickers)
        
        # Upsert data into database
        upsert_stock_data(conn, stock_data)
        
        # Close database connection
        conn.close()
        
        logger.info("Stock data collection completed successfully")
    
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    main()