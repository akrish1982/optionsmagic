# 🏥 Pre-Launch Health Check Guide

**Purpose:** Verify system readiness before Mar 8 launch  
**Script:** `scripts/pre_launch_health_check.py`  
**Status:** ✅ READY

---

## ⚡ Quick Start

### Run Full Health Check
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

poetry run python scripts/pre_launch_health_check.py
```

### Expected Output (Mar 7-8)
```
✅ Passed: 28/36
⚠️  Warnings: 8/36 (expected - credentials due Mar 7, cron jobs not enabled yet)
❌ Failed: 0/36

🟡 STATUS: READY WITH CAUTION → Conditional go/no-go
```

---

## 📋 What Gets Checked

### 1. Environment Setup
```
✅ SUPABASE_URL (database)
✅ SUPABASE_KEY (database)
✅ TELEGRAM_BOT_TOKEN (notifications)
✅ TELEGRAM_CHAT_ID (notifications)
⚠️  Twitter credentials (due Mar 7)
⚠️  LinkedIn credentials (due Mar 7)
```

### 2. Database Connectivity
```
✅ Supabase connected
✅ Table: positions
✅ Table: trade_history
✅ Table: opportunities
✅ View: v_daily_pnl
✅ View: v_performance_metrics
```

### 3. Dependencies
```
✅ tweepy (Twitter API)
✅ selenium (LinkedIn)
✅ PIL/Pillow (images)
✅ yfinance (market data)
✅ supabase (database)
✅ dotenv (config)
```

### 4. API Connections
```
✅ Telegram API connected (test message sent)
⚠️  Twitter API (waiting for credentials)
⚠️  LinkedIn API (waiting for credentials)
```

### 5. Cron Jobs
```
⚠️  Trade proposer (will be enabled Mar 7)
⚠️  Position exits (will be enabled Mar 7)
⚠️  Morning brief (will be enabled Mar 7)
⚠️  Daily scorecard (will be enabled Mar 7)
```

### 6. File System
```
✅ All directories exist
✅ Write permissions OK
✅ Disk space: 68.2 GB free
```

### 7. Trade Simulator
```
✅ Generates test trades
✅ Dry-run mode working
```

### 8. Content Generators
```
✅ Morning Brief Generator (271 LOC)
✅ Daily Scorecard Generator (330 LOC)
```

### 9. Social Media Posters
```
✅ Twitter Poster (193 LOC)
✅ LinkedIn Poster (217 LOC)
```

---

## 🎯 Usage Timeline

### Mar 7 — 2:00 PM (Pre-Launch Validation)

**Run initial check:**
```bash
poetry run python scripts/pre_launch_health_check.py
```

**Expected result:**
- ✅ All critical items pass
- ⚠️ 8 warnings (credentials not yet added, cron not enabled)
- Status: 🟡 READY WITH CAUTION

**Action:**
- Verify all CRITICAL passes
- Document any failures
- Fix issues if needed

### Mar 7 — 5:00 PM (Credentials Added)

**After Zoe adds credentials to .env:**
```bash
poetry run python scripts/pre_launch_health_check.py
```

**Expected result:**
- ✅ All critical items pass
- ⚠️ 2 warnings (cron jobs still not enabled - that's OK)
- Status: 🟡 READY WITH CAUTION

**Action:**
- Verify Twitter credentials working
- Verify LinkedIn credentials working
- Go/No-Go decision time!

### Mar 8 — 6:00 AM (Launch Day)

**Final verification before market open:**
```bash
poetry run python scripts/pre_launch_health_check.py
```

**Expected result:**
- ✅ All critical items pass
- ⚠️ Only cron warning (jobs activate at 9:00 AM)
- Status: 🟡 → Ready

**Action:**
- If all critical pass: GO ✅
- If anything critical fails: NO-GO ❌

---

## 📊 Exit Codes

| Code | Status | Meaning |
|------|--------|---------|
| **0** | 🟢 READY | All systems operational, launch immediately |
| **1** | 🟡 CAUTION | Working but fix warnings before launch |
| **2** | 🔴 NOT READY | Critical issues, do not launch |

### Example:
```bash
poetry run python scripts/pre_launch_health_check.py
echo $?  # Prints 0, 1, or 2
```

---

## 🔧 Troubleshooting

### "Table: opportunities - Failed"
**Issue:** Wrong table name  
**Solution:** Already fixed - script now checks "options_opportunities"

### "Telegram API - Warning"
**Issue:** Telegram may not have internet connectivity  
**Solution:** Not critical - manual fallback exists

### "Cron Jobs - May not be configured"
**Issue:** Cron jobs haven't been enabled yet  
**Solution:** Normal before Mar 8 - they'll be enabled at 6:00 AM

### "Twitter API - Credentials not available"
**Issue:** Zoe hasn't added credentials yet  
**Solution:** Expected before Mar 7 5:00 PM

### "Dependencies - Missing"
**Issue:** A Python package isn't installed  
**Solution:** Run `poetry install` to install all dependencies

---

## 🚀 Launch Day Procedures

### 6:00 AM ET
```bash
poetry run python scripts/pre_launch_health_check.py
```

**Go/No-Go Decision:**
- ✅ All critical pass → **GO** (proceed to 9:00 AM)
- ⚠️ Some warnings → **CONDITIONAL** (fix first)
- ❌ Any failures → **NO-GO** (stop, troubleshoot)

### 8:30 AM ET (30 min before market open)
```bash
poetry run python scripts/pre_launch_health_check.py
```

**Final verification - should be all green:**
- ✅ Database connected
- ✅ All APIs working
- ✅ Generators ready
- ✅ Posters ready

### 9:00 AM ET (LAUNCH!)
- Market opens
- Morning brief auto-posts
- Monitor social media

### 4:00 PM ET
- Daily scorecard auto-posts
- Verify on Twitter & LinkedIn

---

## 📈 Monitoring After Launch

### Daily Health Check
Run every morning to ensure system still healthy:
```bash
poetry run python scripts/pre_launch_health_check.py
```

### Weekly Deep Dive
Check in more detail:
```bash
poetry run python scripts/pre_launch_health_check.py --detailed
```

---

## ✅ Success Criteria

### Pre-Launch (Mar 7)
- [ ] All critical items pass
- [ ] Twitter credentials added to .env
- [ ] LinkedIn credentials added to .env
- [ ] Test message sent to Telegram
- [ ] Trade simulator works
- [ ] Morning brief generator works
- [ ] Daily scorecard generator works

### Launch Day (Mar 8)
- [ ] Health check passes at 6:00 AM
- [ ] Go/No-Go decision: GO ✅
- [ ] First morning brief posts at 9:00 AM
- [ ] Daily scorecard posts at 4:00 PM
- [ ] No critical errors in logs

---

## 🎓 What Health Check Tests

### Critical (Must Pass)
```
✅ Database connectivity
✅ All required credentials present
✅ Telegram API working
✅ All dependencies installed
✅ All files exist
✅ Write permissions OK
```

### Important (Should Pass)
```
✅ Trade simulator working
✅ Content generators exist
✅ Posters implemented
✅ Disk space available
```

### Warnings (Expected Before Mar 8)
```
⚠️  Twitter credentials (until Mar 7)
⚠️  LinkedIn credentials (until Mar 7)
⚠️  Cron jobs (until Mar 8 6:00 AM)
```

---

## 🔗 Related Documentation

- **Launch Day Checklist:** LAUNCH_DAY_CHECKLIST.md
- **Credential Setup:** PHASE_2_CREDENTIAL_SETUP.md
- **Trade Simulator:** LAUNCH_DAY_TRADES_GUIDE.md
- **System Status:** WEEKEND_HEARTBEAT_FINAL.md

---

## 📞 Support

**Script not working?**
- Check Python version: `python --version` (need 3.8+)
- Check poetry: `poetry --version`
- Check directory: Must run from optionsmagic root

**Getting errors?**
- Run with `--detailed` flag for more output
- Check logs: `tail -50 logs/*.log`
- Run individual checks manually

**Before Launch Day:**
- Keep this script handy
- Bookmark this guide
- Test run it a few times
- Know the exit codes

---

**Guide Created:** Saturday, Feb 28, 2026 — 10:15 AM ET  
**Status:** ✅ PRODUCTION READY  
**Next Use:** Friday, Mar 7, 2026 (Pre-launch validation)
