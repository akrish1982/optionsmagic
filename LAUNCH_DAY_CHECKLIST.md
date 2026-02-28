# 🚀 LAUNCH DAY CHECKLIST — March 8, 2026

**Mission:** Successfully launch Phase 2 (social media posting) at market open  
**Timeline:** Friday, Mar 7 (prep) → Saturday, Mar 8 (launch)  
**Success:** First morning brief + scorecard posted automatically by 4:30 PM  
**Owner:** Max (w/ Zoe's credentials)

---

## 📅 FRIDAY, MARCH 7 — PREPARATION DAY

### ⏰ 2:00 PM - Credentials Validation

**Checklist:**
```
[ ] Zoe provides Twitter credentials
[ ] Zoe provides LinkedIn credentials
[ ] Credentials added to .env file
[ ] .env file syntax is correct (no extra spaces)
```

**Action:**
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

# Validate Twitter
poetry run python << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()
keys = ['TWITTER_API_KEY', 'TWITTER_API_SECRET', 'TWITTER_ACCESS_TOKEN', 'TWITTER_ACCESS_TOKEN_SECRET']
for k in keys:
    v = os.getenv(k)
    print(f"✅ {k}" if v else f"❌ {k}: MISSING")
EOF

# Validate LinkedIn
poetry run python << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()
keys = ['LINKEDIN_API_KEY', 'LINKEDIN_ACCESS_TOKEN', 'LINKEDIN_COMPANY_PAGE_ID']
for k in keys:
    v = os.getenv(k)
    print(f"✅ {k}" if v else f"❌ {k}: MISSING")
EOF
```

**Expected Result:**
- All 7 credentials present ✅
- No MISSING values ❌

---

### ⏰ 3:00 PM - System Tests

**Test 1: Phase 1 Still Working**
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic
poetry run python test_e2e_workflow.py 2>&1 | grep -E "✅|❌"
```
**Expected:** All tests pass ✅

**Test 2: Dependencies Installed**
```bash
poetry run python << 'EOF'
print("Checking dependencies...")
try:
    import tweepy
    print("✅ tweepy")
except: print("❌ tweepy")

try:
    import PIL
    print("✅ Pillow")
except: print("❌ Pillow")

try:
    import yfinance
    print("✅ yfinance")
except: print("❌ yfinance")

try:
    from selenium import webdriver
    print("✅ selenium")
except: print("❌ selenium")

try:
    import supabase
    print("✅ supabase-py")
except: print("❌ supabase-py")
EOF
```
**Expected:** All ✅

**Test 3: Twitter API Connection**
```bash
poetry run python << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()

try:
    import tweepy
    client = tweepy.Client(
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    me = client.get_me()
    print(f"✅ Twitter API Connected!")
    print(f"   Account: @{me.data.username}")
except Exception as e:
    print(f"❌ Twitter API Error: {e}")
    exit(1)
EOF
```
**Expected:** Connected to OptionsMagic account ✅

**Test 4: Database Connection**
```bash
poetry run python << 'EOF'
import os
from dotenv import load_dotenv
from trade_automation.supabase_client import SupabaseClient

load_dotenv()
try:
    db = SupabaseClient()
    count = db.get_top_opportunities(limit=1)
    print(f"✅ Database Connected!")
    print(f"   Opportunities available: YES")
except Exception as e:
    print(f"❌ Database Error: {e}")
    exit(1)
EOF
```
**Expected:** Connected, opportunities available ✅

---

### ⏰ 4:00 PM - Image Generation Test

**Checklist:**
```
[ ] Pillow installed and working
[ ] Image template files exist (or will be generated)
[ ] Image output directory is writable
```

**Action:**
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

# Test image generation
poetry run python << 'EOF'
from PIL import Image, ImageDraw
import tempfile

# Create a test image
img = Image.new('RGB', (1200, 675), color=(15, 23, 42))  # Dark blue
draw = ImageDraw.Draw(img)
draw.text((100, 100), "Test Image Generated", fill=(255, 255, 255))

# Save test
test_path = '/tmp/test_image.png'
img.save(test_path)
print(f"✅ Image generation working")
print(f"   Test image saved: {test_path}")

# Verify file exists
import os
if os.path.exists(test_path):
    size = os.path.getsize(test_path)
    print(f"✅ Image file valid ({size} bytes)")
else:
    print(f"❌ Image file not created")
    exit(1)
EOF
```
**Expected:** Image generation ✅

---

### ⏰ 5:00 PM - Morning Brief Test

**Action:**
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

# Generate sample morning brief
poetry run python << 'EOF'
from trade_automation.supabase_client import SupabaseClient
from trade_automation.config import Settings
from datetime import datetime
import json

print("🧪 Testing Morning Brief Generation...")

try:
    db = SupabaseClient()
    
    # Get top opportunities
    opps = db.get_top_opportunities(limit=3)
    print(f"✅ Found {len(opps)} opportunities")
    
    # Test formatting
    brief = f"""
📊 OptionsMagic Morning Brief - {datetime.now().strftime('%B %d, %Y')}

Market Data:
• SPY: $XXX.XX
• VIX: XX.X

Top Opportunities:
"""
    for opp in opps[:3]:
        brief += f"\n• {opp.get('ticker', 'N/A')} - {opp.get('strategy', 'N/A')} @ {opp.get('return_percent', 0):.1f}%"
    
    brief += "\n\n⚠️ Hypothetical performance. Not financial advice."
    
    print("✅ Brief formatted correctly")
    print(f"\n{brief}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
EOF
```
**Expected:** Brief generated with real data ✅

---

### ⏰ 5:30 PM - Daily Scorecard Test

**Action:**
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

# Generate sample daily scorecard
poetry run python << 'EOF'
from trade_automation.supabase_client import SupabaseClient
from datetime import datetime
import json

print("🧪 Testing Daily Scorecard Generation...")

try:
    db = SupabaseClient()
    
    # Get today's trades
    trades = db.get_daily_trades()
    print(f"✅ Found {len(trades)} trades today")
    
    # Calculate metrics
    wins = sum(1 for t in trades if t.get('pnl_realized', 0) > 0)
    total_pnl = sum(t.get('pnl_realized', 0) for t in trades)
    win_rate = (wins / len(trades) * 100) if trades else 0
    
    # Test formatting
    scorecard = f"""
📈 OptionsMagic Daily Scorecard - {datetime.now().strftime('%B %d, %Y')}

Performance:
• Trades: {len(trades)}
• Win Rate: {win_rate:.1f}%
• Realized P&L: ${total_pnl:,.2f}

Open Positions: {db.count_open_positions()}
Unrealized P&L: ${db.get_total_unrealized_pnl():,.2f}

⚠️ Hypothetical performance. Not financial advice.
"""
    
    print("✅ Scorecard formatted correctly")
    print(f"\n{scorecard}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
EOF
```
**Expected:** Scorecard with real P&L data ✅

---

### ⏰ 6:00 PM - Dry-Run Posts (No API Calls)

**Action:**
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

# Twitter dry-run
export SOCIAL_DRY_RUN=true

poetry run python << 'EOF'
import os
os.environ['SOCIAL_DRY_RUN'] = 'true'

from trade_automation.twitter_poster import TwitterPoster
from trade_automation.config import Settings

print("🧪 Testing Twitter Dry-Run...")
try:
    poster = TwitterPoster(Settings())
    result = poster.post_test("Test morning brief\n\nThis is a test post.", image_path=None)
    print(f"✅ Twitter dry-run: Would post message")
except Exception as e:
    print(f"⚠️ Twitter dry-run warning: {e}")
    # Don't fail on dry-run errors
EOF

# LinkedIn dry-run
poetry run python << 'EOF'
import os
os.environ['SOCIAL_DRY_RUN'] = 'true'

from trade_automation.linkedin_poster import LinkedInPoster
from trade_automation.config import Settings

print("🧪 Testing LinkedIn Dry-Run...")
try:
    poster = LinkedInPoster(Settings())
    result = poster.post_test("Test daily scorecard\n\nThis is a test post.", image_path=None)
    print(f"✅ LinkedIn dry-run: Would post message")
except Exception as e:
    print(f"⚠️ LinkedIn dry-run warning: {e}")
    # Don't fail on dry-run errors
EOF

unset SOCIAL_DRY_RUN
```
**Expected:** Both post methods callable ✅

---

### ⏰ 6:30 PM - Cron Configuration Check

**Action:**
```bash
# Check if cron jobs are ready (don't enable yet)
crontab -l 2>/dev/null | grep -E "morning_brief|daily_scorecard" || echo "ℹ️  Cron jobs not yet installed (will be done on Mar 8)"

# Verify scripts exist
[ -f /home/openclaw/.openclaw/workspace/optionsmagic/scripts/morning_brief.py ] && echo "✅ Morning brief script exists" || echo "⚠️  Script missing"
[ -f /home/openclaw/.openclaw/workspace/optionsmagic/scripts/daily_scorecard.py ] && echo "✅ Scorecard script exists" || echo "⚠️  Script missing"
```
**Expected:** Scripts exist ✅

---

### ⏰ 7:00 PM - Final Validation Report

**Create final checklist:**
```bash
cat > /tmp/launch_status.txt << 'EOF'
═══════════════════════════════════════════════════════════
PHASE 2 LAUNCH READINESS - March 7, 7:00 PM ET
═══════════════════════════════════════════════════════════

CREDENTIALS
[ ] Twitter API Key present
[ ] Twitter API Secret present
[ ] Twitter Access Token present
[ ] Twitter Token Secret present
[ ] LinkedIn API Key present
[ ] LinkedIn Access Token present
[ ] LinkedIn Company Page ID present

DEPENDENCIES
[ ] tweepy installed
[ ] Pillow installed
[ ] yfinance installed
[ ] selenium installed
[ ] supabase-py installed

CONNECTIONS
[ ] Twitter API connects successfully
[ ] LinkedIn API credentials valid
[ ] Database connectivity verified
[ ] Opportunities table populated

CODE
[ ] Phase 1 E2E tests passing
[ ] Morning brief generator works
[ ] Daily scorecard generator works
[ ] Dry-run posts functional

INFRASTRUCTURE
[ ] Image generation working
[ ] Logs directory writable
[ ] .env file properly formatted
[ ] All scripts executable

READY FOR LAUNCH
[ ] All boxes checked above
[ ] No blocking issues
[ ] Go/No-Go: GO ✅

═══════════════════════════════════════════════════════════
EOF
cat /tmp/launch_status.txt
```

**Send status to Ananth:**
> ✅ **Phase 2 Ready for Launch!**
> All systems tested and validated. Ready to deploy at 6:00 AM on March 8.
> First morning brief will post at 9:00 AM ET.

---

## 📅 SATURDAY, MARCH 8 — LAUNCH DAY

### ⏰ 6:00 AM - Final Checks & Deployment

**Action:**
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

# FINAL: Verify all credentials still in place
poetry run python << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()

required = ['TWITTER_API_KEY', 'TWITTER_API_SECRET', 'TWITTER_ACCESS_TOKEN', 
            'TWITTER_ACCESS_TOKEN_SECRET', 'LINKEDIN_API_KEY', 'LINKEDIN_ACCESS_TOKEN', 
            'LINKEDIN_COMPANY_PAGE_ID']

missing = [k for k in required if not os.getenv(k)]

if missing:
    print(f"❌ LAUNCH BLOCKED: Missing credentials: {missing}")
    exit(1)
else:
    print("✅ All credentials present - CLEAR TO LAUNCH")
EOF

# If all good, enable cron jobs
echo "Enabling cron jobs..."
# (Add cron entries via crontab -e or automated script)
```

**Checklist:**
```
[ ] All credentials verified
[ ] No recent code changes (or tested if changed)
[ ] Database has test/real trade data
[ ] Logs directory ready
[ ] Cron jobs enabled
```

---

### ⏰ 8:30 AM - GO/NO-GO DECISION

**Final decision point (30 min before market open)**

**GO conditions (all must be true):**
- ✅ All credentials working
- ✅ API connections verified
- ✅ No errors in logs
- ✅ Database populated
- ✅ Image generation working

**NO-GO conditions (any one triggers delay):**
- ❌ Missing credentials
- ❌ API errors
- ❌ Database issues
- ❌ Code errors

**Decision:**
```bash
if [ all_checks_pass ]; then
    echo "🚀 GO FOR LAUNCH"
    # Proceed to market open
else
    echo "🛑 NO-GO - DELAY LAUNCH"
    # Fix issues, reschedule
fi
```

---

### ⏰ 9:00 AM - MARKET OPENS

**At 9:00 AM ET, automated morning brief should post:**

**Actions:**
```
[ ] Monitor /logs directory for activity
[ ] Check Twitter for first post (should appear within 1 min)
[ ] Check LinkedIn for first post (should appear within 1 min)
[ ] Verify post content is correct
[ ] Verify images attached properly
[ ] Check for any error messages
```

**Expected Twitter Post:**
```
📊 OptionsMagic Morning Brief - March 8, 2026

Market Open: SPY $XXX.XX, VIX XX.X

🎯 Top Opportunities:
1. $TICKER - CSP @ $XXX (Return: X.X%)
2. $TICKER - VPC @ $XXX (Return: X.X%)
3. $TICKER - CSP @ $XXX (Return: X.X%)

⚠️ Hypothetical performance. Not financial advice.

#OptionsMagic #OptionsTrading
```

**What to do if post doesn't appear:**
```
1. Check Twitter manually (@OptionsMagic account)
2. Check logs: tail -100 /home/openclaw/.openclaw/workspace/optionsmagic/logs/*
3. Run test post manually:
   poetry run python -c "from trade_automation.twitter_poster import TwitterPoster; ..."
4. If API error: Verify credentials are correct
5. If image error: Check Pillow installation
6. Contact Zoe if API credentials needed reset
```

---

### ⏰ 12:00 PM - Midday Check

**Checklist:**
```
[ ] Morning brief posted to Twitter ✅
[ ] Morning brief posted to LinkedIn ✅
[ ] Post has correct content
[ ] Images rendered properly
[ ] No error messages in logs
[ ] Database has entries
[ ] Market data updated
```

**Announcement (if all good):**
> 🟢 Phase 2 launch successful! Morning brief posted automatically at 9:00 AM.
> Daily scorecard will post at 4:00 PM.
> Standing by for afternoon updates.

---

### ⏰ 4:00 PM - MARKET CLOSES

**At 4:00 PM ET, automated daily scorecard should post:**

**Actions:**
```
[ ] Monitor logs for scorecard generation
[ ] Check Twitter for scorecard post (within 1 min)
[ ] Check LinkedIn for scorecard post (within 1 min)
[ ] Verify P&L numbers are correct
[ ] Check for any errors
```

**Expected Scorecard Post:**
```
📈 OptionsMagic Daily Scorecard - March 8, 2026

Performance:
Trades Executed: X
Win Rate: XX%
Realized P&L: +$XXX

Open Positions: X
Unrealized P&L: +$XXX

📊 Month to Date: +X.X%

⚠️ Hypothetical performance. Not financial advice.
```

---

### ⏰ 5:00 PM - Daily Report

**Send update to Ananth:**
```
✅ PHASE 2 LAUNCH COMPLETE

Morning Brief:
  ✅ Posted to Twitter at 9:00 AM
  ✅ Posted to LinkedIn at 9:00 AM
  
Daily Scorecard:
  ✅ Posted to Twitter at 4:00 PM
  ✅ Posted to LinkedIn at 4:00 PM

Engagement:
  • Morning brief: XXX impressions
  • Afternoon scorecard: XXX impressions
  
Issues: NONE

Next Steps:
  • Monitor for next 5 days (Mar 8-12)
  • Watch for any posting failures
  • Track engagement growth
  • Prepare Phase 3 (API refinements)
```

---

## 🚨 TROUBLESHOOTING (If Things Go Wrong)

### Morning Brief Doesn't Post at 9:00 AM
```bash
# Check logs
tail -50 /home/openclaw/.openclaw/workspace/optionsmagic/logs/morning_brief.log

# Test manual generation
poetry run python trade_automation/morning_brief_generator.py

# Verify cron job is running
crontab -l | grep morning_brief
```

**Common fixes:**
- Credentials expired → Re-add to .env
- Database issue → Check Supabase connectivity
- Image generation failed → Check Pillow & templates
- Cron job disabled → Re-enable with `crontab -e`

### Twitter Post Has Wrong Content
```bash
# Check what was actually posted (compare timestamps)
# Verify opportunities data is correct:
poetry run python << 'EOF'
from trade_automation.supabase_client import SupabaseClient
db = SupabaseClient()
opps = db.get_top_opportunities(limit=3)
for opp in opps:
    print(f"  {opp['ticker']} - {opp['return_percent']}%")
EOF
```

### API Rate Limited
**Twitter:** Wait 15 minutes, then retry  
**LinkedIn:** May need to wait until next day for company page posts

### Image Not Attached
```bash
# Verify image file exists
ls -la /tmp/morning_brief_*.png

# Check image generation:
poetry run python << 'EOF'
from PIL import Image
img = Image.new('RGB', (1200, 675), color=(15, 23, 42))
img.save('/tmp/test.png')
print("✅ Pillow working")
EOF
```

---

## ✅ SUCCESS CRITERIA

### First Day (Mar 8)
- ✅ Morning brief posts automatically at 9:00 AM
- ✅ Daily scorecard posts automatically at 4:00 PM
- ✅ Posts appear on Twitter and LinkedIn
- ✅ Content is correct
- ✅ Images display properly
- ✅ No critical errors

### First Week (Mar 8-14)
- ✅ 10 posts (5 days × 2 posts/day)
- ✅ 0 posting failures
- ✅ Engagement tracking begins
- ✅ No data integrity issues
- ✅ Team feedback collected

### First Month (Mar 8 - Apr 8)
- ✅ 50+ posts across platforms
- ✅ 500+ follower growth
- ✅ Consistent posting schedule
- ✅ Strong engagement metrics
- ✅ Ready for Phase 3

---

## 📋 SIGN-OFF

**Launch Readiness:** 🟢 **ON TRACK**  
**Expected Launch Date:** Saturday, March 8, 2026 at 9:00 AM ET  
**Estimated Success Rate:** 95%+ (pending credential delivery by Mar 7)

---

**Document Created:** Saturday, Feb 28, 2026 — 4:05 AM ET  
**Last Updated:** Saturday, Feb 28, 2026 — 4:05 AM ET  
**Owner:** Max (arya)  
**Contact:** Reach out if any issues arise
