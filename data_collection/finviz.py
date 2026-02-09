import os
import time
import logging
import random
from datetime import datetime
import pytz
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/finviz_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Storage backend configuration: "supabase" (default) or "postgres"
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "supabase")

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Local PostgreSQL configuration (used when STORAGE_BACKEND=postgres)
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "<user>")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")

# Conditional imports based on backend
if STORAGE_BACKEND == "postgres":
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import execute_values
else:
    from supabase import create_client, Client

# Finviz configuration
BASE_URL = "https://finviz.com/screener.ashx"

# List of possible user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
]

def get_random_user_agent():
    """Get a random user agent from the list to avoid detection."""
    return random.choice(USER_AGENTS)

def get_headers():
    """Get headers for HTTP requests with a random user agent."""
    return {
        "User-Agent": get_random_user_agent(),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://finviz.com/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

def get_supabase_client() -> "Client":
    """Get a Supabase client instance."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_db_connection():
    """Establish a connection to the PostgreSQL database (only used when STORAGE_BACKEND=postgres)."""
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
    """Create the stock_quotes table if it doesn't exist (only used when STORAGE_BACKEND=postgres)."""
    try:
        with conn.cursor() as cur:
            # Create table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_quotes (
                    ticker VARCHAR(20) NOT NULL,
                    quote_date DATE NOT NULL,
                    quote_time TIME NOT NULL,
                    price NUMERIC(10, 2),
                    change_percent NUMERIC(6, 2),
                    volume BIGINT,
                    relative_volume NUMERIC(5, 2),
                    market_cap NUMERIC(20, 2),
                    pe_ratio NUMERIC(10, 2),
                    eps NUMERIC(10, 2),
                    dividend_yield NUMERIC(6, 2),
                    sector VARCHAR(100),
                    industry VARCHAR(100),
                    has_options BOOLEAN DEFAULT TRUE,
                    rsi NUMERIC(6, 2),
                    sma50 NUMERIC(10, 2),
                    sma200 NUMERIC(10, 2),
                    distance_from_support NUMERIC(8, 2),
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ticker, quote_date)
                );

                CREATE INDEX IF NOT EXISTS idx_stock_quotes_ticker ON stock_quotes (ticker);
                CREATE INDEX IF NOT EXISTS idx_stock_quotes_date ON stock_quotes (quote_date);
            """)

            # Add new columns if they don't exist (for existing tables)
            for column, col_type in [
                ('rsi', 'NUMERIC(6, 2)'),
                ('sma50', 'NUMERIC(10, 2)'),
                ('sma200', 'NUMERIC(10, 2)'),
                ('distance_from_support', 'NUMERIC(8, 2)')
            ]:
                cur.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                      WHERE table_name = 'stock_quotes' AND column_name = '{column}') THEN
                            ALTER TABLE stock_quotes ADD COLUMN {column} {col_type};
                        END IF;
                    END $$;
                """)
            
            # Check if table exists with old primary key (3 columns) and migrate it
            cur.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'stock_quotes' 
                AND constraint_type = 'PRIMARY KEY'
            """)
            pk_result = cur.fetchone()
            
            if pk_result:
                pk_constraint_name = pk_result[0]
                # Check column count in the primary key
                cur.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.key_column_usage
                    WHERE table_name = 'stock_quotes'
                    AND constraint_name = %s
                """, (pk_constraint_name,))
                pk_column_count = cur.fetchone()[0]
                
                if pk_column_count == 3:
                    # Migrate: drop old primary key and create new one
                    logger.info("Migrating primary key from (ticker, quote_date, quote_time) to (ticker, quote_date)")
                    cur.execute(f"ALTER TABLE stock_quotes DROP CONSTRAINT {pk_constraint_name}")
                    cur.execute("ALTER TABLE stock_quotes ADD PRIMARY KEY (ticker, quote_date)")
            
            conn.commit()
            logger.info("Table stock_quotes created or already exists")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating table: {str(e)}")
        raise

def build_finviz_url(view="111", filters=None, page_offset=1):
    """
    Build a Finviz screener URL with the given parameters.
    
    Args:
        view: View code (e.g., "111" for overview)
        filters: List of filters to apply (e.g., ["cap_mega", "sh_opt_option"])
        page_offset: Page offset (1-based index, so first page starts at offset 1)
    
    Returns:
        URL string for the Finviz screener
    """
    params = {"v": view}
    
    if filters:
        params["f"] = ",".join(filters)
    
    if page_offset > 1:
        params["r"] = str(page_offset)
    
    return f"{BASE_URL}?{urlencode(params)}"

def fetch_finviz_page(url, max_retries=3, retry_delay=5):
    """
    Fetch the HTML content of a Finviz page with retries and error handling.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        HTML text of the page or None if failed
    """
    logger.info(f"Fetching page: {url}")
    
    for attempt in range(max_retries):
        try:
            # Get fresh headers with a random user agent for each attempt
            # headers = get_headers() #### TEMP FIX. NEED TO FIX THIS
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0"
            }
            
            # Add a random delay to avoid detection
            time.sleep(random.uniform(1.0, 3.0))
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=15)
            
            # Check if we got a successful response
            if response.status_code == 200:
                logger.info(f"Successfully fetched page, length: {len(response.text)}")
                return response.text
            
            # If we got here, something went wrong
            logger.warning(f"Failed to fetch page on attempt {attempt+1}/{max_retries}. Status code: {response.status_code}")
            
            # Wait before retrying
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {delay} seconds before retrying...")
                time.sleep(delay)
        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request exception on attempt {attempt+1}/{max_retries}: {str(e)}")
            
            # Wait before retrying
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {delay} seconds before retrying...")
                time.sleep(delay)
    
    logger.error(f"Failed to fetch page after {max_retries} attempts: {url}")
    return None

def find_screener_table(soup):
    # Find the main table containing stock data
    tables = soup.find_all('table')
    logger.info(f"Found {len(tables)} tables in the document")

    for table in tables:
        class_attr = table.get('class')
        class_name = ' '.join(class_attr) if class_attr else "No class"
        if class_name.__contains__("styled-table-new"):
            return table

    return None

def extract_stock_data_from_html(html_content):
    """
    Extract stock data from the HTML content.
    
    Args:
        html_content: HTML content of the Finviz screener page
    
    Returns:
        List of dictionaries containing stock data and URL for next page (if any)
    """
    if not html_content:
        return [], None
    
    stocks_data = []
    next_page_url = None
    
    try:
        # Parse HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get the current time in Eastern Time (market time)
        et_timezone = pytz.timezone('America/New_York')
        current_time = datetime.now(et_timezone)
        quote_date = current_time.date()
        quote_time = current_time.time()
        
        # The key is to find the table inside the screener-table section
        # First locate the screener-table element
        table = find_screener_table(soup)
 
        if not table:
            logger.error("Could not find any suitable table with stock data")
            return [], None
        
        # Extract header row to understand the column structure
        header_row = table.find('thead')
        if header_row:
            headers = header_row.find_all('th')
            header_texts = [h.text.strip() for h in headers]
            logger.info(f"Found headers: {header_texts}")
        
        # Extract the data rows (skip header row if present)
        data_rows = table.find_all('tr', class_='is-hoverable')
        
        if not data_rows:
            # Try without the class filter
            data_rows = table.find_all('tr')
            # Skip the header row if it was included
            if header_row:
                data_rows = data_rows[1:]
        
        logger.info(f"Found {len(data_rows)} data rows")
        
        if not data_rows:
            logger.warning("No data rows found in the table")
            return [], None
        
        # Process each row to extract stock data
        for row in data_rows:
            cells = row.find_all('td')
            
            # Skip if too few cells
            if len(cells) < 9:  # Minimum number of cells we need
                continue
            
            try:
                # Extract ticker (typically in the second cell)
                ticker_cell = cells[1]
                ticker_link = ticker_cell.find('a', class_='screener-link-primary')
                
                if not ticker_link:
                    # Try other anchor tags in the cell
                    ticker_link = ticker_cell.find('a')
                
                if not ticker_link:
                    logger.warning("Could not extract ticker from row, skipping")
                    continue
                
                ticker = ticker_link.text.strip()
                
                # Extract other data based on column positions in the typical Finviz overview layout
                # Normally cells are: No., Ticker, Company, Sector, Industry, Country, Market Cap, P/E, Price, Change, Volume
                
                company = cells[2].text.strip() if len(cells) > 2 else None
                sector = cells[3].text.strip() if len(cells) > 3 else None
                industry = cells[4].text.strip() if len(cells) > 4 else None
                country = cells[5].text.strip() if len(cells) > 5 else None
                
                # Extract numeric values
                try:
                    market_cap_text = cells[6].text.strip() if len(cells) > 6 else None
                    market_cap = parse_market_cap(market_cap_text)
                except:
                    market_cap = None
                
                try:
                    pe_text = cells[7].text.strip() if len(cells) > 7 else None
                    pe_ratio = float(pe_text.replace(',', '')) if pe_text and pe_text != '-' else None
                except:
                    pe_ratio = None
                
                try:
                    price_text = cells[8].text.strip() if len(cells) > 8 else None
                    # Remove color tags or other elements if present
                    if price_text:
                        price_text = re.sub(r'[^\d.,]', '', price_text)
                    price = float(price_text.replace(',', '')) if price_text and price_text != '-' else None
                except:
                    price = None
                
                try:
                    change_text = cells[9].text.strip() if len(cells) > 9 else None
                    # Remove % and color tags or other elements if present
                    if change_text:
                        change_text = re.sub(r'[^\d.,\-]', '', change_text)
                        change_text = change_text.replace('%', '')
                    change_percent = float(change_text) if change_text and change_text != '-' else None
                except:
                    change_percent = None
                
                try:
                    volume_text = cells[10].text.strip() if len(cells) > 10 else None
                    volume = parse_volume(volume_text)
                except:
                    volume = None
                
                # Create stock data entry
                stock_data = {
                    'ticker': ticker,
                    'quote_date': quote_date,
                    'quote_time': quote_time,
                    'price': price,
                    'change_percent': change_percent,
                    'volume': volume,
                    'relative_volume': None,  # Not available in basic view
                    'market_cap': market_cap,
                    'pe_ratio': pe_ratio,
                    'eps': None,  # Not available in basic view
                    'dividend_yield': None,  # Not available in basic view
                    'sector': sector,
                    'industry': industry,
                    'has_options': True,  # We're filtering for stocks with options
                    'rsi': None,  # Will be fetched from technical view
                    'sma50': None,  # Will be fetched from technical view
                    'sma200': None,  # Will be fetched from technical view
                    'distance_from_support': None,  # Will be calculated or fetched
                }

                stocks_data.append(stock_data)
                
            except Exception as e:
                logger.warning(f"Error processing row: {str(e)}")
                continue
        
        # Check for next page URL
        try:
            pagination_td = soup.find('td', id='screener_pagination')

            if pagination_td:
                next_link = None
                links = pagination_td.find_all('a')
                for link in links:
                    if link.get('class').__contains__('is-next'):
                        next_link = link
                        break  # Stop searching once "next" is found

                if next_link:
                    logger.info(f"Next Link HREF: {next_link.get('href')}")
                    next_page_url = "https://finviz.com/" + next_link.get('href')
                else:
                    logger.info("No 'next' link found.")
            else:
                logger.warning("Pagination element not found.")
        except Exception as e:
            logger.warning(f"Error finding next page URL: {str(e)}")
        
        logger.info(f"Extracted data for {len(stocks_data)} stocks")
        return stocks_data, next_page_url
    
    except Exception as e:
        logger.error(f"Error extracting stock data from HTML: {str(e)}")
        return [], None

def parse_market_cap(market_cap_text):
    """
    Parse market cap text into a numeric value.
    Example: "12.5B" -> 12500000000
    """
    try:
        if not market_cap_text or market_cap_text == '-':
            return None
            
        # Remove any non-numeric characters except decimal point and BKMT
        market_cap_text = market_cap_text.strip().upper()
        
        # Extract the numeric part and the suffix
        match = re.match(r'([\d.]+)([BKMT])?', market_cap_text)
        if not match:
            return None
            
        value, suffix = match.groups()
        value = float(value)
        
        # Convert based on suffix
        if suffix == 'B':  # Billion
            return value * 1_000_000_000
        elif suffix == 'M':  # Million
            return value * 1_000_000
        elif suffix == 'K':  # Thousand
            return value * 1_000
        elif suffix == 'T':  # Trillion
            return value * 1_000_000_000_000
        else:
            return value
    except Exception as e:
        logger.warning(f"Error parsing market cap '{market_cap_text}': {str(e)}")
        return None

def parse_volume(volume_text):
    """
    Parse volume text into a numeric value.
    Example: "1.2M" -> 1200000
    """
    try:
        if not volume_text or volume_text == '-':
            return None
            
        # Remove any non-numeric characters except decimal point and BKMT
        volume_text = volume_text.strip().upper().replace(',', '')
        
        # Extract the numeric part and the suffix
        match = re.match(r'([\d.]+)([BKMT])?', volume_text)
        if not match:
            return None
            
        value, suffix = match.groups()
        value = float(value)
        
        # Convert based on suffix
        if suffix == 'B':  # Billion
            return int(value * 1_000_000_000)
        elif suffix == 'M':  # Million
            return int(value * 1_000_000)
        elif suffix == 'K':  # Thousand
            return int(value * 1_000)
        elif suffix == 'T':  # Trillion
            return int(value * 1_000_000_000_000)
        else:
            return int(value)
    except Exception as e:
        logger.warning(f"Error parsing volume '{volume_text}': {str(e)}")
        return None

def upsert_stock_data_supabase(supabase_client, stock_data):
    """
    Upsert stock data into Supabase.
    """
    if not stock_data:
        logger.warning("No stock data to upsert")
        return 0

    try:
        # Prepare records for Supabase upsert
        records = []
        for data in stock_data:
            record = {
                'ticker': data['ticker'],
                'quote_date': str(data['quote_date']),
                'quote_time': str(data['quote_time']),
                'price': float(data['price']) if data['price'] is not None else None,
                'change_percent': float(data['change_percent']) if data['change_percent'] is not None else None,
                'volume': int(data['volume']) if data['volume'] is not None else None,
                'relative_volume': float(data['relative_volume']) if data['relative_volume'] is not None else None,
                'market_cap': float(data['market_cap']) if data['market_cap'] is not None else None,
                'pe_ratio': float(data['pe_ratio']) if data['pe_ratio'] is not None else None,
                'eps': float(data['eps']) if data['eps'] is not None else None,
                'dividend_yield': float(data['dividend_yield']) if data['dividend_yield'] is not None else None,
                'sector': data['sector'],
                'industry': data['industry'],
                'has_options': data['has_options'],
                'rsi': float(data['rsi']) if data.get('rsi') is not None else None,
                'sma50': float(data['sma50']) if data.get('sma50') is not None else None,
                'sma200': float(data['sma200']) if data.get('sma200') is not None else None,
                'distance_from_support': float(data['distance_from_support']) if data.get('distance_from_support') is not None else None,
                'last_updated': datetime.now(pytz.utc).isoformat(),
            }
            records.append(record)

        # Upsert in batches (Supabase has limits on request size)
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            supabase_client.table('stock_quotes').upsert(
                batch,
                on_conflict='ticker,quote_date'
            ).execute()

        logger.info(f"Successfully upserted data for {len(stock_data)} stocks to Supabase")
        return len(stock_data)

    except Exception as e:
        logger.error(f"Error upserting stock data to Supabase: {str(e)}")
        raise


def upsert_stock_data_postgres(conn, stock_data):
    """
    Upsert stock data into local PostgreSQL database.
    """
    if not stock_data:
        logger.warning("No stock data to upsert")
        return 0

    try:
        with conn.cursor() as cur:
            # Define the columns we want to insert/update
            columns = [
                'ticker', 'quote_date', 'quote_time', 'price', 'change_percent',
                'volume', 'relative_volume', 'market_cap', 'pe_ratio',
                'eps', 'dividend_yield', 'sector', 'industry', 'has_options',
                'rsi', 'sma50', 'sma200', 'distance_from_support', 'last_updated'
            ]

            # Prepare values in the format expected by execute_values
            values = []
            for data in stock_data:
                row = (
                    data['ticker'],
                    data['quote_date'],
                    data['quote_time'],
                    data['price'],
                    data['change_percent'],
                    data['volume'],
                    data['relative_volume'],
                    data['market_cap'],
                    data['pe_ratio'],
                    data['eps'],
                    data['dividend_yield'],
                    data['sector'],
                    data['industry'],
                    data['has_options'],
                    data.get('rsi'),
                    data.get('sma50'),
                    data.get('sma200'),
                    data.get('distance_from_support'),
                    datetime.now(pytz.utc)
                )
                values.append(row)

            # Build the SQL query for upserting data
            insert_stmt = sql.SQL("""
                INSERT INTO stock_quotes ({})
                VALUES %s
                ON CONFLICT (ticker, quote_date) DO UPDATE SET
                    quote_time = EXCLUDED.quote_time,
                    price = EXCLUDED.price,
                    change_percent = EXCLUDED.change_percent,
                    volume = EXCLUDED.volume,
                    relative_volume = EXCLUDED.relative_volume,
                    market_cap = EXCLUDED.market_cap,
                    pe_ratio = EXCLUDED.pe_ratio,
                    eps = EXCLUDED.eps,
                    dividend_yield = EXCLUDED.dividend_yield,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    has_options = EXCLUDED.has_options,
                    rsi = EXCLUDED.rsi,
                    sma50 = EXCLUDED.sma50,
                    sma200 = EXCLUDED.sma200,
                    distance_from_support = EXCLUDED.distance_from_support,
                    last_updated = EXCLUDED.last_updated
            """).format(
                sql.SQL(', ').join(map(sql.Identifier, columns))
            )

            # Execute the query
            execute_values(cur, insert_stmt, values)
            conn.commit()

            logger.info(f"Successfully upserted data for {len(stock_data)} stocks to PostgreSQL")
            return len(stock_data)

    except Exception as e:
        conn.rollback()
        logger.error(f"Error upserting stock data to PostgreSQL: {str(e)}")
        raise


def upsert_stock_data(db_client, stock_data):
    """
    Upsert stock data into the configured database backend.
    """
    if STORAGE_BACKEND == "postgres":
        return upsert_stock_data_postgres(db_client, stock_data)
    else:
        return upsert_stock_data_supabase(db_client, stock_data)

def fetch_technical_data(ticker):
    """
    Fetch technical indicators (RSI, SMA50, SMA200) for a specific ticker from Finviz.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with technical indicators or None if failed
    """
    url = f"https://finviz.com/quote.ashx?t={ticker}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0"
        }
        time.sleep(random.uniform(0.5, 1.5))  # Rate limiting
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            logger.warning(f"Failed to fetch technical data for {ticker}: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the snapshot table with technical data
        technical_data = {
            'rsi': None,
            'sma50': None,
            'sma200': None,
            'distance_from_support': None
        }

        # Look for the data table rows
        table = soup.find('table', class_='snapshot-table2')
        if not table:
            return technical_data

        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            for i, cell in enumerate(cells):
                text = cell.text.strip()
                if text == 'RSI (14)' and i + 1 < len(cells):
                    try:
                        technical_data['rsi'] = float(cells[i + 1].text.strip())
                    except (ValueError, TypeError):
                        pass
                elif text == 'SMA50' and i + 1 < len(cells):
                    try:
                        # SMA50 is shown as percentage from current price
                        sma_text = cells[i + 1].text.strip().replace('%', '')
                        technical_data['sma50'] = float(sma_text)
                    except (ValueError, TypeError):
                        pass
                elif text == 'SMA200' and i + 1 < len(cells):
                    try:
                        # SMA200 is shown as percentage from current price
                        sma_text = cells[i + 1].text.strip().replace('%', '')
                        technical_data['sma200'] = float(sma_text)
                    except (ValueError, TypeError):
                        pass

        return technical_data

    except Exception as e:
        logger.warning(f"Error fetching technical data for {ticker}: {str(e)}")
        return None


def enrich_with_technical_data(stocks_data, max_tickers=50):
    """
    Enrich stock data with technical indicators.
    Limited to max_tickers to avoid rate limiting.

    Args:
        stocks_data: List of stock data dictionaries
        max_tickers: Maximum number of tickers to fetch technical data for

    Returns:
        Updated stocks_data with technical indicators
    """
    for i, stock in enumerate(stocks_data[:max_tickers]):
        ticker = stock['ticker']
        logger.info(f"Fetching technical data for {ticker} ({i+1}/{min(len(stocks_data), max_tickers)})")

        technical_data = fetch_technical_data(ticker)
        if technical_data:
            stock.update(technical_data)

    return stocks_data


def scrape_finviz_stocks_with_options():
    """
    Scrape stocks with options from Finviz screener.
    """
    try:
        # Get database client based on configured backend
        if STORAGE_BACKEND == "postgres":
            db_client = get_db_connection()
            create_table_if_not_exists(db_client)
            logger.info("Using local PostgreSQL backend")
        else:
            db_client = get_supabase_client()
            logger.info("Using Supabase backend")

        # Include filters for Large Cap,
        # url = "https://finviz.com/screener.ashx?v=111&f=cap_largeover%2Cfa_eps5years_o10%2Cfa_grossmargin_o25%2Cfa_sales5years_o10%2Csh_opt_option%2Cta_sma200_pa&ft=3&o=-perf3y"
        # adding filter for over 30% above SMA200.
        url = "https://finviz.com/screener.ashx?v=171&f=cap_largeover%2Cfa_eps5years_o10%2Cfa_grossmargin_o25%2Cfa_sales5years_o10%2Csh_opt_option%2Cta_sma200_pa30&ft=3&o=-perf3y"

        page_count = 1
        total_stocks = 0
        max_pages = 30

        while url and page_count <= max_pages:
            logger.info(f"Scraping page {page_count}: {url}")

            # Fetch the page content
            html_content = fetch_finviz_page(url)

            if not html_content:
                logger.error(f"Failed to fetch page {page_count}")
                break

            # Extract stock data from the page
            stocks_data, next_page_url = extract_stock_data_from_html(html_content)

            if stocks_data:
                # Upsert data to database
                inserted_count = upsert_stock_data(db_client, stocks_data)
                total_stocks += inserted_count
                logger.info(f"Added {inserted_count} stocks from page {page_count} (total: {total_stocks})")
            else:
                logger.warning(f"No stocks found on page {page_count}")

            # Move to next page if available
            url = next_page_url
            page_count += 1

            # Add a delay between requests
            if url:
                delay = random.uniform(2.0, 4.0)
                logger.info(f"Waiting {delay:.2f} seconds before next page...")
                time.sleep(delay)

        logger.info(f"Scraping completed. Total stocks: {total_stocks}")

        # Close the database connection (only for PostgreSQL)
        if STORAGE_BACKEND == "postgres":
            db_client.close()

        return total_stocks

    except Exception as e:
        logger.error(f"Error in scrape_finviz_stocks_with_options: {str(e)}")
        return 0

def is_market_open():
    """
    Check if the US stock market is currently open.
    Returns True if the market is open, False otherwise.
    """
    ny_time = datetime.now(pytz.timezone('America/New_York'))
    
    # Market is closed on weekends
    if ny_time.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
        return False
    
    # Regular market hours: 9:30 AM to 4:00 PM Eastern Time
    market_open = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = ny_time.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= ny_time <= market_close

def main():
    """Main function to run the stock data collection."""
    try:
        # Check if market is open (optional - comment out to run anytime)
        # if not is_market_open():
        #     logger.info("Market is closed. Exiting.")
        #     return
        
        # Scrape Finviz stock data
        stock_count = scrape_finviz_stocks_with_options()
        
        logger.info(f"Stock data collection completed successfully. Total stocks: {stock_count}")
    
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    main()
