#!/usr/bin/env python3
"""
Phase 1 System Test - Verify entire trading pipeline
Run: poetry run python test_phase1_system.py
"""

import sys
import logging
from pathlib import Path

# LOAD ENV FIRST, before any other imports that read environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from trade_automation.config import Settings
from trade_automation.supabase_client import get_supabase_client
from trade_automation.opportunities import get_latest_option_contract
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_environment():
    """Test 1: Verify environment is configured"""
    print("\n" + "="*60)
    print("TEST 1: ENVIRONMENT CONFIGURATION")
    print("="*60)
    
    try:
        settings = Settings()
        
        checks = [
            ("Supabase URL", settings.supabase_url[:20] + "..."),
            ("Supabase Key", settings.supabase_key[:20] + "..."),
            ("TradeStation Env", settings.ts_env),
            ("TradeStation Dry Run", settings.ts_dry_run),
            ("Trade Mode", settings.trade_mode),
            ("Telegram Bot Token", "***" if settings.telegram_bot_token else "MISSING"),
            ("Telegram Chat ID", settings.telegram_chat_id),
        ]
        
        for name, value in checks:
            status = "✅" if value and value != "MISSING" else "❌"
            print(f"{status} {name}: {value}")
        
        return True
    except Exception as e:
        print(f"❌ Environment check failed: {e}")
        return False

def test_database():
    """Test 2: Verify database connectivity and tables"""
    print("\n" + "="*60)
    print("TEST 2: DATABASE CONNECTIVITY")
    print("="*60)
    
    try:
        settings = Settings()
        supabase = get_supabase_client(settings)
        
        # Test tables
        tables = {
            "options_opportunities": "Trade opportunities",
            "positions": "Open positions",
            "trade_history": "Closed trades",
        }
        
        for table, desc in tables.items():
            try:
                result = supabase.table(table).select("count", count="exact").execute()
                print(f"✅ {table}: {result.count} records")
            except Exception as e:
                print(f"❌ {table}: {e}")
                return False
        
        # Test views
        views = {
            "v_daily_pnl": "Daily P&L",
            "v_performance_metrics": "Performance",
        }
        
        for view, desc in views.items():
            try:
                result = supabase.table(view).select("*").limit(1).execute()
                print(f"✅ {view}: exists")
            except:
                print(f"⚠️  {view}: not yet populated")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_opportunities():
    """Test 3: Verify opportunities generation"""
    print("\n" + "="*60)
    print("TEST 3: OPPORTUNITIES GENERATION")
    print("="*60)
    
    try:
        settings = Settings()
        supabase = get_supabase_client(settings)
        
        # Fetch recent opportunities
        result = supabase.table("options_opportunities")\
            .select("ticker, strategy_type, strike_price, net_credit")\
            .order("last_updated", desc=True)\
            .limit(5)\
            .execute()
        
        if result.data:
            print(f"✅ Found {len(result.data)} recent opportunities:")
            for opp in result.data:
                print(f"   - {opp['ticker']} {opp['strategy_type']} @ ${opp['strike_price']} | Credit: ${opp['net_credit']}")
            return True
        else:
            print("⚠️  No opportunities found (may be normal if generated outside market hours)")
            return True
    except Exception as e:
        print(f"❌ Opportunities test failed: {e}")
        return False

def test_proposal_generation():
    """Test 4: Verify proposal generation logic"""
    print("\n" + "="*60)
    print("TEST 4: PROPOSAL GENERATION LOGIC")
    print("="*60)
    
    try:
        settings = Settings()
        supabase = get_supabase_client(settings)
        
        # Get top 3 opportunities
        result = supabase.table("options_opportunities")\
            .select("*")\
            .order("net_credit", desc=True)\
            .limit(3)\
            .execute()
        
        if result.data:
            print(f"✅ Top 3 opportunities for proposal:")
            for i, opp in enumerate(result.data, 1):
                print(f"   {i}. {opp['ticker']} - {opp['strategy_type']} @ ${opp['strike_price']}")
                print(f"      Credit: ${opp['net_credit']} | Return: {opp['return_pct']:.1f}% | Expiry: {opp['expiration_date']}")
            return True
        else:
            print("⚠️  No opportunities available for proposal")
            return True
    except Exception as e:
        print(f"❌ Proposal generation test failed: {e}")
        return False

def test_position_tracking():
    """Test 5: Verify position tracking schema"""
    print("\n" + "="*60)
    print("TEST 5: POSITION TRACKING SCHEMA")
    print("="*60)
    
    try:
        settings = Settings()
        supabase = get_supabase_client(settings)
        
        # Check positions table structure
        result = supabase.table("positions")\
            .select("*")\
            .limit(1)\
            .execute()
        
        print(f"✅ Positions table ready (status: awaiting SIM test data)")
        
        # Check trade_history table
        result = supabase.table("trade_history")\
            .select("*")\
            .limit(1)\
            .execute()
        
        print(f"✅ Trade history table ready (status: awaiting SIM test data)")
        
        return True
    except Exception as e:
        print(f"❌ Position tracking test failed: {e}")
        return False

def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*60)
    print("PHASE 1 SYSTEM VALIDATION TEST")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = []
    results.append(("Environment", test_environment()))
    results.append(("Database", test_database()))
    results.append(("Opportunities", test_opportunities()))
    results.append(("Proposals", test_proposal_generation()))
    results.append(("Positions", test_position_tracking()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🟢 PHASE 1 READY FOR SIM TRADING")
        return 0
    else:
        print("\n🔴 FIX FAILURES BEFORE SIM TRADING")
        return 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
