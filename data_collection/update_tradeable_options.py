import os
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
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

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Database configuration - set these as environment variables in your production environment
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "<user>")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")

db_params = {
    'host': DB_HOST,
    'database': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD
}


def check_table_exists(cursor, table_name):
    """Check if the specified table exists in the database."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

def create_tradeable_options_table(cursor):
    """Create the tradeable_options table if it doesn't exist."""
    cursor.execute("""
        CREATE TABLE public.tradeable_options (
            collateral DECIMAL,
            income DECIMAL,
            return_pct DECIMAL,
            contractid VARCHAR(255) PRIMARY KEY,
            symbol VARCHAR(255),
            expiration DATE,
            strike DECIMAL,
            price DECIMAL,
            type VARCHAR(10),
            last DECIMAL,
            mark DECIMAL,
            bid DECIMAL,
            bid_size INTEGER,
            ask DECIMAL,
            ask_size INTEGER,
            volume INTEGER,
            open_interest INTEGER,
            date DATE,
            implied_volatility DECIMAL,
            delta DECIMAL,
            gamma DECIMAL,
            theta DECIMAL,
            vega DECIMAL,
            rho DECIMAL
        );
    """)
    logger.info("Created tradeable_options table")

def delete_tradeable_options_rows(cursor):
    """Delete all rows from the tradeable_options table."""
    cursor.execute("DELETE FROM public.tradeable_options;")
    logger.info("Deleted all rows from tradeable_options table")
    
def connect_to_db(db_params):
    """Connect to the PostgreSQL database and return the connection and cursor."""
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    return conn, cursor
def close_db_connection(conn, cursor):
    """Close the database connection and cursor."""
    if cursor:
        cursor.close()
    if conn:
        conn.close()

def upsert_tradeable_options(cursor, conn):
    """
    Upsert data into tradeable_options table based on a SELECT query from yahoo_finance_options.
    Creates the table if it doesn't exist.
    """
    try:
        
        # The SELECT query to fetch data
        select_query = """
            SELECT 
                strike * 100 as collateral, 
                bid * 100 as income, 
                bid/strike * 100 as return_pct,
                contractid,
                symbol, 
                expiration, 
                strike, 
                stcks.price as price,
                type, 
                last, 
                mark, 
                bid, 
                bid_size, 
                ask, 
                ask_size, 
                opt.volume, 
                open_interest,
                date, 
                implied_volatility, 
                delta, 
                gamma, 
                theta, 
                vega, 
                rho
            FROM public.yahoo_finance_options opt
            LEFT JOIN public.stock_quotes stcks ON opt.symbol = stcks.ticker
            WHERE date = (
                SELECT MAX(date) FROM public.yahoo_finance_options
            )
            AND stcks.quote_date = (
                SELECT MAX(quote_date) FROM public.stock_quotes
            )
            AND type = 'put'
            AND strike <= stcks.price
            and strike/price < 0.9
            and (bid/strike * 100) > 2
            ORDER BY return_pct DESC
        """
        
        # Execute the SELECT query
        cursor.execute(select_query)
        results = cursor.fetchall()
        
        if not results:
            logger.info("No matching options found to upsert")
            return 0
        
        # Column names for the INSERT statement
        columns = [
            "collateral", "income", "return_pct", "contractid", "symbol", 
            "expiration", "strike", "price", "type", "last", "mark", "bid", "bid_size", 
            "ask", "ask_size", "volume", "open_interest", "date", 
            "implied_volatility", "delta", "gamma", "theta", "vega", "rho"
        ]
        
        # Prepare the UPSERT query
        upsert_query = sql.SQL("""
            INSERT INTO public.tradeable_options ({})
            VALUES %s
            ON CONFLICT (contractid)
            DO UPDATE SET
                collateral = EXCLUDED.collateral,
                income = EXCLUDED.income,
                return_pct = EXCLUDED.return_pct,
                symbol = EXCLUDED.symbol,
                expiration = EXCLUDED.expiration,
                strike = EXCLUDED.strike,
                price = EXCLUDED.price,
                type = EXCLUDED.type,
                last = EXCLUDED.last,
                mark = EXCLUDED.mark,
                bid = EXCLUDED.bid,
                bid_size = EXCLUDED.bid_size,
                ask = EXCLUDED.ask,
                ask_size = EXCLUDED.ask_size,
                volume = EXCLUDED.volume,
                open_interest = EXCLUDED.open_interest,
                date = EXCLUDED.date,
                implied_volatility = EXCLUDED.implied_volatility,
                delta = EXCLUDED.delta,
                gamma = EXCLUDED.gamma,
                theta = EXCLUDED.theta,
                vega = EXCLUDED.vega,
                rho = EXCLUDED.rho
        """).format(sql.SQL(', ').join(map(sql.Identifier, columns)))
        
        # Execute the upsert
        execute_values(cursor, upsert_query, results)
        
        # Commit the transaction
        conn.commit()
        
        row_count = len(results)
        logger.info(f"Successfully upserted {row_count} rows into tradeable_options")
        return row_count
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.info(f"Error upserting data: {e}")
        raise
        
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    
    # Run the upsert operation
    conn, cursor = connect_to_db(db_params)
    if not conn:
        logger.info("Failed to connect to the database")
        exit(1)
    # Check if table exists, create if not
    if not check_table_exists(cursor, "tradeable_options"):
        create_tradeable_options_table(cursor)
    delete_tradeable_options_rows(cursor)
    upsert_tradeable_options(cursor, conn)
    close_db_connection(conn, cursor)
