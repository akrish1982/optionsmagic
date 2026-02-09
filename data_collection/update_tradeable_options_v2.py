"""
Update Tradeable Options - Supabase Version for Latest Code

Filters options from options_quotes table (TradeStation data) and generates 
tradeable_options summary.

Criteria:
- Put options only
- Strike <= current stock price  
- Strike/price < 0.9 (at least 10% OTM)
- Return > 2% (bid/strike * 100 > 2)

Usage:
    poetry run python data_collection/update_tradeable_options_v2.py
"""

import os
import logging
from datetime import date
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/tradeable.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

from supabase import create_client


def get_supabase_client():
    """Get Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def generate_tradeable_options(supabase):
    """
    Generate tradeable options by joining options_quotes with stock_quotes.
    Returns list of options that meet our criteria.
    """
    try:
        # Get latest dates
        logger.info("Getting latest data dates...")
        
        options_response = supabase.table('options_quotes').select('date').order('date', desc=True).limit(1).execute()
        if not options_response.data:
            logger.warning("No options data found")
            return []
        latest_options_date = options_response.data[0]['date']
        
        stock_response = supabase.table('stock_quotes').select('quote_date').order('quote_date', desc=True).limit(1).execute()
        if not stock_response.data:
            logger.warning("No stock quotes found")
            return []
        latest_stock_date = stock_response.data[0]['quote_date']
        
        logger.info(f"Latest options date: {latest_options_date}, Latest stock date: {latest_stock_date}")
        
        # Get all put options for latest date
        logger.info("Fetching put options data...")
        options = supabase.table('options_quotes').select('*').eq('date', latest_options_date).eq('type', 'put').execute()
        
        if not options.data:
            logger.warning("No put options found")
            return []
        
        logger.info(f"Found {len(options.data)} put options")
        
        # Get all stock prices for latest date
        logger.info("Fetching stock prices...")
        stocks = supabase.table('stock_quotes').select('ticker,price').eq('quote_date', latest_stock_date).execute()
        
        if not stocks.data:
            logger.warning("No stock prices found")
            return []
        
        # Create price lookup
        price_map = {row['ticker']: float(row['price']) for row in stocks.data if row.get('price')}
        logger.info(f"Found prices for {len(price_map)} stocks")
        
        # Filter and calculate
        tradeable = []
        for opt in options.data:
            symbol = opt.get('symbol')
            strike = opt.get('strike')
            bid = opt.get('bid')
            
            if not all([symbol, strike, bid]):
                continue
            
            # Get stock price
            price = price_map.get(symbol)
            if not price:
                continue
            
            try:
                strike = float(strike)
                bid = float(bid)
            except (ValueError, TypeError):
                continue
            
            # Apply filters
            if strike > price:  # Only puts below current price
                continue
            
            if strike / price >= 0.9:  # Must be at least 10% OTM
                continue
            
            return_pct = (bid / strike) * 100
            if return_pct <= 2:  # Must have at least 2% return
                continue
            
            # Calculate values
            collateral = strike * 100
            income = bid * 100
            
            # Build tradeable option record
            tradeable_opt = {
                'collateral': collateral,
                'income': income,
                'return_pct': return_pct,
                'contractid': opt['contractid'],
                'symbol': symbol,
                'expiration': opt['expiration'],
                'strike': strike,
                'price': price,
                'type': 'put',
                'last': opt.get('last'),
                'mark': opt.get('mark'),
                'bid': bid,
                'bid_size': opt.get('bid_size'),
                'ask': opt.get('ask'),
                'ask_size': opt.get('ask_size'),
                'volume': opt.get('volume'),
                'open_interest': opt.get('open_interest'),
                'date': opt['date'],
                'implied_volatility': opt.get('implied_volatility'),
                'delta': opt.get('delta'),
                'gamma': opt.get('gamma'),
                'theta': opt.get('theta'),
                'vega': opt.get('vega'),
                'rho': opt.get('rho')
            }
            
            tradeable.append(tradeable_opt)
        
        # Sort by return percentage descending
        tradeable.sort(key=lambda x: x['return_pct'], reverse=True)
        
        logger.info(f"Generated {len(tradeable)} tradeable options")
        return tradeable
        
    except Exception as e:
        logger.error(f"Error generating tradeable options: {e}", exc_info=True)
        raise


def upsert_tradeable_options(supabase, options):
    """Upsert tradeable options to Supabase."""
    if not options:
        logger.info("No options to upsert")
        return 0
    
    try:
        # Delete existing data first (truncate equivalent)
        logger.info("Clearing existing tradeable_options...")
        # Supabase doesn't support TRUNCATE via REST, so delete all
        try:
            supabase.table('tradeable_options').delete().neq('contractid', '').execute()
        except Exception as e:
            logger.warning(f"Could not clear table (may not exist yet): {e}")
        
        # Batch upsert
        batch_size = 100
        total = 0
        
        for i in range(0, len(options), batch_size):
            batch = options[i:i + batch_size]
            supabase.table('tradeable_options').upsert(
                batch,
                on_conflict='contractid'
            ).execute()
            total += len(batch)
            logger.info(f"Upserted batch {i // batch_size + 1}: {len(batch)} options")
        
        logger.info(f"✅ Successfully upserted {total} tradeable options")
        return total
        
    except Exception as e:
        logger.error(f"Error upserting tradeable options: {e}", exc_info=True)
        raise


def main():
    """Main execution."""
    logger.info("🚀 Starting tradeable options update (Supabase + options_quotes)")
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Generate tradeable options
        options = generate_tradeable_options(supabase)
        
        if not options:
            logger.warning("⚠️  No tradeable options generated")
            return 0
        
        # Upsert to database
        count = upsert_tradeable_options(supabase, options)
        
        logger.info(f"🎉 Completed successfully. {count} tradeable options stored.")
        return count
        
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        raise


if __name__ == "__main__":
    main()
