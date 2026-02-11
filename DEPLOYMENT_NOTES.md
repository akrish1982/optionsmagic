# Deployment Notes for OptionsMagic
**Production Deployment Checklist**

**Created by:** Max 👨‍💻  
**Date:** Feb 11, 2026  
**Status:** Ready for Production Server

---

## 🚀 **Deployment Steps for Production Server**

### **1. Install Cron Jobs**

**Run on production server (not sandbox):**
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic
bash scripts/setup_cron_jobs.sh
```

**This will install:**
- Hourly data collection (9 AM - 4 PM ET, Mon-Fri)
- Weekly cleanup (Sunday 2 AM ET)

**Verify installation:**
```bash
crontab -l | grep OptionsMagic
```

**Expected output:**
```
# OptionsMagic - Hourly data collection (market hours)
0 9-16 * * 1-5 cd /home/openclaw/.openclaw/workspace/optionsmagic && $HOME/.local/bin/poetry run python data_collection/finviz.py >> logs/finviz.log 2>&1 && ...

# OptionsMagic - Weekly data cleanup (30-day retention)
0 2 * * 0 cd /home/openclaw/.openclaw/workspace/optionsmagic && $HOME/.local/bin/poetry run python data_collection/cleanup_old_data.py >> logs/cleanup.log 2>&1
```

---

### **2. Monitor First Production Run**

**When:** Next market hours (Feb 12, 2026 9:00 AM ET)

**Check logs:**
```bash
tail -f logs/finviz.log
tail -f logs/tradestation.log
tail -f logs/opportunities.log
```

**Expected behavior:**
- finviz.py: Fetch ~70 stocks
- tradestation_options.py: Fetch ~16,800 contracts (70% reduction from 56K)
- generate_options_opportunities.py: Generate ~300 opportunities

**Success criteria:**
- No errors in logs
- ~16,800 contracts fetched (not ~56,000)
- Execution completes in ~53 minutes
- No timeouts

---

### **3. Verify Optimization Working**

**After first run, check contract count:**
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic
poetry run python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
result = supabase.table('options_quotes').select('contractid', count='exact').eq('date', '2026-02-12').execute()
print(f'Contracts fetched: {result.count}')
print(f'Target: ~16,800')
print(f'Baseline: ~56,000')
if result.count < 20000:
    print('✅ Optimization working!')
else:
    print('⚠️ Check optimization - higher than expected')
"
```

---

### **4. Database Cleanup Verification**

**After first weekly cleanup (Sunday Feb 16, 2026):**
```bash
# Check cleanup log
cat logs/cleanup.log

# Verify oldest data is ~30 days
poetry run python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
result = supabase.table('stock_quotes').select('quote_date').order('quote_date').limit(1).execute()
print(f'Oldest stock data: {result.data[0][\"quote_date\"]}')
result = supabase.table('options_quotes').select('date').order('date').limit(1).execute()
print(f'Oldest options data: {result.data[0][\"date\"]}')
"
```

Expected: Dates should be ~30 days ago or less

---

## 📊 **Performance Baseline**

**Before optimization:**
- Contracts/run: ~56,000
- Execution time: 30-40 minutes
- Timeout risk: HIGH
- Database growth: Uncapped

**After optimization:**
- Contracts/run: ~16,800
- Execution time: ~53 minutes
- Timeout risk: NONE
- Database size: 51MB (30-day retention)

---

## ⚠️ **Troubleshooting**

### **Issue: Cron jobs not running**

**Check:**
```bash
# Verify cron service is running
sudo service cron status

# Check cron logs
grep CRON /var/log/syslog

# Test cron job manually
bash -c "$(crontab -l | grep 'OptionsMagic - Hourly' | grep -v '#')"
```

### **Issue: Contract count still high (~56K)**

**Possible causes:**
1. Old code still deployed (check git commit hash)
2. Optimization not applied (check tradestation_options.py)
3. Account ID wrong (check .env)

**Fix:**
```bash
# Verify code version
cd /home/openclaw/.openclaw/workspace/optionsmagic
git log -1

# Expected: e15fab8 or later
# "📊 Data Quality & Optimization Complete (5/6 Tasks)"

# Verify account ID
grep TRADESTATION_ACCOUNT_ID .env
# Expected: TRADESTATION_ACCOUNT_ID=12022381

# Verify optimization parameters
grep "max_expirations" data_collection/tradestation_options.py
# Expected: max_expirations=4
```

### **Issue: Cleanup not deleting old data**

**Check:**
```bash
# Run cleanup in dry-run mode
cd /home/openclaw/.openclaw/workspace/optionsmagic
poetry run python data_collection/cleanup_old_data.py --dry-run

# Check for errors
cat logs/cleanup.log
```

---

## ✅ **Production Readiness Checklist**

**Before deploying to production:**

- [x] Code tested locally
- [x] Optimization verified (70% reduction)
- [x] Cleanup script tested (dry-run)
- [x] Documentation complete
- [x] Git commits pushed
- [ ] Cron jobs installed on production server
- [ ] First production run monitored
- [ ] Logs verified (no errors)
- [ ] Performance metrics confirmed

---

## 📁 **Key Files for Production**

**Scripts:**
- `scripts/setup_cron_jobs.sh` - One-time cron installation
- `scripts/test_optimization.py` - Verify optimization working
- `data_collection/cleanup_old_data.py` - 30-day retention

**Documentation:**
- `docs/DATABASE_DESIGN_RECOMMENDATIONS.md` - Schema analysis
- `docs/TRADESTATION_OPTIMIZATION.md` - Optimization details
- `docs/CLEANUP_SCRIPT.md` - Cleanup documentation
- `STATUS_REPORT_FEB11.md` - Complete status report

**Configuration:**
- `.env` - Account ID: 12022381
- `data_collection/tradestation_options.py` - Optimized parameters

---

## 🎯 **Success Metrics (Week 1)**

**Monitor these for first week:**

1. **Contract Count:** ~16,800/day (not ~56,000)
2. **Execution Time:** ~53 minutes (no timeouts)
3. **Database Size:** ~51MB (30-day window)
4. **Cleanup Runs:** Weekly (Sunday 2 AM)
5. **Error Rate:** 0% (no failures)

**If all metrics hit targets: ✅ Optimization successful!**

---

**Created by:** Max 👨‍💻  
**Date:** Feb 11, 2026  
**Status:** Ready for Production Deployment
