import os
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Database configuration - set these as environment variables in your production environment
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "ananth")
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
    print("Created tradeable_options table")

def upsert_tradeable_options(db_params):
    """
    Upsert data into tradeable_options table based on a SELECT query from yahoo_finance_options.
    Creates the table if it doesn't exist.
    """
    conn = None
    try:
        # Connect to the database
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Check if table exists, create if not
        if not check_table_exists(cursor, "tradeable_options"):
            create_tradeable_options_table(cursor)
        
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
            ORDER BY return_pct DESC
        """
        
        # Execute the SELECT query
        cursor.execute(select_query)
        results = cursor.fetchall()
        
        if not results:
            print("No matching options found to upsert")
            return 0
        
        # Column names for the INSERT statement
        columns = [
            "collateral", "income", "return_pct", "contractid", "symbol", 
            "expiration", "strike", "type", "last", "mark", "bid", "bid_size", 
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
        print(f"Successfully upserted {row_count} rows into tradeable_options")
        return row_count
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error upserting data: {e}")
        raise
        
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    
    # Run the upsert operation
    upsert_tradeable_options(db_params)
