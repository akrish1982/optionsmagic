# 🚀 Monday Launch Guide - February 24, 2026

**Mission:** Deploy Phase 1 code and start SIM testing  
**Timeline:** Monday 9:00 AM ET - 4:00 PM ET  
**Risk Level:** ZERO (SIM mode - no real money)  
**Expected Outcome:** First automated proposal + successful test

---

## 📋 Pre-Launch Checklist (Sunday Evening - DO THIS TODAY)

### ✅ 1. Database Migration (2 minutes)
**Status:** Must be complete before Monday

```
1. Go to: https://supabase.com/dashboard
2. Select project: OptionsMagic
3. Click: "SQL Editor"
4. Click: "New Query"
5. Paste entire contents of: database/ddl/002_positions_and_trade_history.sql
6. Click: "Execute" (green button)
7. Verify: No errors, tables created
8. Check: See "positions" and "trade_history" tables in "Tables" list
```

**What this does:**
- Creates `positions` table (track open positions)
- Creates `trade_history` table (log closed trades)
- Creates `v_daily_pnl` view (daily metrics)
- Creates `v_performance_metrics` view (overall stats)

### ✅ 2. Verify Environment Variables (5 minutes)
**Status:** Verify before Monday

```bash
# From project root
cat .env | grep -E "SUPABASE|TELEGRAM|TRADESTATION"

# Should show:
# SUPABASE_URL=https://...
# SUPABASE_KEY=...
# TRADESTATION_ENV=SIM
# TRADESTATION_DRY_RUN=true
# TELEGRAM_BOT_TOKEN=...
# TELEGRAM_CHAT_ID=...
```

**If any are missing:**
1. Get values from Ananth
2. Edit `.env` file
3. Add missing variables

### ✅ 3. Test Telegram Access (2 minutes)
**Status:** Verify bot can send messages

```bash
# Send a test message to verify Telegram works
poetry run python3 << 'EOF'
from trade_automation.config import Settings
from trade_automation.notifier_telegram import TelegramNotifier
settings = Settings()
notifier = TelegramNotifier(settings)
notifier.send_message("🧪 Test message from OptionsMagic - All systems go!")
EOF
```

**Expected:** Message appears in Telegram chat within 5 seconds

**If fails:**
- Check `TELEGRAM_BOT_TOKEN` is correct
- Check `TELEGRAM_CHAT_ID` is correct
- Verify bot has been added to chat
- See troubleshooting section

### ✅ 4. Run Pre-Deployment Validation (5 minutes)
**Status:** Verify all systems ready

```bash
# Full automated validation
poetry run python scripts/pre_deployment_validation.py

# Or simpler bash check
bash scripts/deployment_ready_check.sh
```

**Expected:** All checks pass (green ✅)

**If failures:** Fix before Monday launch

---

## 🚀 Monday Morning Launch (9:00 AM - 4:00 PM)

### 9:00 AM - System Boot

#### Step 1: Deploy Code (5 min)
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

# Pull latest code
git pull origin main

# Install dependencies
poetry install

# Verify setup
poetry run python scripts/pre_deployment_validation.py
```

**Expected output:** All checks pass, system ready

#### Step 2: Database Connection Test (5 min)
```bash
poetry run python3 << 'EOF'
from trade_automation.supabase_client import get_supabase_client
from trade_automation.config import Settings
settings = Settings()
supabase = get_supabase_client(settings)
result = supabase.table("opportunities").select("count", count="exact").execute()
print(f"✅ Database connected! {result.count} opportunities found.")
EOF
```

**Expected:** Database connection successful

#### Step 3: View Logs Directory (2 min)
```bash
# Verify logs can be written
ls -la logs/
touch logs/test.txt
rm logs/test.txt

# Should see no permission errors
```

### 9:15 AM - First Proposal Generation

#### Step 4: Run Proposal Worker (5-10 min)
```bash
# This will generate trading proposals and send to Telegram
poetry run python -m trade_automation.proposal_worker
```

**What happens:**
1. Connects to database
2. Fetches top 2-3 opportunities
3. Generates trade proposals with risk analysis
4. **Sends to your Telegram** with ✅ APPROVE / ❌ REJECT buttons
5. Logs results to `logs/proposal_worker.log`

**Expected:** Telegram notification arrives with proposal details

**If nothing happens:**
- Check logs: `tail logs/proposal_worker.log`
- Verify database has opportunities
- See troubleshooting

### 10:00 AM - Approval Flow Test

#### Step 5: Approve Trade in Telegram (1 min)
```
In Telegram chat:
- See proposal with trade details
- Click ✅ APPROVE button
- Should get confirmation within 10 seconds
```

**What happens on approval:**
1. approval_worker.py processes click
2. Validates trade parameters
3. Places order on TradeStation (SIM mode)
4. Creates position record in database
5. Sends confirmation Telegram message
6. Logs to `logs/approval_worker.log`

**Expected:**
- Telegram reply: "✅ Position #1 created"
- Position visible in database

**If approval fails:**
- Check logs: `tail logs/approval_worker.log`
- Check Supabase connection
- See troubleshooting

### 11:00 AM - Position Monitoring Test

#### Step 6: Monitor Position (2 min)
```bash
# Check if position was created
poetry run python3 << 'EOF'
from trade_automation.supabase_client import get_supabase_client
from trade_automation.config import Settings
settings = Settings()
supabase = get_supabase_client(settings)
positions = supabase.table("positions").select("*").eq("status", "OPEN").execute()
print(f"✅ Found {len(positions.data)} open positions")
for pos in positions.data:
    print(f"  - {pos['ticker']}: Entry ${pos['entry_price']}")
EOF
```

**Expected:** Position appears in database with entry details

### 1:00 PM - Exit Automation Test

#### Step 7: Run Exit Automation (2-5 min)
```bash
# This monitors positions and applies exit rules
poetry run python -m trade_automation.exit_automation
```

**What it checks:**
1. All open positions
2. Profit target: Is P&L ≥ 50% of max?
3. Stop loss: Has loss exceeded 200% of credit?
4. Days to expiry: Are we ≤ 21 days to expiry?
5. If condition triggered: Close position, log trade, notify

**Expected output:**
- Logs show positions checked
- If no exits triggered: "No positions met exit criteria"
- Logs written to `logs/exit_automation.log`

**If position exits too early:**
- Might be test data from earlier, that's fine

### 2:00 PM - Database Integrity Check

#### Step 8: Verify Data Integrity (2 min)
```bash
# Check positions table
poetry run python3 << 'EOF'
from trade_automation.supabase_client import get_supabase_client
from trade_automation.config import Settings
settings = Settings()
supabase = get_supabase_client(settings)

# Check positions
pos_result = supabase.table("positions").select("count", count="exact").execute()
print(f"Total positions: {pos_result.count}")

# Check trade history
trade_result = supabase.table("trade_history").select("count", count="exact").execute()
print(f"Total trades: {trade_result.count}")

# Check metrics view
metrics = supabase.table("v_performance_metrics").select("*").execute()
print(f"Performance: {metrics.data[0] if metrics.data else 'No data yet'}")
EOF
```

**Expected:** Tables have data, views return results

### 3:00 PM - Full System Review

#### Step 9: Review Logs (5 min)
```bash
# Check all logs for errors
tail -50 logs/*.log

# Specifically check for errors
grep -i "error\|fail" logs/*.log

# Or check for successes
grep "✅" logs/*.log
```

**Expected:** Mostly ✅ success messages, no ❌ critical errors

### 4:00 PM - Readiness Confirmation

#### Step 10: Confirm Ready for Cron Jobs (1 min)
```
If all tests pass:
1. System is working
2. Proposals generated successfully
3. Approvals processed correctly
4. Positions tracked in database
5. Exit automation runs without errors

THEN: Ready to enable cron jobs (or keep manual for today)
```

---

## 📊 Expected Results by 4:00 PM Monday

✅ **Proposal Generated:**
- Trading proposal sent to Telegram
- Shows: Ticker, Strike, Credit, Expiry, Risk

✅ **Trade Executed (SIM):**
- TradeStation shows order placed
- Position created in database
- Entry price logged

✅ **Position Tracked:**
- Position visible in database
- Entry details correct
- P&L calculations working

✅ **All Logs Clean:**
- No critical errors
- Steps logged correctly
- Ready for automation

---

## 🔍 Monitoring During SIM Week

### Daily Checklist (Monday-Friday)

**Each morning (before 9:30 AM):**
```bash
# Check proposal generated
tail -20 logs/proposal_worker.log

# Check approvals processed
tail -20 logs/approval_worker.log

# Check for database errors
grep -i "error" logs/*.log
```

**Each afternoon (after 4:00 PM):**
```bash
# Check exit automation ran
tail -20 logs/exit_automation.log

# Check trades closed
poetry run python3 << 'EOF'
from trade_automation.supabase_client import get_supabase_client
from trade_automation.config import Settings
from datetime import datetime
settings = Settings()
supabase = get_supabase_client(settings)
today = datetime.now().date()
trades = supabase.table("trade_history").select("*").gte("closed_at", str(today)).execute()
print(f"Trades closed today: {len(trades.data)}")
for trade in trades.data:
    print(f"  - {trade['ticker']}: P&L ${trade['pnl_realized']}")
EOF
```

---

## 🆘 Troubleshooting Guide

### Problem: "ModuleNotFoundError: No module named 'trade_automation'"
**Solution:**
```bash
poetry install  # Reinstall dependencies
poetry run python -m trade_automation.proposal_worker
```

### Problem: "SUPABASE_URL not found"
**Solution:**
1. Check .env file: `cat .env | grep SUPABASE`
2. If missing, add to .env and reload
3. Restart Python environment

### Problem: Telegram message not received
**Solution:**
1. Verify bot token: `cat .env | grep TELEGRAM_BOT_TOKEN`
2. Verify chat ID: `cat .env | grep TELEGRAM_CHAT_ID`
3. Check bot is in chat: Telegram → Bot page → Members
4. Test: `poetry run python scripts/test_telegram.py` (if exists)

### Problem: "Database connection failed"
**Solution:**
1. Check internet connection
2. Verify SUPABASE_URL is correct
3. Check Supabase project is online
4. Verify tables exist (see Supabase dashboard)

### Problem: Position not created after approval
**Solution:**
1. Check logs: `tail logs/approval_worker.log`
2. Verify TradeStation credentials configured
3. Check SIM mode enabled: `cat .env | grep TRADESTATION_ENV`
4. Verify database table exists

---

## ✅ Success Metrics

### By End of Monday (4:00 PM)

- [x] Code deployed successfully
- [x] Database connected and verified
- [x] At least 1 proposal generated
- [x] At least 1 approval processed
- [x] Position created in database
- [x] All logs clean (no critical errors)
- [x] Exit automation runs without errors
- [x] Telegram notifications working

### By End of SIM Week (Friday)

- [x] 5-10 trades executed
- [x] Win rate > 50% (or collecting data)
- [x] All 3 exit rules tested
- [x] Zero database errors
- [x] Performance metrics calculated
- [x] Ready for Phase 2 launch

---

## 📝 Monday Launch Worksheet

Print this out and fill in as you go:

```
MONDAY LAUNCH - February 24, 2026

Pre-Launch (Sunday Evening):
☐ Database migration applied
☐ Environment variables verified
☐ Telegram access tested
☐ Pre-deployment validation passed

Monday 9:00 AM Checks:
☐ Code deployed
☐ Dependencies installed
☐ Database connected
☐ Logs directory ready

Monday 9:15 AM - Proposal:
☐ Proposal generated
☐ Telegram message received
☐ Proposal details correct

Monday 10:00 AM - Approval:
☐ Clicked ✅ APPROVE in Telegram
☐ Confirmation received
☐ Position created in database

Monday 1:00 PM - Exit Automation:
☐ Exit automation ran successfully
☐ No critical errors in logs
☐ Database integrity verified

Monday 4:00 PM - Final Check:
☐ All logs reviewed
☐ No blocking issues
☐ System ready for automation

Ready for SIM week? ☐ YES ☐ NO
```

---

## 🎯 Next Phase

### After Successful Monday Launch

**Tuesday-Friday (Feb 25-28):**
- Execute 2-3 trades per day in SIM
- Monitor all exit rules
- Collect P&L data
- Review logs daily

**Friday Evening:**
- Generate SIM week report
- Validate all systems working
- Collect metrics for Phase 2 planning

**Next Week (Mar 1-7):**
- Get Twitter/LinkedIn credentials
- Integrate social media APIs
- Prepare for Phase 2 launch Mar 8

---

## 📞 Support Contacts

**Technical Issues:**
- Check logs first: `tail -f logs/*.log`
- See troubleshooting section above
- Contact engineering team if still stuck

**Quick Reference:**
- Phase 1 docs: `PHASE_1_CHECKLIST.md`
- System overview: `OPTIONSMAGIC_COMPLETE_SYSTEM.md`
- Database schema: `POSITION_MANAGEMENT_SYSTEM.md`

---

**Last Updated:** February 22, 2026  
**Status:** Ready for Monday Launch  
**Confidence:** 🚀 Maximum

**Let's go! 🚀**
