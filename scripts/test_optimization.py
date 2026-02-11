"""
Quick test to verify TradeStation optimization (80% contract reduction)

Tests with 3 tickers to measure:
- Number of contracts fetched
- Execution time
- Expiration count
- Strike filtering effectiveness

Run: poetry run python scripts/test_optimization.py
"""

import sys
import os
import time
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from data_collection.tradestation_options import (
    TradeStationAPI,
    get_supabase_client,
    fetch_options_for_ticker
)

load_dotenv()

def test_optimization():
    """Test optimized pipeline with 3 tickers."""
    
    # Test tickers (popular, liquid options)
    test_tickers = ['SPY', 'QQQ', 'AAPL']
    
    print("=" * 60)
    print("TRADESTATION OPTIMIZATION TEST")
    print("=" * 60)
    print()
    print("Configuration:")
    print("  - Max expirations: 4")
    print("  - Max days: 60")
    print("  - Strike filter: ±20% from current price")
    print("  - Account ID: 12022381")
    print()
    print("=" * 60)
    print()
    
    # Initialize clients
    try:
        api = TradeStationAPI()
        supabase = get_supabase_client()
        print("✅ API clients initialized")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize clients: {e}")
        return 1
    
    total_contracts = 0
    total_time = 0
    
    for ticker in test_tickers:
        print(f"Testing {ticker}...")
        print("-" * 40)
        
        start_time = time.time()
        
        try:
            # Fetch and count contracts
            contracts_stored = fetch_options_for_ticker(api, supabase, ticker)
            
            elapsed = time.time() - start_time
            total_time += elapsed
            total_contracts += contracts_stored
            
            print(f"  Contracts stored: {contracts_stored}")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Rate: {contracts_stored/elapsed:.1f} contracts/sec")
            print()
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            print()
            continue
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total tickers tested: {len(test_tickers)}")
    print(f"Total contracts fetched: {total_contracts}")
    print(f"Avg contracts/ticker: {total_contracts/len(test_tickers):.0f}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Avg time/ticker: {total_time/len(test_tickers):.2f}s")
    print()
    
    # Extrapolate to 70 tickers
    estimated_total = (total_contracts / len(test_tickers)) * 70
    estimated_time = (total_time / len(test_tickers)) * 70
    
    print("EXTRAPOLATION TO 70 TICKERS:")
    print(f"  Estimated contracts: {estimated_total:.0f}")
    print(f"  Estimated time: {estimated_time/60:.1f} minutes")
    print()
    
    # Compare to baseline
    baseline_contracts = 56000  # Before optimization
    reduction_pct = ((baseline_contracts - estimated_total) / baseline_contracts) * 100
    
    print("OPTIMIZATION RESULTS:")
    print(f"  Baseline (before): ~56,000 contracts")
    print(f"  Current (after): ~{estimated_total:.0f} contracts")
    print(f"  Reduction: {reduction_pct:.1f}%")
    
    if reduction_pct >= 70:
        print(f"  ✅ TARGET ACHIEVED (70% reduction)")
    else:
        print(f"  ⚠️  Below target (need 70% reduction)")
    
    print()
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(test_optimization())
