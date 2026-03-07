# 📊 SATURDAY MONITORING GUIDE
**For Live Launch Day - March 8, 2026**

**Purpose:** Real-time monitoring checklist during market hours to catch issues immediately.

---

## ⏰ TIMELINE & KEY WINDOWS

### 6:00 AM - Pre-Market Prep (30 min)
- [ ] Verify all credentials loaded
- [ ] Test API connections
- [ ] Check logs are clear

### 8:30 AM - Go/No-Go Decision (15 min before open)
- [ ] All tests passing? YES → Proceed to 9:00 AM
- [ ] Any issues? NO → Fix and re-run tests

### 9:00 AM - MARKET OPENS (Critical First Hour)
**MONITOR THESE SIGNALS:**
- [ ] Morning brief starts generating
- [ ] Check logs for no errors
- [ ] Watch for first Twitter post
- [ ] Watch for first LinkedIn post

### 9:15 AM - First Trade Proposal
- [ ] Proposal arrives in Telegram
- [ ] Content looks correct
- [ ] Buttons work (APPROVE/REJECT)

### 9:15 AM - 4:00 PM - Continuous Operation
- [ ] Position monitoring every 5 min
- [ ] Exit automation checks
- [ ] No critical errors

### 4:00 PM - Market Closes
- [ ] Scorecard generation starts
- [ ] Watch for posts appear

### 5:00 PM - End of Day
- [ ] Send summary report to Ananth

---

## 🔍 REAL-TIME MONITORING TERMINAL

Keep this terminal open during market hours:

```bash
# Terminal 1: Watch Logs (Live Updates)
cd /home/openclaw/.openclaw/workspace/optionsmagic
tail -f logs/morning_brief.log logs/daily_scorecard.log logs/position_manager.log 2>/dev/null

# Terminal 2: Check Cron Jobs (Status)
watch -n 5 'crontab -l | grep -E "morning_brief|daily_scorecard|propose_trades|position_manager"'

# Terminal 3: Monitor Posts (If can access Twitter API)
# Will show recent posts to @OptionsMagic account
```

---

## 📋 MONITORING CHECKLIST

### 9:00 AM Window (Morning Brief)

**Signal to Expect:**
```
✅ Logs show: "Starting morning_brief_generator"
✅ Within 1 min: Image file created at /tmp/morning_brief_*.png
✅ Within 2 min: Tweet posted to Twitter (if credentials working)
✅ Within 2 min: Post published to LinkedIn (if credentials working)
```

**If no signal:**
```bash
# Check logs immediately
tail -20 logs/morning_brief.log

# If error, check:
1. Credentials present? env | grep TWITTER
2. Network working? ping -c 1 twitter.com
3. API rate limited? Check Twitter dashboard
4. Image generation failed? Check /tmp/morning_brief_*.png exists
```

### 9:15 AM Window (First Trade Proposal)

**Signal to Expect:**
```
✅ Telegram message arrives with trade details
✅ Shows: Ticker, Strategy, Risk/Return, Buttons
✅ Buttons are responsive (APPROVE/REJECT clickable)
```

**If no signal:**
```bash
# Check logs
tail -20 logs/proposal_worker.log
tail -20 logs/telegram.log

# If error, check:
1. Telegram bot token valid? Test with manual message
2. Database connectivity? Check opportunities table has data
3. Opportunity scoring working? Check data quality
```

### 4:00 PM Window (Daily Scorecard)

**Signal to Expect:**
```
✅ Logs show: "Starting daily_scorecard_generator"
✅ Within 1 min: Scorecard image created
✅ Within 2 min: Posts appear on Twitter & LinkedIn
✅ Shows: Win rate, P&L, open positions
```

**If no signal:**
```bash
# Check logs
tail -20 logs/daily_scorecard.log

# Common issues:
1. No trades executed today? Scorecard will show 0s (this is OK)
2. P&L calculation error? Check trade_history table
3. Image styling wrong? Check Pillow version: python -c "import PIL; print(PIL.__version__)"
```

---

## 🚨 EMERGENCY PROCEDURES

### Issue: Posts Not Appearing on Twitter

**Quick Diagnose (2 min):**
```bash
# 1. Check credentials loaded
grep TWITTER .env

# 2. Check logs for errors
tail -50 logs/twitter_poster.log | grep -E "ERROR|Exception"

# 3. Check if rate limited
# Twitter limits: 300 posts/3 hours. We only do 2 posts/day, so unlikely.

# 4. Test Twitter API manually
poetry run python << 'EOF'
import os
from dotenv import load_dotenv
import tweepy

load_dotenv()
try:
    client = tweepy.Client(
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    me = client.get_me()
    print(f"✅ Connected to @{me.data.username}")
except Exception as e:
    print(f"❌ Error: {e}")
EOF
```

**If API test passes:** Posts are getting posted. Check Twitter manually.  
**If API test fails:** Credentials are bad. Get fresh ones from Zoe.

### Issue: Posts Not Appearing on LinkedIn

**Quick Diagnose (2 min):**
```bash
# Check logs
tail -50 logs/linkedin_poster.log | grep -E "ERROR|Exception"

# LinkedIn uses browser automation (Selenium)
# Check if browser is working:
poetry run python << 'EOF'
try:
    from selenium import webdriver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.quit()
    print("✅ Selenium/Chrome working")
except Exception as e:
    print(f"❌ Error: {e}")
EOF
```

**If Selenium works:** LinkedIn server issue or auth problem. Check logs.  
**If Selenium fails:** Chrome or webdriver not installed. Not critical for MVP.

### Issue: First Trade Proposal Never Arrives

**Quick Diagnose (3 min):**
```bash
# 1. Check if proposal_worker ran
grep -l "proposal_worker" logs/*

# 2. Check for proposals generated
tail -20 logs/proposal_worker.log

# 3. Verify opportunities exist
poetry run python << 'EOF'
from trade_automation.supabase_client import SupabaseClient
db = SupabaseClient()
opps = db.get_top_opportunities(limit=1)
print(f"Opportunities available: {len(opps) > 0}")
EOF

# 4. Test Telegram manually
poetry run python << 'EOF'
from trade_automation.notifier_telegram import TelegramNotifier
notifier = TelegramNotifier()
notifier.send_message("Test: OptionsMagic is live and running 🚀")
EOF
```

**If test message sends:** Telegram working, proposals issue is data/logic.  
**If test fails:** Telegram credentials bad. Get fresh token.

### Issue: Position Monitoring Not Running

**Check:**
```bash
# Verify cron job is active
crontab -l | grep exit_automation

# Check if it ran in last 5 minutes
ls -la logs/position_manager.log
stat logs/position_manager.log | grep Modify

# Check last 5 lines
tail -5 logs/position_manager.log
```

**If recent:** Monitoring is running.  
**If old:** Re-run cron setup: `bash scripts/setup_cron_jobs.sh`

---

## 📊 WHAT NORMAL LOOKS LIKE

### Log Example - Everything Working

```
2026-03-08 09:00:00 - INFO - Starting morning_brief_generator
2026-03-08 09:00:05 - INFO - Fetched SPY: $445.23
2026-03-08 09:00:10 - INFO - Fetched VIX: 18.5
2026-03-08 09:00:15 - INFO - Got 3 opportunities from database
2026-03-08 09:00:20 - INFO - Generated image: /tmp/morning_brief_2026-03-08.png
2026-03-08 09:00:25 - INFO - ✅ Twitter API Connected
2026-03-08 09:00:30 - INFO - Posted to Twitter: Tweet ID 1234567890
2026-03-08 09:00:35 - INFO - ✅ LinkedIn post published
2026-03-08 09:00:40 - INFO - Morning brief complete (40 sec)
```

### Log Example - Error Handling

```
2026-03-08 09:00:00 - INFO - Starting morning_brief_generator
2026-03-08 09:00:05 - WARNING - Could not fetch real-time VIX, using fallback: 18.0
2026-03-08 09:00:15 - INFO - Got 3 opportunities from database
2026-03-08 09:00:20 - INFO - Generated image: /tmp/morning_brief_2026-03-08.png
2026-03-08 09:00:25 - WARNING - Twitter rate limit approaching, will retry at 09:01
2026-03-08 09:00:35 - INFO - ✅ LinkedIn post published
2026-03-08 09:01:00 - INFO - ✅ Twitter post published (retried)
```

---

## 🎯 KEY METRICS TO TRACK

**During 9:00 AM - 4:00 PM:**

| Metric | Status | Note |
|--------|--------|------|
| Morning Brief Posted | ✅/⏳/❌ | Should be within 1 min of 9:00 AM |
| First Trade Proposal | ✅/⏳/❌ | Should arrive by 9:15 AM |
| Position Monitoring | ✅/⏳/❌ | Runs every 5 min (should see logs) |
| Daily Scorecard Posted | ✅/⏳/❌ | Should be within 1 min of 4:00 PM |
| Critical Errors | 0 | Check logs for "ERROR" or "CRITICAL" |
| Posts to Twitter | 2 | Morning brief + scorecard |
| Posts to LinkedIn | 2 | Morning brief + scorecard |
| Trades Executed | ? | Depends on approvals |

---

## 📞 ESCALATION CONTACTS

**Issue Type → Contact**

- **Telegram not working** → Check notifier_telegram.py logs
- **Twitter credentials bad** → Contact Zoe immediately
- **LinkedIn credentials bad** → Contact Zoe immediately
- **Database connectivity** → Check Supabase status
- **Cron jobs not running** → Re-run setup_cron_jobs.sh
- **Trade execution issue** → Check tradestation.py logs
- **Anything unclear** → Contact Ananth via Telegram

---

## 💾 LOG FILES TO MONITOR

```
logs/
├── morning_brief.log         ← Morning brief generation
├── daily_scorecard.log       ← End-of-day scorecard
├── twitter_poster.log        ← Twitter API calls
├── linkedin_poster.log       ← LinkedIn posting
├── proposal_worker.log       ← Trade proposals
├── approval_worker.log       ← Telegram approvals
├── position_manager.log      ← Position tracking
├── exit_automation.log       ← Exit automation
├── tradestation.log          ← Trade execution
└── telegram.log              ← Telegram notifications
```

**Monitor with:**
```bash
tail -f logs/*.log | grep -E "ERROR|WARNING|Posted|Generated"
```

---

## ✅ PRE-9:00 AM CHECKLIST

Run this at 8:30 AM to ensure everything is ready:

```bash
#!/bin/bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

echo "🔍 PRE-LAUNCH VERIFICATION - 8:30 AM"
echo "===================================="

# 1. Check all logs are writable
echo -n "Logs writable: "
[ -w logs/ ] && echo "✅" || echo "❌"

# 2. Check credentials present
echo -n "Twitter credentials: "
grep -q "TWITTER_API_KEY" .env && echo "✅" || echo "❌"

echo -n "LinkedIn credentials: "
grep -q "LINKEDIN_API_KEY" .env && echo "✅" || echo "❌"

# 3. Check cron jobs
echo -n "Cron jobs configured: "
crontab -l 2>/dev/null | grep -q "morning_brief" && echo "✅" || echo "❌"

# 4. Test image generation
echo -n "Image generation: "
poetry run python << 'EOF' 2>/dev/null
from PIL import Image
img = Image.new('RGB', (100, 100))
img.save('/tmp/test.png')
print("✅")
EOF
[ $? -eq 0 ] || echo "❌"

# 5. Final decision
echo ""
echo "=================================="
echo "🟢 GO FOR LAUNCH (all ✅)"
echo "OR"
echo "🔴 DO NOT LAUNCH (any ❌)"
echo "=================================="
```

---

## 📝 NOTES FOR ANANTH

**Send this summary at 5:00 PM:**

```
Subject: OptionsMagic Launch Day Summary - March 8

Hi Ananth,

LAUNCH DAY REPORT:
✅ Morning brief posted at 9:00 AM
✅ First trade proposal at 9:15 AM
✅ Daily scorecard posted at 4:00 PM
✅ [X] trades executed today
✅ Win rate: [X]%
✅ Realized P&L: +$[X]

METRICS:
- Twitter posts: 2
- LinkedIn posts: 2
- Telegram notifications: [X]
- Approval flow: Working
- Position tracking: Real-time monitoring active

ISSUES: [None / list any]

NEXT STEPS:
- Continue monitoring Monday
- Phase 4 viability testing starts April 5
- Target: 30+ trades by April 30

Ready for week 2 of Phase 2!

-Max
```

---

**Document Created:** Friday, March 6, 2026 — 10:15 PM ET  
**Purpose:** Real-time monitoring during live launch  
**Next Review:** Saturday morning at 6:00 AM ET
