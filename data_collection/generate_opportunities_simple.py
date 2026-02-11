"""
Simple Opportunities Generator (Based on Ananth's Working Query)

Uses straightforward SQL join logic to generate put opportunities.
Much simpler than the complex CSP/VPC logic in the original script.

Usage:
    poetry run python data_collection/generate_opportunities_simple.py
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/opportunities_simple.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

from supabase import create_client


def calculate_trade_score(return_pct, rsi, days_to_exp, annualized_return):
    """
    Calculate trade score (A+ to F) based on multiple factors.
    
    Scoring criteria:
    - Return %: Higher is better (up to 50 points)
    - RSI: 30-70 range is best (up to 25 points)
    - Days to expiration: 14-45 days ideal (up to 15 points)
    - Annualized return: Bonus for high annualized (up to 10 points)
    
    Total: 100 points max
    A+: 95-100, A: 90-94, A-: 85-89
    B+: 80-84, B: 75-79, B-: 70-74
    C+: 65-69, C: 60-64, C-: 55-59
    D+: 50-54, D: 45-49, D-: 40-44
    F: < 40
    """
    score = 0
    
    # Return % score (0-50 points)
    # 0-2%: 0-20pts, 2-5%: 20-35pts, 5-10%: 35-45pts, >10%: 45-50pts
    if return_pct >= 10:
        score += 50
    elif return_pct >= 5:
        score += 35 + ((return_pct - 5) / 5) * 15
    elif return_pct >= 2:
        score += 20 + ((return_pct - 2) / 3) * 15
    else:
        score += (return_pct / 2) * 20
    
    # RSI score (0-25 points)
    # Ideal range: 30-70 (neutral to slightly oversold)
    if rsi:
        if 30 <= rsi <= 70:
            score += 25
        elif 20 <= rsi < 30 or 70 < rsi <= 80:
            score += 15
        else:
            score += 5
    else:
        score += 10  # Neutral if no RSI
    
    # Days to expiration score (0-15 points)
    # Ideal: 14-45 days (sweet spot for theta decay)
    if days_to_exp:
        if 14 <= days_to_exp <= 45:
            score += 15
        elif 7 <= days_to_exp < 14 or 45 < days_to_exp <= 60:
            score += 10
        else:
            score += 5
    else:
        score += 7  # Neutral if unknown
    
    # Annualized return bonus (0-10 points)
    if annualized_return:
        if annualized_return >= 100:
            score += 10
        elif annualized_return >= 50:
            score += 7
        elif annualized_return >= 25:
            score += 5
        else:
            score += 2
    
    # Convert score to letter grade
    if score >= 95:
        return 'A+'
    elif score >= 90:
        return 'A'
    elif score >= 85:
        return 'A-'
    elif score >= 80:
        return 'B+'
    elif score >= 75:
        return 'B'
    elif score >= 70:
        return 'B-'
    elif score >= 65:
        return 'C+'
    elif score >= 60:
        return 'C'
    elif score >= 55:
        return 'C-'
    elif score >= 50:
        return 'D+'
    elif score >= 45:
        return 'D'
    elif score >= 40:
        return 'D-'
    else:
        return 'F'


def get_supabase_client():
    """Get Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def generate_simple_opportunities():
    """
    Generate opportunities using simple SQL join logic.
    
    Based on Ananth's working query:
    - Join options_quotes with stock_quotes
    - Filter for puts
    - Calculate returns
    - Insert top opportunities
    """
    supabase = get_supabase_client()
    
    logger.info("Starting simple opportunities generation")
    
    # Clear existing opportunities
    supabase.table('options_opportunities').delete().neq('opportunity_id', 0).execute()
    logger.info("Cleared options_opportunities table")
    
    # Get latest dates
    opt_date_result = supabase.table('options_quotes').select('date').order('date', desc=True).limit(1).execute()
    stock_date_result = supabase.table('stock_quotes').select('quote_date').order('quote_date', desc=True).limit(1).execute()
    
    if not opt_date_result.data or not stock_date_result.data:
        logger.error("No data found in options_quotes or stock_quotes")
        return 0
    
    latest_opt_date = opt_date_result.data[0]['date']
    latest_stock_date = stock_date_result.data[0]['quote_date']
    
    logger.info(f"Using options date: {latest_opt_date}, stock date: {latest_stock_date}")
    
    # Get all put options for latest date
    logger.info("Fetching put options...")
    options_result = supabase.table('options_quotes').select(
        'contractid, symbol, expiration, strike, bid, ask, delta, theta, '
        'implied_volatility, open_interest, volume'
    ).eq('date', latest_opt_date).eq('type', 'put').execute()
    
    logger.info(f"Found {len(options_result.data)} put options")
    
    # Get all stocks for latest date
    logger.info("Fetching stock data...")
    stocks_result = supabase.table('stock_quotes').select(
        'ticker, price, rsi, sma200'
    ).eq('quote_date', latest_stock_date).execute()
    
    # Create stock lookup dict
    stocks = {s['ticker']: s for s in stocks_result.data}
    logger.info(f"Found {len(stocks)} stocks")
    
    # Group options by symbol and expiration for VPC generation
    options_by_symbol_exp = {}
    for opt in options_result.data:
        symbol = opt.get('symbol')
        exp = opt.get('expiration')
        if symbol not in options_by_symbol_exp:
            options_by_symbol_exp[symbol] = {}
        if exp not in options_by_symbol_exp[symbol]:
            options_by_symbol_exp[symbol][exp] = []
        options_by_symbol_exp[symbol][exp].append(opt)
    
    # Generate opportunities (both CSP and VPC)
    opportunities = []
    
    # Generate CSPs (Cash Secured Puts)
    logger.info("Generating CSP opportunities...")
    for opt in options_result.data:
        symbol = opt.get('symbol')
        stock = stocks.get(symbol)
        
        if not stock:
            continue
        
        try:
            strike = float(opt.get('strike', 0))
            bid = float(opt.get('bid', 0))
            ask = float(opt.get('ask', 0))
            price = float(stock.get('price', 0))
            
            if strike <= 0 or bid <= 0 or price <= 0:
                continue
            
            # Calculate metrics (Cash Secured Put style)
            collateral = strike * 100  # Per contract
            income = bid * 100  # Premium collected (per contract)
            return_pct = (bid / strike) * 100  # Return on collateral
            
            # Calculate days to expiration
            exp_date_str = opt.get('expiration')
            if exp_date_str:
                try:
                    exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                    days_to_exp = (exp_date - datetime.now().date()).days
                except:
                    days_to_exp = None
            else:
                days_to_exp = None
            
            # Calculate annualized return
            if days_to_exp and days_to_exp > 0:
                annualized_return = return_pct * (365 / days_to_exp)
            else:
                annualized_return = None
            
            # Basic filters (very permissive)
            if return_pct < 0.5:  # At least 0.5% return
                continue
            
            if days_to_exp and days_to_exp > 90:  # Max 90 days out
                continue
            
            # Calculate trade score
            trade_score = calculate_trade_score(
                return_pct=return_pct,
                rsi=stock.get('rsi'),
                days_to_exp=days_to_exp,
                annualized_return=annualized_return
            )
            
            # Create opportunity record
            opportunity = {
                'ticker': symbol,
                'stock_price': price,  # Current stock price
                'strategy_type': 'CSP',  # Cash Secured Put
                'expiration_date': exp_date_str,
                'strike_price': strike,
                'width': None,  # N/A for CSP
                'net_credit': bid * 100,  # Income per contract (×100)
                'collateral': collateral,
                'return_pct': round(return_pct, 2),
                'annualized_return': round(annualized_return, 2) if annualized_return else None,
                'trade_score': trade_score,  # Letter grade (A+ to F)
                'rsi_14': stock.get('rsi'),
                'iv_percentile': None,
                'price_vs_bb_lower': None,
                'above_sma_200': stock.get('sma200') is not None and price > stock.get('sma200') if stock.get('sma200') else None,
                'delta': float(opt.get('delta')) if opt.get('delta') else None,
                'theta': float(opt.get('theta')) if opt.get('theta') else None,
                'last_updated': datetime.now().isoformat()
            }
            
            opportunities.append(opportunity)
            
        except (ValueError, TypeError) as e:
            logger.debug(f"Error processing option {opt.get('contractid')}: {e}")
            continue
    
    csp_count = len(opportunities)
    logger.info(f"Generated {csp_count} CSP opportunities")
    
    # Generate VPCs (Vertical Put Credit Spreads)
    logger.info("Generating VPC opportunities...")
    
    for symbol, expirations in options_by_symbol_exp.items():
        stock = stocks.get(symbol)
        if not stock:
            continue
        
        price = float(stock.get('price', 0))
        if price <= 0:
            continue
        
        for exp_date_str, exp_options in expirations.items():
            # Sort by strike descending
            exp_options_sorted = sorted(exp_options, key=lambda x: float(x.get('strike', 0)), reverse=True)
            
            # Try to create VPCs with $5 or $10 width
            for i, short_leg in enumerate(exp_options_sorted):
                try:
                    short_strike = float(short_leg.get('strike', 0))
                    short_bid = float(short_leg.get('bid', 0))
                    
                    if short_strike <= 0 or short_bid <= 0:
                        continue
                    
                    # Filter out ITM (In-The-Money) VPCs
                    # For puts: ITM when price >= strike
                    if price >= short_strike:
                        continue
                    
                    # Look for long leg at lower strikes
                    for long_leg in exp_options_sorted[i+1:]:
                        long_strike = float(long_leg.get('strike', 0))
                        long_ask = float(long_leg.get('ask', 0))
                        
                        if long_strike <= 0 or long_ask <= 0:
                            continue
                        
                        width = short_strike - long_strike
                        
                        # Only reasonable widths ($2.50 to $20)
                        if width < 2.5 or width > 20:
                            continue
                        
                        # Calculate net credit
                        net_credit = short_bid - long_ask
                        
                        # Must have positive credit
                        if net_credit <= 0:
                            continue
                        
                        # Calculate metrics
                        collateral = width * 100  # Max risk
                        return_pct = (net_credit / width) * 100
                        
                        # Calculate days to expiration
                        try:
                            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                            days_to_exp = (exp_date - datetime.now().date()).days
                        except:
                            days_to_exp = None
                        
                        # Calculate annualized return
                        if days_to_exp and days_to_exp > 0:
                            annualized_return = return_pct * (365 / days_to_exp)
                        else:
                            annualized_return = None
                        
                        # Filters
                        if return_pct < 0.5:  # At least 0.5% return
                            continue
                        
                        if days_to_exp and days_to_exp > 90:  # Max 90 days out
                            continue
                        
                        # Calculate trade score
                        trade_score = calculate_trade_score(
                            return_pct=return_pct,
                            rsi=stock.get('rsi'),
                            days_to_exp=days_to_exp,
                            annualized_return=annualized_return
                        )
                        
                        # Create VPC opportunity
                        vpc_opp = {
                            'ticker': symbol,
                            'stock_price': price,  # Current stock price
                            'strategy_type': 'VPC',  # Vertical Put Credit Spread
                            'expiration_date': exp_date_str,
                            'strike_price': short_strike,  # Short leg strike
                            'width': width,  # Spread width
                            'net_credit': net_credit * 100,  # Income per contract (×100)
                            'collateral': collateral,
                            'return_pct': round(return_pct, 2),
                            'annualized_return': round(annualized_return, 2) if annualized_return else None,
                            'trade_score': trade_score,  # Letter grade (A+ to F)
                            'rsi_14': stock.get('rsi'),
                            'iv_percentile': None,
                            'price_vs_bb_lower': None,
                            'above_sma_200': stock.get('sma200') is not None and price > stock.get('sma200') if stock.get('sma200') else None,
                            'delta': float(short_leg.get('delta')) if short_leg.get('delta') else None,
                            'theta': float(short_leg.get('theta')) if short_leg.get('theta') else None,
                            'last_updated': datetime.now().isoformat()
                        }
                        
                        opportunities.append(vpc_opp)
                        
                        # Only keep best 3 VPCs per expiration per symbol
                        break
                        
                except (ValueError, TypeError) as e:
                    continue
    
    vpc_count = len(opportunities) - csp_count
    logger.info(f"Generated {vpc_count} VPC opportunities")
    logger.info(f"Total opportunities: {len(opportunities)} ({csp_count} CSP + {vpc_count} VPC)")
    
    # Group opportunities by ticker and take top 3 per ticker
    # Sort by return_pct descending first
    opportunities.sort(key=lambda x: x['return_pct'], reverse=True)
    
    ticker_opps = {}
    for opp in opportunities:
        ticker = opp['ticker']
        if ticker not in ticker_opps:
            ticker_opps[ticker] = []
        
        # Only keep top 3 per ticker
        if len(ticker_opps[ticker]) < 3:
            ticker_opps[ticker].append(opp)
    
    # Flatten back to list
    top_opportunities = []
    for ticker_list in ticker_opps.values():
        top_opportunities.extend(ticker_list)
    
    logger.info(f"Keeping top 3 per ticker: {len(top_opportunities)} opportunities ({len(ticker_opps)} tickers)")
    
    # Insert in batches of 100
    if top_opportunities:
        batch_size = 100
        total_inserted = 0
        
        for i in range(0, len(top_opportunities), batch_size):
            batch = top_opportunities[i:i+batch_size]
            result = supabase.table('options_opportunities').insert(batch).execute()
            total_inserted += len(batch)
            logger.info(f"Inserted batch {i//batch_size + 1}: {len(batch)} opportunities")
        
        logger.info(f"✅ Total opportunities inserted: {total_inserted}")
        return total_inserted
    else:
        logger.warning("No opportunities generated")
        return 0


def main():
    """Main entry point."""
    try:
        count = generate_simple_opportunities()
        logger.info(f"Options opportunities generation complete: {count} opportunities")
        return 0
    except Exception as e:
        logger.error(f"Failed to generate opportunities: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
