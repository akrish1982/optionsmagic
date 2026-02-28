# 🚀 LAUNCH DAY RUNBOOK GUIDE

**Purpose:** Execute all pre-launch verifications with a single command  
**Script:** `scripts/launch_day_runbook.sh`  
**Status:** ✅ READY

---

## ⚡ QUICK START

### Run on Launch Day (Mar 8, 6:00 AM ET)
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

bash scripts/launch_day_runbook.sh
```

**Expected Output:**
```
🟢 STATUS: READY FOR LAUNCH
   All systems operational. Go/No-Go: GO ✅
```

**Exit Code:** `0` = GO ✅

---

## 📋 WHAT THE RUNBOOK DOES

### Automated Checks (7 sections)

**1. Time Verification**
- ✅ Checks current time is within 6-9 AM ET window
- ⚠️ Warns if outside window (but continues anyway)

**2. Environment Verification**
- ✅ Verifies .env file exists
- ✅ Checks all required credentials present

**3. Database Connectivity**
- ✅ Delegates to comprehensive health check system

**4. Comprehensive Health Check**
- ✅ Runs full 36-point system verification
- ✅ Reports: passed, warnings, failed counts

**5. Content Generator Verification**
- ✅ Morning brief generator exists
- ✅ Daily scorecard generator exists
- ✅ Twitter poster exists
- ✅ LinkedIn poster exists

**6. File System Check**
- ✅ All critical directories exist
- ✅ Write permissions verified

**7. Dependency & Service Check**
- ✅ Poetry available
- ✅ Python3 available

---

## 📊 RUNBOOK OUTPUTS

### On Console
```
================================================================================
🚀 LAUNCH DAY RUNBOOK
================================================================================
📅 Date: 2026-03-08
⏰ Time: 06:00:15 EST
🎯 Target: First post at 9:00 AM ET
📋 Log: /home/openclaw/.openclaw/workspace/optionsmagic/logs/launch_day_2026-03-08.log
================================================================================

[... checks run ...]

================================================================================
LAUNCH DAY VERIFICATION SUMMARY
================================================================================

Results:
  ✅ Passed:  28
  ⚠️  Warnings: 0
  ❌ Failed:  0

🟢 STATUS: READY FOR LAUNCH
   All systems operational. Go/No-Go: GO ✅

   Next step: Market opens at 9:30 AM
   Morning brief will post at 9:00 AM
   Daily scorecard will post at 4:00 PM
```

### In Log File
```
logs/launch_day_2026-03-08.log

Contains:
  • All checks with pass/fail status
  • Timestamp of execution
  • Full audit trail
  • Summary at end
```

---

## 🎯 EXIT CODES

| Code | Status | Meaning | Action |
|------|--------|---------|--------|
| **0** | 🟢 GO | All systems operational | Launch immediately ✅ |
| **1** | 🟡 CAUTION | Warnings present | Fix issues, re-run |
| **2** | 🔴 NO-GO | Critical failures | Do not launch ❌ |

### Check Exit Code
```bash
bash scripts/launch_day_runbook.sh
echo $?  # Prints 0, 1, or 2
```

---

## 📅 RECOMMENDED TIMELINE

### 6:00 AM ET
```bash
bash scripts/launch_day_runbook.sh
```

**Expected:** Exit code 0 (GO)

### 8:30 AM ET (30 minutes before market open)
```bash
bash scripts/launch_day_runbook.sh
```

**Expected:** Exit code 0 (GO)

If exit code is 0 at 8:30 AM → **PROCEED WITH LAUNCH** ✅

If exit code is 1 or 2 → **INVESTIGATE & FIX** before proceeding

---

## 🔍 UNDERSTANDING THE OUTPUT

### ✅ When You See Green (Passed Checks)
```
✅ Database connected and responding
✅ SUPABASE_URL configured
✅ Morning brief generator: ✅
```

Good! System is working.

### ⚠️ When You See Yellow (Warnings)
```
⚠️  TWITTER_API_KEY not set (will post fail if called)
⚠️  Health check: READY WITH CAUTION (check warnings)
```

These are usually expected (credentials due Mar 7).
Review them, but you can still proceed if no critical failures.

### ❌ When You See Red (Failures)
```
❌ .env file missing - cannot proceed
❌ Database connection failed
❌ Critical checks failed
```

**STOP!** Do not launch. Fix these issues first.

---

## 🛠️ TROUBLESHOOTING

### "Script not found"
```bash
# Make it executable first
chmod +x scripts/launch_day_runbook.sh

# Then run
bash scripts/launch_day_runbook.sh
```

### "Exit code 2 - No-Go"
```bash
# Check what failed
tail -100 logs/launch_day_2026-03-08.log

# Look for ❌ lines to see what failed
grep "❌" logs/launch_day_2026-03-08.log

# Fix the issues, then re-run
bash scripts/launch_day_runbook.sh
```

### "Python/Poetry not found"
```bash
# Ensure you're in the right directory
cd /home/openclaw/.openclaw/workspace/optionsmagic

# Verify poetry is installed
poetry --version

# If not, install via (ask system admin)
```

### "Database connection failed"
```bash
# Check .env has correct credentials
grep SUPABASE .env

# Verify network connectivity
ping supabase.com

# Check logs for details
tail -50 logs/launch_day_2026-03-08.log | grep -i database
```

---

## 📝 LOG FILE LOCATION

All runbook output is logged to:
```
logs/launch_day_YYYY-MM-DD.log
```

Example for Mar 8, 2026:
```
logs/launch_day_2026-03-08.log
```

### View Logs
```bash
# See latest log
tail -100 logs/launch_day_2026-03-08.log

# Search for failures
grep "❌" logs/launch_day_2026-03-08.log

# Full log
cat logs/launch_day_2026-03-08.log
```

---

## 🎯 LAUNCH DAY PROCEDURE

### 6:00 AM
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic
bash scripts/launch_day_runbook.sh
```
⏱️ Should take 1-2 minutes  
📊 Expected: All green  
🎯 Goal: Verify systems ready

### 8:30 AM (Go/No-Go Point)
```bash
bash scripts/launch_day_runbook.sh
```
📊 Expected: Still all green  
✅ If YES → Launch ✅  
❌ If NO → Stop and investigate

### 9:00 AM
Morning brief posts automatically ✅

### 4:00 PM
Daily scorecard posts automatically ✅

### 5:00 PM
Report results to Ananth

---

## 📊 WHAT GETS VERIFIED

### Critical Systems (Must Pass)
- ✅ .env file exists
- ✅ Database connectivity
- ✅ All generators present
- ✅ File system writable
- ✅ Poetry available

### Important Systems (Should Pass)
- ✅ Twitter poster exists
- ✅ LinkedIn poster exists
- ✅ All directories present
- ✅ Python available

### Optional (May Have Warnings)
- ⚠️ Twitter credentials (added by Zoe Mar 7)
- ⚠️ LinkedIn credentials (added by Zoe Mar 7)

---

## ✅ SUCCESS CRITERIA

Launch is **GO** when runbook returns:
```
Exit code: 0
Status: 🟢 READY FOR LAUNCH
Failures: 0
```

Launch is **CONDITIONAL** when runbook returns:
```
Exit code: 1
Status: 🟡 READY WITH CAUTION
Failures: 0 (but warnings exist)
```
→ Review warnings, fix if needed, re-run

Launch is **NO-GO** when runbook returns:
```
Exit code: 2
Status: 🔴 NOT READY
Failures: > 0
```
→ Do NOT proceed. Fix critical issues.

---

## 📞 SUPPORT

**Script not working?**
- Check if bash available: `bash --version`
- Check if in correct directory: `pwd` (should be optionsmagic root)
- Check log file for details: `tail -100 logs/launch_day_*.log`

**Don't understand output?**
- ✅ Green = good, continue
- ⚠️ Yellow = warning, usually OK but check
- ❌ Red = critical, must fix before launching

**Still stuck?**
- Review LAUNCH_DAY_CHECKLIST.md for step-by-step guide
- Check PRE_LAUNCH_HEALTH_CHECK_GUIDE.md for detailed checks
- Contact Max for technical issues

---

## 🎬 QUICK REFERENCE

### Run the runbook
```bash
bash scripts/launch_day_runbook.sh
```

### Check result
```bash
echo $?  # 0=GO, 1=CAUTION, 2=NO-GO
```

### View logs
```bash
tail -100 logs/launch_day_2026-03-08.log
```

### Find errors
```bash
grep "❌" logs/launch_day_2026-03-08.log
```

---

**Guide Created:** Saturday, February 28, 2026 — 4:15 PM ET  
**Status:** ✅ PRODUCTION READY  
**Next Use:** Saturday, March 8, 2026 @ 6:00 AM ET
