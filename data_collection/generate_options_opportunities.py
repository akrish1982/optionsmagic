"""
Generate Options Opportunities

Filters stocks based on "Long-Only" technical criteria and calculates
Cash-Secured Put (CSP) and Vertical Put Credit Spread (VPC) opportunities.

Criteria:
- Long Bias: price > SMA200, RSI between 30-48 (oversold in uptrend)
- CSP: Delta < 0.30, 30-90 days to expiration
- VPC: Pairs puts at different strikes for credit spreads

Usage:
    poetry run python data_collection/generate_options_opportunities.py
"""

import os
import logging
from datetime import date, datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("options_opportunities.log"),
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


def get_long_bias_candidates(supabase):
    """
    Get stocks that meet "Long-Only" criteria:
    - price > sma200 (uptrend)
    - RSI between 30 and 48 (oversold but not crashed)

    Returns list of ticker dicts with price, rsi, sma200, sma50
    """
    try:
        # Get latest quote date
        response = supabase.table('stock_quotes').select('quote_date').order('quote_date', desc=True).limit(1).execute()
        if not response.data:
            return []
        latest_date = response.data[0]['quote_date']

        # Get stocks meeting long-bias criteria
        # Note: Supabase REST API has limited filtering, so we fetch and filter in Python
        response = supabase.table('stock_quotes').select(
            'ticker, price, rsi, sma50, sma200'
        ).eq('quote_date', latest_date).execute()

        candidates = []
        for row in response.data:
            price = row.get('price')
            rsi = row.get('rsi')
            sma200 = row.get('sma200')

            # Skip if missing data
            if price is None or sma200 is None:
                continue

            # Long-bias filter: price > sma200, RSI in range
            # Note: sma200 in our data is % distance from price, so we check differently
            # If sma200 is stored as actual value, use: price > sma200
            # If sma200 is % from price, negative means price is above SMA200

            # Assuming sma200 is the actual SMA value (not percentage)
            try:
                price_val = float(price)
                sma200_val = float(sma200) if sma200 else None
                rsi_val = float(rsi) if rsi else None

                # Check uptrend: price above SMA200
                # If sma200 is percentage from price: negative = price above SMA
                above_sma200 = True  # Default if we can't determine
                if sma200_val is not None:
                    # If it's a percentage (like -5.2 meaning 5.2% above)
                    if -50 < sma200_val < 50:  # Likely a percentage
                        above_sma200 = sma200_val < 0  # Negative = price above SMA
                    else:  # Likely actual price value
                        above_sma200 = price_val > sma200_val

                # Check RSI in range (oversold but not crashed)
                rsi_in_range = rsi_val is not None and 30 <= rsi_val <= 48

                if above_sma200 and rsi_in_range:
                    candidates.append({
                        'ticker': row['ticker'],
                        'price': price_val,
                        'rsi': rsi_val,
                        'sma50': float(row.get('sma50')) if row.get('sma50') else None,
                        'sma200': sma200_val,
                        'above_sma200': above_sma200
                    })
            except (ValueError, TypeError):
                continue

        logger.info(f"Found {len(candidates)} long-bias candidates")
        return candidates

    except Exception as e:
        logger.error(f"Error getting long-bias candidates: {e}")
        return []


def get_options_for_ticker(supabase, ticker, min_days=30, max_days=90):
    """
    Get put options for a ticker within the specified DTE range.
    """
    try:
        today = date.today()

        # Get latest options date
        response = supabase.table('options_quotes').select('date').order('date', desc=True).limit(1).execute()
        if not response.data:
            return []
        latest_date = response.data[0]['date']

        # Get put options for this ticker
        response = supabase.table('options_quotes').select('*').eq(
            'symbol', ticker
        ).eq('date', latest_date).eq('type', 'put').execute()

        options = []
        for row in response.data:
            try:
                exp_date = datetime.strptime(row['expiration'], '%Y-%m-%d').date()
                days_to_exp = (exp_date - today).days

                if min_days <= days_to_exp <= max_days:
                    options.append({
                        **row,
                        'days_to_exp': days_to_exp
                    })
            except (ValueError, TypeError):
                continue

        return options

    except Exception as e:
        logger.error(f"Error getting options for {ticker}: {e}")
        return []


def calculate_csp_opportunities(ticker_data, options):
    """
    Calculate Cash-Secured Put opportunities.

    Criteria:
    - Delta < 0.30 (high probability of profit)
    - Reasonable premium (bid > 0)

    Returns list of CSP opportunities.
    """
    opportunities = []
    price = ticker_data['price']

    for opt in options:
        try:
            strike = float(opt.get('strike', 0))
            bid = float(opt.get('bid', 0)) if opt.get('bid') else 0
            delta = float(opt.get('delta', 0)) if opt.get('delta') else None
            days_to_exp = opt.get('days_to_exp', 0)

            # Skip if no bid or strike above current price
            if bid <= 0 or strike >= price:
                continue

            # Delta filter: only high probability entries (delta < 0.30)
            # Note: put delta is negative, so we check abs(delta) < 0.30
            if delta is not None and abs(delta) >= 0.30:
                continue

            # Calculate returns
            collateral = strike * 100  # 100 shares per contract
            income = bid * 100
            return_pct = (bid / strike) * 100
            annualized_return = return_pct * (365 / days_to_exp) if days_to_exp > 0 else 0

            # # Cap extreme values to avoid DB overflow
            # return_pct = min(return_pct, 9999.99)
            # annualized_return = min(annualized_return, 9999.99)

            opportunities.append({
                'ticker': ticker_data['ticker'],
                'strategy_type': 'CSP',
                'expiration_date': opt.get('expiration'),
                'strike_price': strike,
                'width': None,  # N/A for CSP
                'net_credit': bid,
                'collateral': collateral,
                'return_pct': round(return_pct, 2),
                'annualized_return': round(annualized_return, 2),
                'rsi_14': ticker_data.get('rsi'),
                'iv_percentile': None,  # TODO: calculate IV percentile
                'price_vs_bb_lower': None,  # TODO: calculate BB distance
                'above_sma_200': ticker_data.get('above_sma200'),
                'delta': delta,
                'theta': float(opt.get('theta', 0)) if opt.get('theta') else None,
                'days_to_exp': days_to_exp,
                'implied_volatility': float(opt.get('implied_volatility', 0)) if opt.get('implied_volatility') else None,
                'contractid': opt.get('contractid')
            })

        except (ValueError, TypeError) as e:
            continue

    # Sort by return and take top 5
    opportunities.sort(key=lambda x: x['return_pct'], reverse=True)
    return opportunities[:5]


def calculate_vpc_opportunities(ticker_data, options):
    """
    Calculate Vertical Put Credit Spread opportunities.

    Structure:
    - Short leg: Sell put at higher strike (collect premium)
    - Long leg: Buy put at lower strike (limit risk)

    Returns list of VPC opportunities.
    """
    opportunities = []
    price = ticker_data['price']

    # Group options by expiration
    by_expiration = {}
    for opt in options:
        exp = opt.get('expiration')
        if exp not in by_expiration:
            by_expiration[exp] = []
        by_expiration[exp].append(opt)

    # For each expiration, find spread opportunities
    for exp_date, exp_options in by_expiration.items():
        # Sort by strike
        exp_options.sort(key=lambda x: float(x.get('strike', 0)))

        # Try different spread widths (typically $5 or $10)
        for i, short_leg in enumerate(exp_options):
            short_strike = float(short_leg.get('strike', 0))
            short_bid = float(short_leg.get('bid', 0)) if short_leg.get('bid') else 0
            short_delta = float(short_leg.get('delta', 0)) if short_leg.get('delta') else None

            # Skip if short strike above current price or no bid
            if short_strike >= price or short_bid <= 0:
                continue

            # Look for long leg at lower strikes
            for long_leg in exp_options[:i]:
                long_strike = float(long_leg.get('strike', 0))
                long_ask = float(long_leg.get('ask', 0)) if long_leg.get('ask') else 0

                width = short_strike - long_strike

                # Only consider reasonable widths ($2.50 to $20)
                if width < 2.5 or width > 20:
                    continue

                # Skip if long ask is too high (no credit)
                if long_ask >= short_bid:
                    continue

                try:
                    net_credit = short_bid - long_ask
                    max_risk = (width - net_credit) * 100
                    collateral = max_risk  # Collateral = width - credit for spreads

                    if max_risk <= 0:
                        continue

                    return_pct = (net_credit / (width - net_credit)) * 100
                    days_to_exp = short_leg.get('days_to_exp', 30)
                    annualized_return = return_pct * (365 / days_to_exp) if days_to_exp > 0 else 0

                    # # Cap extreme values to avoid DB overflow
                    # return_pct = min(return_pct, 9999.99)
                    # annualized_return = min(annualized_return, 9999.99)

                    opportunities.append({
                        'ticker': ticker_data['ticker'],
                        'strategy_type': 'VPC',
                        'expiration_date': exp_date,
                        'strike_price': short_strike,  # Short strike
                        'width': width,
                        'net_credit': round(net_credit, 2),
                        'collateral': round(collateral, 2),
                        'return_pct': round(return_pct, 2),
                        'annualized_return': round(annualized_return, 2),
                        'rsi_14': ticker_data.get('rsi'),
                        'iv_percentile': None,
                        'price_vs_bb_lower': None,
                        'above_sma_200': ticker_data.get('above_sma200'),
                        'delta': short_delta,
                        'theta': float(short_leg.get('theta', 0)) if short_leg.get('theta') else None,
                        'days_to_exp': days_to_exp,
                        'implied_volatility': float(short_leg.get('implied_volatility', 0)) if short_leg.get('implied_volatility') else None,
                        'contractid': f"{short_leg.get('contractid')}/{long_leg.get('contractid')}"
                    })

                except (ValueError, TypeError, ZeroDivisionError):
                    continue

    # Sort by return and take top 5
    opportunities.sort(key=lambda x: x['return_pct'], reverse=True)
    return opportunities[:5]


def truncate_opportunities_table(supabase):
    """Clear the options_opportunities table."""
    try:
        # Delete all rows (Supabase doesn't have TRUNCATE via REST)
        supabase.table('options_opportunities').delete().neq('opportunity_id', 0).execute()
        logger.info("Cleared options_opportunities table")
    except Exception as e:
        logger.warning(f"Could not clear table (may not exist): {e}")


def upsert_opportunities(supabase, opportunities):
    """Insert opportunities into Supabase."""
    if not opportunities:
        return 0

    try:
        # Prepare records for insert
        records = []
        for opp in opportunities:
            record = {
                'ticker': opp['ticker'],
                'strategy_type': opp['strategy_type'],
                'expiration_date': opp['expiration_date'],
                'strike_price': opp['strike_price'],
                'width': opp.get('width'),
                'net_credit': opp['net_credit'],
                'collateral': opp['collateral'],
                'return_pct': opp['return_pct'],
                'annualized_return': opp['annualized_return'],
                'rsi_14': opp.get('rsi_14'),
                'iv_percentile': opp.get('iv_percentile'),
                'price_vs_bb_lower': opp.get('price_vs_bb_lower'),
                'above_sma_200': opp.get('above_sma_200'),
                'delta': opp.get('delta'),
                'theta': opp.get('theta')
            }
            records.append(record)

        # Insert in batches
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            supabase.table('options_opportunities').insert(batch).execute()

        logger.info(f"Inserted {len(records)} opportunities")
        return len(records)

    except Exception as e:
        logger.error(f"Error inserting opportunities: {e}")
        raise


def main():
    """Main function to generate options opportunities."""
    logger.info("Starting options opportunities generation")

    supabase = get_supabase_client()

    # Step 1: Clear old opportunities
    truncate_opportunities_table(supabase)

    # Step 2: Get long-bias candidates
    candidates = get_long_bias_candidates(supabase)

    if not candidates:
        logger.warning("No long-bias candidates found. Relaxing criteria...")
        # Fallback: get all tickers if no candidates meet strict criteria
        response = supabase.table('stock_quotes').select('ticker, price, rsi, sma50, sma200').order('quote_date', desc=True).limit(100).execute()
        candidates = [
            {
                'ticker': row['ticker'],
                'price': float(row['price']) if row.get('price') else 0,
                'rsi': float(row['rsi']) if row.get('rsi') else None,
                'sma50': float(row['sma50']) if row.get('sma50') else None,
                'sma200': float(row['sma200']) if row.get('sma200') else None,
                'above_sma200': True
            }
            for row in response.data if row.get('price')
        ]

    # Step 3: Calculate opportunities for each candidate
    all_opportunities = []

    for ticker_data in candidates:
        ticker = ticker_data['ticker']
        logger.info(f"Processing {ticker}...")

        # Get options for this ticker
        options = get_options_for_ticker(supabase, ticker, min_days=30, max_days=90)

        if not options:
            logger.debug(f"No options found for {ticker}")
            continue

        # Calculate CSP opportunities
        csp_opps = calculate_csp_opportunities(ticker_data, options)
        all_opportunities.extend(csp_opps)

        # Calculate VPC opportunities
        vpc_opps = calculate_vpc_opportunities(ticker_data, options)
        all_opportunities.extend(vpc_opps)

    # Step 4: Insert into database
    if all_opportunities:
        upsert_opportunities(supabase, all_opportunities)
        logger.info(f"Total opportunities generated: {len(all_opportunities)}")
    else:
        logger.warning("No opportunities found")

    logger.info("Options opportunities generation complete")


if __name__ == "__main__":
    main()
