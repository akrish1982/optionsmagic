# SIM Testing Roadmap - February 24-28, 2026

**Status:** Ready to Execute  
**Timeline:** Monday Feb 24 - Friday Feb 28 (5 days)  
**Objective:** Validate Phase 1 code in live trading environment (SIM mode)  
**Risk Level:** ZERO (simulation mode, no real money)

---

## 🎯 Week at a Glance

| Day | Focus | Key Activities |
|-----|-------|-----------------|
| **Mon, Feb 24** | Setup & Smoke Tests | Deploy code, run first proposal generation |
| **Tue, Feb 25** | Trade Execution Test | Execute 2-3 SIM trades, verify approval flow |
| **Wed, Feb 26** | Exit Automation | Test profit target exits, stop loss triggers |
| **Thu, Feb 27** | Performance Validation | Verify P&L calculations, data accuracy |
| **Fri, Feb 28** | Full Integration | Run complete end-to-end workflow, collect data |

---

## 📋 Pre-SIM Checklist (Sunday Feb 23, Ananth)

**Must-Do (30 minutes):**

- [ ] Apply database migration
  - File: `database/ddl/002_positions_and_trade_history.sql`
  - Copy entire SQL into Supabase SQL Editor
  - Click "Execute"
  - Verify: Tables created, no errors

- [ ] Verify TradeStation SIM credentials
  - Check `optionsmagic/.env`
  - Should show:
    ```
    TRADESTATION_ENV=SIM
    TRADESTATION_DRY_RUN=true
    ```

- [ ] Verify Telegram bot access
  - Ananth should have Telegram credentials in `.env`
  - Test by sending a message to bot

---

## 📅 Monday, Feb 24 - SETUP & SMOKE TESTS

### 9:00 AM - Deploy & Verify

**Checklist:**
1. [ ] Pull latest code from main branch
2. [ ] Verify all environment variables loaded
3. [ ] Run Supabase connection test
4. [ ] Verify database tables exist (SELECT count from positions, trade_history)
5. [ ] Check logs directory is writable

**Command:**
```bash
cd optionsmagic
poetry install  # Re-install in case of missing deps
poetry run python -m trade_automation.config  # Verify settings load
```

### 9:30 AM - First Proposal Generation (Dry Run)

**Objective:** Test the full proposal pipeline without executing

**What Happens:**
1. `propose_trades.py` runs
2. Fetches top 3 opportunities from database
3. Generates trade proposals with risk analysis
4. Sends to Telegram (Ananth receives proposals)
5. **Does NOT execute** (dry run mode)

**Expected Output:**
- 📬 Telegram message with 3 proposals
- Each shows: Ticker, Strategy, Strike, Credit, Risk, Target
- ✅ and ❌ buttons (approval/rejection)
- Logs in `logs/proposal_worker.log`

**If it fails:**
- Check `logs/proposal_worker.log` for errors
- Verify opportunities exist in database
- Check Telegram credentials in `.env`

### 11:00 AM - Test Approval Button

**Objective:** Test Telegram interaction

**What Happens:**
1. Click ✅ APPROVE on one of the proposals
2. `approval_worker.py` processes the click
3. **In dry-run mode:** Just logs, doesn't execute
4. Telegram confirmation sent

**Expected Output:**
- Telegram reply: "✅ Processing approval (DRY_RUN mode)"
- Logs show: Request marked as "approved"
- No actual TradeStation order placed

**If it fails:**
- Check Telegram bot token in `.env`
- Verify bot has webhook configured
- Check `logs/approval_worker.log`

### 1:00 PM - Database Sanity Check

**Objective:** Verify database schema is correct

**Queries to run (in Supabase SQL Editor):**
```sql
-- Check positions table
SELECT count(*) FROM positions;

-- Check trade_history table
SELECT count(*) FROM trade_history;

-- Check views exist
SELECT * FROM v_daily_pnl LIMIT 1;
SELECT * FROM v_performance_metrics;
```

**Expected:**
- Both tables exist (count = 0 if fresh)
- Both views return data (or empty if no trades yet)
- No errors

---

## 📊 Tuesday, Feb 25 - TRADE EXECUTION TEST

### 9:00 AM - Generate Proposals

Same as Monday 9:30 AM - proposals should populate Telegram.

### 10:00 AM - Execute First SIM Trade

**Objective:** Test trade execution in SIM mode

**What Happens:**
1. You click ✅ APPROVE on a proposal
2. `approval_worker.py` validates trade
3. TradeStation API called (SIM mode)
4. Order placed on SIM account
5. Position record created in database
6. Telegram confirmation sent with position ID

**Expected Output:**
- Telegram: "✅ Executed {request_id}\nPosition ID: 1"
- Database: New row in `positions` table with status='OPEN'
- Logs: Entry price, quantity, target profit, stop loss recorded

**Manual Verification:**
```sql
SELECT * FROM positions WHERE status = 'OPEN' ORDER BY entry_date DESC LIMIT 1;
```

**If it fails:**
- Check TradeStation credentials in `.env`
- Verify SIM account is accessible
- Check `logs/approval_worker.log` for errors
- Check `logs/tradestation.log` for API errors

### 2:00 PM - Monitor Position

**Objective:** Verify position is being tracked

**Check:**
```sql
SELECT 
  position_id, ticker, entry_price, unrealized_pnl, 
  profit_target, stop_loss
FROM positions 
WHERE status = 'OPEN';
```

**Expected:** Position shows with:
- entry_price filled in
- profit_target = 50% of max profit
- stop_loss = 200% of credit
- unrealized_pnl updating (or 0 if market hasn't moved)

### 3:00 PM - Exit Automation Check

**Objective:** Test exit automation runs without errors

**Command:**
```bash
poetry run python -m trade_automation.exit_automation
```

**Expected Output:**
- Logs show: "Checking open positions..."
- For each position: Shows profit, DTE, stop loss check
- Logs: "No positions met exit criteria" (or exits if triggered)
- No errors

**If it fails:**
- Check `logs/exit_automation.log`
- Verify position data is correct
- Check for database connectivity issues

### 5:00 PM - Review Day 1 Data

**Summary Check:**
```sql
-- How many positions opened today?
SELECT COUNT(*) as positions_created FROM positions 
WHERE DATE(entry_date) = '2026-02-25';

-- Any trades closed?
SELECT COUNT(*) as trades_closed FROM trade_history 
WHERE DATE(closed_at) = '2026-02-25' AND status = 'CLOSED';
```

---

## 📈 Wednesday, Feb 26 - EXIT AUTOMATION TEST

### Goal: Execute some exits to verify all 3 exit rules work

### Morning - Generate & Execute 2-3 Trades

Same process as Tuesday. Target: 2-3 open positions by noon.

### Midday - Manual Exit Test

**Objective:** Test profit target exit

**Process:**
1. Position is open at entry price $100, credit $150
2. Profit target = $75 (50% of max)
3. Manually set current price to $102 (simulating profit)
4. Run exit automation
5. Should exit with profit

**Command:**
```bash
poetry run python -m trade_automation.exit_automation
```

**Expected:**
- Exit automation detects position at profit target
- Closes position with exit_reason = "profit_target"
- Logs to trade_history with pnl_realized = +$75
- Telegram alert sent: "📊 Position exited - SPY - 50% profit target"

**Verify:**
```sql
SELECT * FROM trade_history 
WHERE exit_reason = 'profit_target' 
ORDER BY closed_at DESC LIMIT 1;
```

### Afternoon - Stop Loss Test

**Objective:** Test stop loss exit

**Process:**
1. Open new position at $100 credit, stop loss = $300 (200% of credit)
2. Manually simulate loss to $-300
3. Run exit automation
4. Should exit with stop loss triggered

**Expected:**
- Exit automation detects stop loss hit
- Closes position with exit_reason = "stop_loss"
- Logs to trade_history with pnl_realized = -$300
- Telegram alert sent: "⚠️ Position exited - Stop loss triggered"

### End of Day - Review Exits

```sql
SELECT 
  position_id, ticker, entry_price, exit_price, 
  exit_reason, realized_pnl 
FROM trade_history 
WHERE DATE(closed_at) = '2026-02-26' 
ORDER BY closed_at;
```

---

## 🔍 Thursday, Feb 27 - PERFORMANCE VALIDATION

### Objective: Verify all P&L calculations are accurate

### Morning - Generate New Proposals

Continue generating trades.

### Midday - Accuracy Check

**Verify calculations:**

```sql
-- Check daily P&L view
SELECT * FROM v_daily_pnl WHERE trade_date = '2026-02-26';

-- Check performance metrics view
SELECT * FROM v_performance_metrics;

-- Manual calculation: verify trades
SELECT 
  COUNT(*) as total_trades,
  SUM(CASE WHEN win_loss = 'WIN' THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN win_loss = 'LOSS' THEN 1 ELSE 0 END) as losses,
  ROUND(100.0 * SUM(CASE WHEN win_loss = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as calculated_win_rate,
  SUM(pnl_realized) as total_pnl,
  AVG(pnl_realized) as avg_pnl
FROM trade_history 
WHERE status IN ('CLOSED', 'EXPIRED');
```

**Expected:**
- View calculations match manual SQL calculations
- P&L numbers are accurate
- Win rate is correctly calculated
- No negative trades that should be positive (data integrity)

### Afternoon - Test Phase 2 Data Extraction

**Objective:** Verify morning brief and scorecard generators can access data

**Commands:**
```bash
# Test morning brief generator
poetry run python -m trade_automation.morning_brief_generator

# Test daily scorecard generator
poetry run python -m trade_automation.daily_scorecard_generator
```

**Expected:**
- Morning brief: Fetches 3 opportunities, generates image
- Daily scorecard: Fetches closed trades, calculates metrics
- Both generate images in `/tmp/`
- No database errors

---

## 🚀 Friday, Feb 28 - FULL INTEGRATION & SUMMARY

### Morning - Final Comprehensive Test

**Run complete workflow:**
1. Generate proposals (9:15 AM-style)
2. Execute 2 trades via Telegram approval
3. Exit automation runs every 5 min (should exit at least 1)
4. Generate morning brief (9:00 AM-style)
5. Generate daily scorecard (4:00 PM-style)
6. Verify all data in database

### Midday - Generate Final Report

**Collect metrics:**
```bash
# Export all trade data for the week
psql -h [supabase-host] -U postgres -d [db] << EOF
\COPY (SELECT * FROM trade_history WHERE DATE(entry_date) >= '2026-02-24') TO 'sim_trades_week.csv' WITH CSV HEADER;
\COPY (SELECT * FROM positions) TO 'sim_positions.csv' WITH CSV HEADER;
EOF

# Or via Supabase dashboard: Export CSV from tables
```

### End of Day - SIM Week Summary

**Generate report:**
```markdown
# SIM Testing Week Summary (Feb 24-28)

## Trades Executed
- Total: XX trades
- Wins: XX
- Losses: XX
- Win Rate: XX%

## P&L Performance
- Total P&L: $XX
- Avg P&L/Trade: $XX
- Best Trade: $XX
- Worst Trade: -$XX

## Features Tested
- ✅ Proposal generation
- ✅ Telegram approval flow
- ✅ Trade execution (SIM)
- ✅ Position tracking
- ✅ Profit target exits
- ✅ Stop loss exits
- ✅ 21 DTE exits (if applicable)
- ✅ Database integrity
- ✅ P&L calculations
- ✅ Phase 2 data extraction

## Issues Found
- None! (or list any bugs found)

## Recommendation
✅ Ready for Phase 2 launch on Mar 8
✅ All systems operating as expected
✅ Database performing well
✅ No data integrity issues

## Next Steps
1. Finalize social media APIs
2. Build image templates
3. Deploy Phase 2 generators
4. Start posting to social media (Mar 8)
```

---

## 🔧 Daily Checklist Template

**Each morning:**
```markdown
## [Date] SIM Testing Status

**Start Time:** 9:00 AM ET

### Overnight Checks
- [ ] Database integrity (any errors?)
- [ ] Supabase connection stable
- [ ] Logs reviewed (errors?)

### Daily Activities
- [ ] Proposals generated at 9:15 AM
- [ ] At least 1 trade approved
- [ ] Exit automation runs every 5 min
- [ ] No database errors
- [ ] P&L calculations verified

### End of Day
- [ ] Data exported
- [ ] Summary logged
- [ ] Blockers documented

**Status:** 🟢 All Good / 🟡 Issues Found / 🔴 Critical Error
```

---

## ⚠️ Troubleshooting Reference

### "Database connection failed"
```bash
# Verify Supabase URL and key
cat .env | grep SUPABASE

# Test connection
poetry run python -c "
from trade_automation.config import Settings
from trade_automation.supabase_client import get_supabase_client
s = Settings()
c = get_supabase_client(s)
print('✅ Connected')
"
```

### "TradeStation order failed"
```bash
# Check logs
tail -f logs/tradestation.log

# Verify credentials
cat tokens.json | grep -i "client_id"

# Test SIM mode
poetry run python -c "
from trade_automation.config import Settings
s = Settings()
print(f'Environment: {s.ts_env}')
print(f'Dry Run: {s.tradestation_dry_run}')
"
```

### "Telegram not receiving proposals"
```bash
# Verify bot token
echo $TELEGRAM_BOT_TOKEN

# Check approver ID is correct
cat .env | grep TELEGRAM_CHAT_ID

# Test manually
poetry run python -c "
from trade_automation.notifier_telegram import TelegramNotifier
from trade_automation.config import Settings
n = TelegramNotifier(Settings())
n.send_message('Test message')
"
```

### "P&L calculations wrong"
```sql
-- Verify calculation manually
SELECT 
  entry_price, exit_price, quantity,
  (exit_price - entry_price) * quantity as calculated_pnl,
  pnl_realized
FROM trade_history 
WHERE status = 'CLOSED' 
LIMIT 5;
```

---

## 🎯 Success Criteria

### By End of SIM Week (Feb 28)

✅ **Trades Executed:** 5-10 SIM trades  
✅ **Win Rate:** > 50% (realistic target)  
✅ **Exits Working:** All 3 exit rules triggered at least once  
✅ **Database:** No errors, all data accurate  
✅ **P&L:** Calculations match manual verification  
✅ **Phase 2 Ready:** Generators can extract data  

**If criteria met:** → Proceed to Phase 2 launch (Mar 8)  
**If issues found:** → Fix and re-test until ready  

---

## 📞 Escalation

**If blocker found:**
1. Log issue in `logs/`
2. Document steps to reproduce
3. Check `PHASE_1_CHECKLIST.md` troubleshooting section
4. If unresolved → Escalate to Ananth

---

## 🚀 Ready to Go

**Starting Monday Feb 24, 9:00 AM ET**

All Phase 1 code is tested and ready. SIM mode is safe. Let's run it.

