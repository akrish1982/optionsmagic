#!/usr/bin/env python3
"""
Launch Day Trade Simulator
Generates realistic options trades for demonstration/testing on Mar 8, 2026

This creates:
- Morning opportunities (pre-market)
- Intraday trade executions
- Realistic P&L (wins & losses)
- Proper timestamps
- Complete trade history for daily scorecard

Usage:
  poetry run python scripts/generate_launch_trades.py [--trades 5] [--date 2026-03-08]
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import argparse
from datetime import datetime, timedelta
from trade_automation.supabase_client import get_supabase_client
import random
import uuid

# Configuration
TICKERS = [
    ("AAPL", 150),  # (ticker, approx price)
    ("MSFT", 330),
    ("NVDA", 850),
    ("SPY", 550),
    ("QQQ", 420),
    ("IWM", 190),
    ("GLD", 190),
]

STRATEGIES = ["CSP", "VPC", "PMCP"]  # Cash Secured Put, Vertical Put Call, Poor Man's Call Spread

def generate_realistic_trade(ticker, base_price, strategy):
    """Generate a realistic options trade with P&L"""
    
    # Random entry price (slightly below bid to show it was a good entry)
    entry_price = base_price * random.uniform(0.98, 0.995)
    
    # Calculate net credit/debit
    if strategy == "CSP":
        # Sold Put - credit received
        net_credit = base_price * random.uniform(0.01, 0.03)  # 1-3% credit
        win_chance = 0.65  # 65% win rate on CSPs
    elif strategy == "VPC":
        # Vertical Put Call Spread
        net_credit = base_price * random.uniform(0.005, 0.015)  # 0.5-1.5% credit
        win_chance = 0.60  # 60% win rate
    else:  # PMCP
        # Poor Man's Call Spread
        net_credit = base_price * random.uniform(0.02, 0.05)  # 2-5% credit
        win_chance = 0.70  # 70% win rate

    # Determine win/loss
    is_winner = random.random() < win_chance
    
    if is_winner:
        # Hit profit target (50% of credit)
        exit_price = entry_price + (net_credit * 0.5)
        pnl = net_credit * 0.5
        pnl_percent = (pnl / net_credit * 100) if net_credit > 0 else 0
    else:
        # Hit stop loss (200% of credit for spreads, 100% of credit for CSP)
        stop_mult = 1.0 if strategy == "CSP" else 2.0
        exit_price = entry_price - (net_credit * stop_mult)
        pnl = -(net_credit * stop_mult)
        pnl_percent = -(stop_mult * 100)
    
    return {
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2),
        "net_credit": round(net_credit, 2),
        "pnl": round(pnl, 2),
        "pnl_percent": round(pnl_percent, 2),
        "is_winner": is_winner,
    }

def create_trade_record(supabase, ticker, strategy, trade_data, entry_time):
    """Create a trade record in the database"""
    
    exit_time = entry_time + timedelta(hours=random.randint(2, 8))
    
    # Determine win/loss
    win_loss = "WIN" if trade_data["is_winner"] else "LOSS"
    
    record = {
        "request_id": f"DEMO-{uuid.uuid4().hex[:8].upper()}",
        "ticker": ticker,
        "strategy_type": strategy,
        "entry_date": entry_time.isoformat(),
        "exit_date": exit_time.isoformat(),
        "entry_price": trade_data["entry_price"],
        "exit_price": trade_data["exit_price"],
        "pnl_realized": trade_data["pnl"],
        "pnl_percent": trade_data["pnl_percent"],
        "win_loss": win_loss,
        "status": "CLOSED",
        "quantity": 1,
        "collateral_required": trade_data["net_credit"] * 100,  # Collateral for the trade
    }
    
    try:
        result = supabase.table("trade_history").insert(record).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error inserting trade: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate demo trades for launch day")
    parser.add_argument("--trades", type=int, default=5, help="Number of trades to generate")
    parser.add_argument("--date", type=str, default="2026-03-08", help="Trade date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created without saving")
    
    args = parser.parse_args()
    
    # Parse trade date
    try:
        trade_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Invalid date format: {args.date}. Use YYYY-MM-DD")
        sys.exit(1)
    
    print("=" * 70)
    print(f"🎯 LAUNCH DAY TRADE SIMULATOR")
    print("=" * 70)
    print(f"📅 Date: {trade_date.strftime('%B %d, %Y')}")
    print(f"📊 Trades to generate: {args.trades}")
    print(f"🏃 Mode: {'DRY RUN (no save)' if args.dry_run else 'LIVE (saving to database)'}")
    print("=" * 70)
    
    # Connect to database
    try:
        from trade_automation.config import Settings
        settings = Settings()
        supabase = get_supabase_client(settings)
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Generate trades
    trades_created = []
    total_pnl = 0
    wins = 0
    losses = 0
    
    print(f"\n📈 GENERATING {args.trades} TRADES:")
    print("-" * 70)
    
    for i in range(args.trades):
        # Random ticker & strategy
        ticker, base_price = random.choice(TICKERS)
        strategy = random.choice(STRATEGIES)
        
        # Generate realistic trade
        trade_data = generate_realistic_trade(ticker, base_price, strategy)
        
        # Create entry time (spread throughout trading day: 9:30 AM - 3:30 PM)
        entry_hour = random.randint(9, 15)
        entry_minute = random.randint(0, 59)
        entry_time = trade_date.replace(hour=entry_hour, minute=entry_minute)
        
        trades_created.append({
            "ticker": ticker,
            "strategy": strategy,
            "trade_data": trade_data,
            "entry_time": entry_time,
        })
        
        # Update stats
        total_pnl += trade_data["pnl"]
        if trade_data["is_winner"]:
            wins += 1
            status = "✅ WIN"
        else:
            losses += 1
            status = "❌ LOSS"
        
        # Print trade
        print(f"\n{i+1}. {ticker} {strategy} @ {trade_data['entry_price']} → {trade_data['exit_price']}")
        print(f"   Credit: ${trade_data['net_credit']} | P&L: ${trade_data['pnl']:+.2f} ({trade_data['pnl_percent']:+.1f}%) {status}")
        print(f"   Entry: {entry_time.strftime('%H:%M')}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY:")
    print("=" * 70)
    print(f"Total Trades: {args.trades}")
    print(f"Wins: {wins} ({wins/args.trades*100:.1f}%)")
    print(f"Losses: {losses} ({losses/args.trades*100:.1f}%)")
    print(f"Total P&L: ${total_pnl:+.2f}")
    print(f"Avg Return per Trade: {(total_pnl/sum(t['trade_data']['net_credit'] for t in trades_created)*100):.1f}%")
    
    # Save to database if not dry-run
    if not args.dry_run:
        print("\n" + "=" * 70)
        print("💾 SAVING TO DATABASE...")
        print("=" * 70)
        
        saved = 0
        for trade in trades_created:
            record = create_trade_record(
                supabase,
                trade["ticker"],
                trade["strategy"],
                trade["trade_data"],
                trade["entry_time"],
            )
            
            if record:
                print(f"✅ {trade['ticker']} {trade['strategy']}: {record.get('request_id', 'saved')}")
                saved += 1
            else:
                print(f"❌ {trade['ticker']} {trade['strategy']}: Failed to save")
        
        print(f"\n✅ Saved {saved}/{args.trades} trades to database")
        
        # Verify by querying
        print("\n" + "=" * 70)
        print("🔍 VERIFICATION:")
        print("=" * 70)
        
        try:
            result = supabase.table("trade_history").select("*").execute()
            total_trades = len(result.data) if result.data else 0
            
            # Get today's P&L
            today_trades = [t for t in result.data if t.get("entry_date", "").startswith(args.date)]
            today_pnl = sum(t.get("pnl_realized", 0) for t in today_trades)
            today_wins = sum(1 for t in today_trades if t.get("pnl_realized", 0) > 0)
            
            print(f"Total trades in database: {total_trades}")
            print(f"Today's trades: {len(today_trades)}")
            print(f"Today's P&L: ${today_pnl:+.2f}")
            print(f"Today's win rate: {(today_wins/len(today_trades)*100 if today_trades else 0):.1f}%")
            
        except Exception as e:
            print(f"⚠️ Could not verify: {e}")
    
    else:
        print("\n" + "=" * 70)
        print("🏃 DRY RUN MODE - No data saved")
        print("To save: Run without --dry-run flag")
        print("=" * 70)
    
    print("\n✅ SIMULATION COMPLETE")
    print("\nThis data will appear in:")
    print("  • Morning brief at 9:00 AM (top opportunities)")
    print("  • Daily scorecard at 4:00 PM (P&L summary)")

if __name__ == "__main__":
    main()
