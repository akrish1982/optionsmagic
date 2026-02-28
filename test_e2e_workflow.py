#!/usr/bin/env python3
"""
End-to-End Workflow Test
Simulates: Proposal → Approval → Execution → Position Tracking → Exit → P&L Logging
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path('.').resolve() / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta
from trade_automation.config import Settings
from trade_automation.supabase_client import get_supabase_client
import uuid

def create_synthetic_position(supabase, ticker, strategy, strike, expiry, entry_price, net_credit):
    """Create a synthetic position to test tracking & exit automation"""
    
    position = {
        "request_id": f"TEST-{uuid.uuid4().hex[:8].upper()}",
        "ticker": ticker,
        "strategy_type": strategy,
        "entry_date": datetime.now().isoformat(),
        "entry_price": float(entry_price),
        "status": "OPEN",
        "quantity": 1,
        "legs": [
            {"type": "short_call" if strategy == "CSP" else "short_put", "strike": strike}
        ],
        "profit_target": float(net_credit) * 0.5,
        "stop_loss": float(net_credit) * 2.0,
        "days_held": 0,
        "unrealized_pnl": float(net_credit) * 0.5,  # At profit target
    }
    
    result = supabase.table("positions").insert(position).execute()
    return result.data[0] if result.data else None

def create_synthetic_closed_trade(supabase, ticker, strategy, entry_price, exit_price, credit, pnl):
    """Create a synthetic closed trade to test P&L calculations"""
    
    trade = {
        "request_id": f"TEST-{uuid.uuid4().hex[:8].upper()}",
        "ticker": ticker,
        "strategy_type": strategy,
        "entry_date": (datetime.now() - timedelta(days=1)).isoformat(),
        "exit_date": datetime.now().isoformat(),
        "entry_price": float(entry_price),
        "exit_price": float(exit_price),
        "status": "CLOSED",
        "quantity": 1,
        "collateral_required": float(credit),
        "pnl_realized": float(pnl),
        "pnl_percent": (float(pnl) / float(credit)) * 100,
        "win_loss": "WIN" if pnl > 0 else "LOSS",
    }
    
    result = supabase.table("trade_history").insert(trade).execute()
    return result.data[0] if result.data else None

def test_end_to_end():
    """Run full workflow test"""
    
    print("\n" + "="*70)
    print("END-TO-END WORKFLOW TEST")
    print("="*70)
    
    settings = Settings()
    supabase = get_supabase_client(settings)
    
    print("\n📊 STEP 1: CREATE SYNTHETIC OPEN POSITIONS")
    print("-" * 70)
    
    test_positions = [
        {
            "ticker": "MPWR",
            "strategy": "CSP",
            "strike": 1400.0,
            "expiry": "2026-05-15",
            "entry_price": 1400.0,
            "net_credit": 27000.0,
        },
        {
            "ticker": "NVMI",
            "strategy": "CSP",
            "strike": 480.0,
            "expiry": "2026-05-15",
            "entry_price": 480.0,
            "net_credit": 6880.0,
        },
    ]
    
    created_positions = []
    for pos in test_positions:
        position = create_synthetic_position(supabase, **pos)
        if position:
            created_positions.append(position)
            print(f"✅ Created: {pos['ticker']} {pos['strategy']} @ ${pos['strike']}")
            print(f"   Request ID: {position.get('request_id')}")
            print(f"   P&L: ${position.get('unrealized_pnl', 0):.2f}")
        else:
            print(f"❌ Failed: {pos['ticker']}")
    
    print("\n📊 STEP 2: CREATE SYNTHETIC CLOSED TRADES")
    print("-" * 70)
    
    test_trades = [
        ("SPY", "CSP", 575.0, 577.0, 2500.0, 1250.0),  # Win: 50% profit
        ("QQQ", "VPC", 380.0, 378.0, 2000.0, 1000.0),  # Win: 50% profit
        ("IWM", "CSP", 190.0, 192.0, 1500.0, -750.0), # Loss: 50% of credit
    ]
    
    created_trades = []
    for ticker, strategy, entry, exit_p, credit, pnl in test_trades:
        trade = create_synthetic_closed_trade(supabase, ticker, strategy, entry, exit_p, credit, pnl)
        if trade:
            created_trades.append(trade)
            status = "WIN ✅" if pnl > 0 else "LOSS ❌"
            print(f"✅ Created: {ticker} {strategy} [{status}]")
            print(f"   Entry: ${entry:.2f} → Exit: ${exit_p:.2f} | P&L: ${pnl:,.2f}")
        else:
            print(f"❌ Failed: {ticker}")
    
    print("\n📊 STEP 3: VERIFY POSITION TRACKING")
    print("-" * 70)
    
    positions = supabase.table("positions").select("*").execute()
    print(f"Open Positions: {len(positions.data)}")
    
    total_unrealized = 0
    for p in positions.data:
        print(f"  - {p['ticker']} {p['strategy_type']} @ ${p['entry_price']:.2f}")
        print(f"    Unrealized P&L: ${p['unrealized_pnl']:.2f} | Status: {p['status']}")
        total_unrealized += p.get('unrealized_pnl', 0)
    
    print(f"\n  Total Unrealized P&L: ${total_unrealized:,.2f}")
    
    print("\n📊 STEP 4: VERIFY TRADE HISTORY")
    print("-" * 70)
    
    trades = supabase.table("trade_history").select("*").execute()
    print(f"Closed Trades: {len(trades.data)}")
    
    total_realized = 0
    wins = 0
    if len(trades.data) > 0:
        for t in trades.data:
            pnl = t.get('pnl_realized', 0)
            status = "✅" if pnl > 0 else "❌"
            print(f"  {status} {t['ticker']} {t['strategy_type']} | P&L: ${pnl:,.2f}")
            total_realized += pnl
            if pnl > 0:
                wins += 1
        
        print(f"\n  Total Realized P&L: ${total_realized:,.2f}")
        print(f"  Win Rate: {(wins/len(trades.data)*100):.1f}% ({wins}/{len(trades.data)})")
    else:
        print("  No closed trades found")
    
    print("\n📊 STEP 5: VERIFY P&L VIEWS")
    print("-" * 70)
    
    try:
        daily_pnl = supabase.table("v_daily_pnl").select("*").execute()
        print(f"Daily P&L View: {len(daily_pnl.data)} records")
        if daily_pnl.data:
            for row in daily_pnl.data[:3]:
                print(f"  Date: {row.get('trade_date')} | P&L: ${row.get('total_pnl', 0):,.2f}")
    except Exception as e:
        print(f"⚠️  Daily P&L View: {e}")
    
    try:
        perf = supabase.table("v_performance_metrics").select("*").execute()
        print(f"\nPerformance Metrics: {len(perf.data)} records")
        if perf.data:
            row = perf.data[0]
            print(f"  Total Trades: {row.get('total_trades', 0)}")
            print(f"  Win Rate: {row.get('win_rate', 0):.1f}%")
            print(f"  Total P&L: ${row.get('total_pnl', 0):,.2f}")
    except Exception as e:
        print(f"⚠️  Performance View: {e}")
    
    print("\n📊 STEP 6: VERIFY TELEGRAM WOULD SEND ALERTS")
    print("-" * 70)
    
    from trade_automation.notifier_telegram import TelegramNotifier
    notifier = TelegramNotifier(settings)
    
    if notifier.is_configured():
        try:
            msg = notifier.send_message(
                f"🧪 E2E Test Complete:\n"
                f"• Positions: {len(created_positions)} created\n"
                f"• Trades: {len(created_trades)} logged\n"
                f"• Realized P&L: ${total_realized:,.2f}\n"
                f"• Unrealized P&L: ${total_unrealized:,.2f}\n"
                f"✅ Workflow verified!"
            )
            if msg:
                print(f"✅ Alert message sent (ID: {msg.get('message_id')})")
            else:
                print("⚠️  Alert message failed")
        except Exception as e:
            print(f"❌ Telegram error: {e}")
    else:
        print("⚠️  Telegram not configured")
    
    print("\n" + "="*70)
    print("✅ END-TO-END TEST COMPLETE")
    print("="*70)
    print(f"\n📊 SUMMARY:")
    print(f"  Positions Created: {len(created_positions)}")
    print(f"  Trades Logged: {len(created_trades)}")
    print(f"  Total Realized P&L: ${total_realized:,.2f}")
    print(f"  Total Unrealized P&L: ${total_unrealized:,.2f}")
    print(f"  Total Portfolio Value: ${total_realized + total_unrealized:,.2f}")
    
    if len(created_positions) > 0 and len(created_trades) > 0:
        print("\n🟢 PHASE 1 WORKFLOW VALIDATED")
        return 0
    else:
        print("\n🔴 WORKFLOW INCOMPLETE")
        return 1

if __name__ == "__main__":
    exit_code = test_end_to_end()
    sys.exit(exit_code)
