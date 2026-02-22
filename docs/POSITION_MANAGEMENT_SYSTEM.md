# Position Management System - Technical Documentation

**Status:** ✅ Implementation Complete (Phase 1)  
**Date:** February 22, 2026  
**Author:** Max

---

## Overview

The Position Management System tracks all open positions, calculates unrealized/realized P&L, and automatically applies exit rules based on profit targets, stop losses, and days to expiry.

### Key Components

1. **`position_manager.py`** - Core position tracking logic
2. **`exit_automation.py`** - Monitoring and exit execution
3. **`Database Tables`** - positions, trade_history, and performance views
4. **Integration with `approval_worker.py`** - Creates positions on trade execution

---

## Database Schema

### positions Table

Stores all open and closed positions with real-time P&L tracking.

```sql
CREATE TABLE positions (
    position_id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) UNIQUE,
    ticker VARCHAR(20),
    strategy_type VARCHAR(10),        -- 'CSP' or 'VPC'
    status VARCHAR(20),                -- 'OPEN', 'CLOSED', 'EXPIRED'
    
    -- Entry
    entry_date TIMESTAMP,
    entry_price NUMERIC(10, 2),
    quantity INTEGER,
    
    -- Exit
    exit_date TIMESTAMP,
    exit_price NUMERIC(10, 2),
    exit_reason VARCHAR(50),           -- profit_target, stop_loss, 21dte, manual
    
    -- P&L
    unrealized_pnl NUMERIC(10, 2),
    realized_pnl NUMERIC(10, 2),
    pnl_percent NUMERIC(10, 2),
    
    -- Rules
    stop_loss NUMERIC(10, 2),
    profit_target NUMERIC(10, 2),
    days_held INTEGER,
    
    -- Metadata
    legs JSONB,
    notes TEXT,
    last_updated TIMESTAMP
);
```

### trade_history Table

Complete log of all executed trades for performance analytics.

```sql
CREATE TABLE trade_history (
    trade_id SERIAL PRIMARY KEY,
    request_id VARCHAR(255),
    position_id INTEGER REFERENCES positions,
    
    ticker VARCHAR(20),
    strategy_type VARCHAR(10),
    
    entry_date TIMESTAMP,
    entry_price NUMERIC(10, 2),
    quantity INTEGER,
    
    exit_date TIMESTAMP,
    exit_price NUMERIC(10, 2),
    
    pnl_realized NUMERIC(10, 2),
    pnl_percent NUMERIC(10, 2),
    win_loss VARCHAR(10),              -- 'WIN' or 'LOSS'
    
    collateral_required NUMERIC(10, 2),
    max_risk NUMERIC(10, 2),
    target_return NUMERIC(10, 2),
    
    status VARCHAR(20),
    executed_by VARCHAR(20),           -- 'auto' or 'manual'
    created_at TIMESTAMP,
    closed_at TIMESTAMP
);
```

### SQL Views

#### `v_daily_pnl`
```sql
SELECT 
    trade_date,
    ticker,
    trades_count,
    wins,
    losses,
    win_rate,
    total_pnl,
    avg_pnl
FROM v_daily_pnl
ORDER BY trade_date DESC;
```

#### `v_performance_metrics`
```sql
SELECT 
    total_trades,
    total_wins,
    total_losses,
    win_rate,
    total_pnl,
    avg_pnl_per_trade,
    max_loss,
    max_win,
    pnl_stddev
FROM v_performance_metrics;
```

---

## Position Manager API

### Core Methods

#### `create_position(request, entry_price, quantity, execution_data)`
Creates a new position when a trade is executed.

```python
position = await position_mgr.create_position(
    request=trade_request,
    entry_price=100.50,
    quantity=1,
    execution_data={"order_id": "TS123"}
)
# Returns: {"position_id": 1, "ticker": "SPY", "status": "OPEN", ...}
```

#### `get_open_positions(ticker=None)`
Fetch all open positions, optionally filtered by ticker.

```python
open_positions = await position_mgr.get_open_positions()
# or
spy_positions = await position_mgr.get_open_positions(ticker="SPY")
```

#### `check_exit_conditions()`
Evaluate all open positions for exit rules.

```python
exit_list = await position_mgr.check_exit_conditions()
# Returns: [(position, "21dte"), (position, "profit_target"), ...]
```

#### `close_position(position_id, exit_price, exit_reason, realized_pnl)`
Close a position and log to trade_history.

```python
await position_mgr.close_position(
    position_id=1,
    exit_price=102.00,
    exit_reason="profit_target",
    realized_pnl=150.00
)
```

### Performance Queries

#### `get_performance_metrics()`
Overall trading performance.

```python
metrics = await position_mgr.get_performance_metrics()
# Returns: {
#     "total_trades": 15,
#     "win_rate": 73.3,
#     "total_pnl": 450.00,
#     "avg_pnl_per_trade": 30.00
# }
```

#### `get_daily_pnl(date)`
Get P&L summary for a specific date.

```python
daily = await position_mgr.get_daily_pnl(datetime(2026, 2, 22))
# Returns: {
#     "date": "2026-02-22",
#     "trades": 3,
#     "wins": 2,
#     "win_rate": 66.7,
#     "total_pnl": 175.00
# }
```

---

## Exit Rules

### Rule 1: Days to Expiry (21 DTE)
Positions close 21 days before option expiration to avoid gamma risk.

```python
def _should_exit_by_dte(position):
    expiration = parse_date(position.legs[0].expiration)
    days_remaining = (expiration - now()).days
    return days_remaining <= 21
```

### Rule 2: Profit Target (50%)
Close position when it reaches 50% of maximum profit.

```python
max_profit = position.profit_target * 2
current_pnl = (current_price - entry_price) * quantity
exit_if_reached = current_pnl >= max_profit * 0.5
```

### Rule 3: Stop Loss (200% for spreads)
Close position if loss exceeds stop loss threshold.

- **CSP (Cash-Secured Put):** Stop loss = 200% of credit received
- **VPC (Vertical Put Credit):** Stop loss = width of spread

```python
def _check_stop_loss(position, current_price):
    current_loss = abs((current_price - entry_price) * quantity)
    return current_loss >= position.stop_loss
```

---

## Exit Automation

The `exit_automation.py` script runs every 5 minutes during market hours to check and execute exits.

### Running Exit Automation

```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic
python -m trade_automation.exit_automation
```

### Adding to Crontab (Market Hours Only)

```bash
# Every 5 minutes, Mon-Fri, 9:30 AM - 4:00 PM ET
*/5 9-16 * * 1-5 cd /workspace && poetry run python -m trade_automation.exit_automation
```

### Exit Workflow

1. **Check open positions** - Query all positions with status='OPEN'
2. **Evaluate each position:**
   - Days to expiry ≤ 21?
   - Unrealized P&L ≥ 50% target?
   - Loss ≥ stop loss threshold?
3. **Execute exits:**
   - Close position in database
   - Log to trade_history
   - Send notification via Telegram
4. **Sleep 5 minutes** - Check again

---

## Integration with Trade Approval

When a trade is executed, the approval worker creates a position:

```python
# approval_worker.py (lines 108-121)
if result.get("ok") or result.get("dry_run"):
    update_request_status(state, request_id, "executed")
    
    # Create position record
    position = position_mgr.create_position(
        trade,
        entry_price=result.get("execution_price", net_credit),
        quantity=quantity,
        execution_data=result
    )
    
    notifier.send_message(f"✅ Position {position['position_id']} created")
```

---

## Performance Dashboard

The system provides multiple ways to track performance:

### 1. Real-Time Position Monitoring

```python
open = await position_mgr.get_open_positions()
for pos in open:
    print(f"{pos['ticker']}: Entry ${pos['entry_price']} - "
          f"Current: ${pos['unrealized_pnl']}")
```

### 2. Historical Trade Analysis

```python
history = supabase.table("trade_history").select("*").execute().data
win_rate = sum(1 for t in history if t['win_loss'] == 'WIN') / len(history) * 100
```

### 3. Daily P&L Reports

```python
daily = await position_mgr.get_daily_pnl(today)
print(f"Today: {daily['wins']} wins, {daily['losses']} losses, "
      f"P&L: ${daily['total_pnl']}")
```

---

## Data Flow Diagram

```
┌──────────────────────┐
│ propose_trades.py    │
│ (Daily @ 9:15 AM)    │
└──────────┬───────────┘
           │
┌──────────▼──────────────────────────┐
│ approval_worker.py                  │
│ (Telegram button clicks)             │
└──────────┬───────────────────────────┘
           │
           │ On APPROVE:
           │ 1. Execute via TradeStation
           │ 2. Create position record
           │ 3. Log to positions table
           │
┌──────────▼──────────────────────────┐
│ POSITIONS (Open)                    │
├──────────────────────────────────────┤
│ position_id | ticker | entry_price  │
│ unrealized_pnl | exit_reason        │
└──────────┬───────────────────────────┘
           │
           │ Async monitoring
           │
┌──────────▼──────────────────────────┐
│ exit_automation.py                  │
│ (Every 5 min, Mon-Fri 9:30-4:00)   │
│                                      │
│ Check:                              │
│ - Days to expiry ≤ 21?             │
│ - P&L ≥ 50% profit target?         │
│ - Loss ≥ stop loss?                │
└──────────┬───────────────────────────┘
           │
           │ On EXIT:
           │ 1. Close position record
           │ 2. Calculate realized P&L
           │ 3. Log to trade_history
           │ 4. Send Telegram alert
           │
┌──────────▼──────────────────────────┐
│ TRADE_HISTORY (Closed)              │
├──────────────────────────────────────┤
│ ticker | entry_price | exit_price   │
│ pnl_realized | win_loss | status    │
└──────────────────────────────────────┘
```

---

## Example Workflow

### Day 1: Trade Execution

```
09:15 AM: propose_trades.py sends opportunity
         → Ticker: SPY, Strategy: CSP, Strike: 580, Credit: $150

09:17 AM: User clicks ✅ APPROVE in Telegram
         → TradeStation executes order
         → Position created:
           {
             "position_id": 5,
             "ticker": "SPY",
             "status": "OPEN",
             "entry_price": 150.00,
             "profit_target": 75.00,  # 50% of max
             "stop_loss": 300.00,     # 200% of credit
             "entry_date": "2026-02-22T14:17:00"
           }
```

### Day 7: Exit Automation Checks

```
10:30 AM: exit_automation.py runs (every 5 min)

         Check Position #5:
         - Days to expiry: 45 days ✓ (> 21)
         - Current stock price: $582
         - Current P&L: -$200 (loss)
         - Loss vs stop: $200 < $300 ✓
         
         Result: HOLD (no exit triggered)

2:00 PM:  exit_automation.py runs

         Check Position #5:
         - Current stock price: $575
         - Current P&L: +$75 (profit)
         - P&L vs target: $75 >= $75 ✓
         
         Action: EXIT (profit target reached)
         
         Position updated:
         {
           "status": "CLOSED",
           "exit_date": "2026-02-22T19:00:00",
           "exit_price": 75.00,
           "exit_reason": "profit_target",
           "realized_pnl": 75.00,
           "pnl_percent": 50.0
         }
         
         Trade logged to history:
         {
           "ticker": "SPY",
           "win_loss": "WIN",
           "pnl_realized": 75.00,
           "pnl_percent": 50.0
         }
         
         Telegram alert: "📊 Position 5 exited - SPY - 50% profit target"
```

---

## Testing the System

### 1. Create a Test Position

```python
from trade_automation.position_manager import PositionManager
from trade_automation.supabase_client import get_supabase_client
from trade_automation.models import TradeRequest, OptionLeg

settings = Settings()
supabase = get_supabase_client(settings)
position_mgr = PositionManager(supabase)

# Create test trade
test_trade = TradeRequest(
    request_id="TEST_001",
    strategy_type="CSP",
    ticker="SPY",
    expiration_date="2026-03-21",
    strike_price=580.0,
    net_credit=150.00,
    quantity=1,
    legs=[OptionLeg(...)]
)

# Create position
position = await position_mgr.create_position(
    test_trade,
    entry_price=150.00,
    quantity=1,
    execution_data={}
)

print(f"Created position: {position}")
```

### 2. Check Open Positions

```python
open_pos = await position_mgr.get_open_positions()
print(f"Open positions: {len(open_pos)}")
for pos in open_pos:
    print(f"  {pos['position_id']}: {pos['ticker']} - "
          f"Entry: ${pos['entry_price']}")
```

### 3. Simulate Exit

```python
# Close position manually
await position_mgr.close_position(
    position_id=position['position_id'],
    exit_price=175.00,
    exit_reason="test_exit",
    realized_pnl=25.00
)

# Verify it's closed
history = supabase.table("trade_history").select("*").execute().data
print(f"Trade history: {history[-1]}")
```

---

## Performance Metrics

After a week of trading, check performance:

```python
metrics = await position_mgr.get_performance_metrics()

print(f"Total Trades: {metrics['total_trades']}")
print(f"Win Rate: {metrics['win_rate']:.1f}%")
print(f"Total P&L: ${metrics['total_pnl']:.2f}")
print(f"Avg P&L/Trade: ${metrics['avg_pnl_per_trade']:.2f}")
```

---

## Next Steps

### Phase 2: Social Media Integration
1. Morning Brief Generator (9:00 AM ET)
   - Fetch opportunities
   - Generate formatted brief
   - Post to Twitter/X, LinkedIn, Instagram

2. Daily Scorecard Generator (4:00 PM ET)
   - Fetch today's closed trades
   - Generate P&L summary
   - Create visual cards with Pillow
   - Post to social media

### Phase 3: Advanced Features
1. Position analytics dashboard (web UI)
2. Weekly performance reports
3. Sharpe ratio and max drawdown calculations
4. Strategy performance comparison
5. Trade journal with notes and sentiment tracking

---

## Troubleshooting

### "Position not found"
```python
# Make sure request_id matches exactly (case-sensitive)
position = await position_mgr.get_position_by_request_id(request_id)
assert position is not None, f"Position for {request_id} not found"
```

### "Failed to create position"
```python
# Check Supabase connection
try:
    supabase = get_supabase_client(settings)
    test = supabase.table("positions").select("count", count="exact").execute()
    print(f"Table accessible: {test.count} rows")
except Exception as e:
    print(f"Supabase error: {e}")
```

### Exit automation not running
```bash
# Check if process is alive
ps aux | grep exit_automation.py

# Check logs
tail -f logs/exit_automation.log

# Test manually
python -m trade_automation.exit_automation
```

---

## Summary

The Position Management System provides:

✅ **Automatic position tracking** - Created on execution, logged in database  
✅ **Real-time P&L calculation** - Entry/exit prices tracked  
✅ **Smart exit rules** - Profit targets, stop losses, days to expiry  
✅ **Trade history logging** - Complete audit trail of all trades  
✅ **Performance metrics** - Win rate, P&L, daily summaries  
✅ **Notification integration** - Telegram alerts on exits  

Ready for Phase 2: Social media publishing and public performance tracking.

