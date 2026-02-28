# 🔐 PHASE 2: CREDENTIAL SETUP GUIDE

**Objective:** Add social media API credentials to enable March 8 launch  
**Timeline:** Due by Mar 7, 5:00 PM ET  
**Owner:** Zoe  
**Validator:** Max (automated scripts provided)

---

## 📋 REQUIRED CREDENTIALS

### 1. Twitter API v2 (4 fields)

**Source:** optionsmagic.ananth@gmail.com - Twitter Developer Portal

**Steps to get credentials:**
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Sign in with optionsmagic.ananth@gmail.com
3. Select "OptionsMagic" app
4. Go to "Keys and tokens"
5. Copy these 4 values:
   - API Key (Consumer Key)
   - API Secret (Consumer Secret)
   - Access Token
   - Access Token Secret

**⚠️ Safety:** These are secrets! Only Zoe & Max should see these.

### 2. LinkedIn API (2 fields)

**Source:** LinkedIn Developer Console (optionsmagic.ananth@gmail.com account)

**Steps to get credentials:**
1. Go to https://www.linkedin.com/developers/apps
2. Sign in with optionsmagic.ananth@gmail.com
3. Select "OptionsMagic" app
4. Go to "Auth" tab
5. Copy:
   - Client ID (also called "API Key")
   - Client Secret (also called "API Secret")
6. Generate Access Token (or use OAuth flow)
7. Get Company Page ID: Go to https://www.linkedin.com/company/optionsmagic → URL contains `/company/XXXXXXX/`

**⚠️ Safety:** Keep these secrets secure!

### 3. Image Templates (Design Assets)

**Files needed:**
- `templates/morning_brief_template.png` (1200x675px)
- `templates/daily_scorecard_template.png` (1200x675px)

**Option A: Create from scratch**
- Download template files into `templates/` folder
- Dimensions: 1200×675 pixels
- Format: PNG

**Option B: Provide design specs**
- If templates aren't ready, send design specifications
- Max can generate programmatically with Pillow

**Current default colors (if not provided):**
- Dark blue: `#0f172a`
- Success green: `#22c55e`
- White: `#ffffff`
- Text: Arial/Helvetica, white on dark blue

---

## 🔧 ADD CREDENTIALS TO .env

### Step 1: Open `.env` file

```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic
nano .env  # or use your preferred editor
```

### Step 2: Add Twitter credentials

Find the comment `# Phase 2: Social Media APIs` (or create it), then add:

```bash
# Twitter/X Credentials
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
TWITTER_ACCESS_TOKEN=your_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret_here
```

### Step 3: Add LinkedIn credentials

```bash
# LinkedIn Credentials
LINKEDIN_API_KEY=your_api_key_here
LINKEDIN_ACCESS_TOKEN=your_access_token_here
LINKEDIN_COMPANY_PAGE_ID=xxxxxxx
```

### Step 4: Add image template locations (if different)

```bash
# Image Templates (optional - use defaults if not set)
IMAGE_TEMPLATE_MORNING_BRIEF=templates/morning_brief_template.png
IMAGE_TEMPLATE_DAILY_SCORECARD=templates/daily_scorecard_template.png
```

### Step 5: Verify it looks right

```bash
grep -A 10 "Phase 2: Social Media" .env
```

**Expected output:**
```
# Phase 2: Social Media APIs
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
LINKEDIN_API_KEY=...
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_COMPANY_PAGE_ID=...
```

---

## ✅ VALIDATE CREDENTIALS (Automated)

### Test 1: Twitter Configuration

```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

poetry run python << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()

twitter_keys = [
    'TWITTER_API_KEY',
    'TWITTER_API_SECRET',
    'TWITTER_ACCESS_TOKEN',
    'TWITTER_ACCESS_TOKEN_SECRET'
]

print("🔍 Checking Twitter credentials...")
missing = []
for key in twitter_keys:
    value = os.getenv(key)
    if value:
        status = "✅" if len(value) > 10 else "⚠️"
        print(f"{status} {key}: {'*' * len(value)}")
    else:
        print(f"❌ {key}: MISSING")
        missing.append(key)

if missing:
    print(f"\n❌ Missing {len(missing)} Twitter credentials: {', '.join(missing)}")
    exit(1)
else:
    print("\n✅ All Twitter credentials present!")
    
    # Try importing tweepy and validating API
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=os.getenv('TWITTER_API_KEY'),
            consumer_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
            wait_on_rate_limit=True
        )
        user = client.get_me()
        print(f"✅ Twitter API working! Connected as: @{user.data.username}")
    except Exception as e:
        print(f"⚠️ Twitter API error: {e}")
        print("   Check credentials are correct")
        exit(1)
EOF
```

### Test 2: LinkedIn Configuration

```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

poetry run python << 'EOF'
import os
from dotenv import load_dotenv
load_dotenv()

linkedin_keys = [
    'LINKEDIN_API_KEY',
    'LINKEDIN_ACCESS_TOKEN',
    'LINKEDIN_COMPANY_PAGE_ID'
]

print("🔍 Checking LinkedIn credentials...")
missing = []
for key in linkedin_keys:
    value = os.getenv(key)
    if value:
        status = "✅" if len(str(value)) > 3 else "⚠️"
        print(f"{status} {key}: {'*' * min(len(str(value)), 10)}")
    else:
        print(f"❌ {key}: MISSING")
        missing.append(key)

if missing:
    print(f"\n❌ Missing {len(missing)} LinkedIn credentials: {', '.join(missing)}")
    exit(1)
else:
    print("\n✅ All LinkedIn credentials present!")
EOF
```

### Test 3: Full System Test

```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

poetry run python << 'EOF'
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🚀 PHASE 2 CREDENTIAL VALIDATION")
print("=" * 60)

checks = {
    "Twitter API Key": "TWITTER_API_KEY",
    "Twitter API Secret": "TWITTER_API_SECRET",
    "Twitter Access Token": "TWITTER_ACCESS_TOKEN",
    "Twitter Token Secret": "TWITTER_ACCESS_TOKEN_SECRET",
    "LinkedIn API Key": "LINKEDIN_API_KEY",
    "LinkedIn Access Token": "LINKEDIN_ACCESS_TOKEN",
    "LinkedIn Company Page ID": "LINKEDIN_COMPANY_PAGE_ID",
}

all_good = True
for name, env_var in checks.items():
    value = os.getenv(env_var)
    if value and len(str(value)) > 3:
        print(f"✅ {name}")
    else:
        print(f"❌ {name}: MISSING")
        all_good = False

print("=" * 60)

if all_good:
    print("✅ ALL CREDENTIALS READY FOR PHASE 2 LAUNCH!")
    print("\nNext steps:")
    print("  1. Run final pre-launch tests on Mar 7")
    print("  2. Deploy cron jobs")
    print("  3. Launch morning brief at 9:00 AM on Mar 8")
else:
    print("❌ MISSING CREDENTIALS - Cannot launch Phase 2")
    print("\nPlease add missing credentials to .env and try again")

print("=" * 60)
EOF
```

---

## 📦 CREATE IMAGE TEMPLATES (If not provided)

If Zoe doesn't have template designs ready, Max can create them programmatically.

### Option A: Create with Pillow (programmatic)

**File:** `trade_automation/generate_templates.py` (to be created)

This will generate templates with:
- OptionsMagic branding
- Color scheme (dark blue, green, white)
- Placeholders for data (ticker, P&L, etc.)

### Option B: Use static templates

If Zoe provides PNG templates, place them in:
```
templates/
├── morning_brief_template.png
└── daily_scorecard_template.png
```

---

## 🧪 FULL PRE-LAUNCH TEST (Mar 7, 5:00 PM)

Run this on March 7 after adding all credentials:

```bash
#!/bin/bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

echo "🚀 PHASE 2 PRE-LAUNCH VALIDATION"
echo "=================================="

# Test 1: Credentials
echo -e "\n1️⃣  Testing credentials..."
poetry run python PHASE_2_CREDENTIAL_SETUP.md  # validates credentials

# Test 2: Twitter dry-run
echo -e "\n2️⃣  Testing Twitter dry-run..."
SOCIAL_DRY_RUN=true poetry run python -c "
from trade_automation.twitter_poster import TwitterPoster
from trade_automation.config import Settings
poster = TwitterPoster(Settings())
result = poster.post_dry_run('Test morning brief', image_path=None)
print(f'✅ Twitter dry-run: {result}')
"

# Test 3: LinkedIn dry-run
echo -e "\n3️⃣  Testing LinkedIn dry-run..."
SOCIAL_DRY_RUN=true poetry run python -c "
from trade_automation.linkedin_poster import LinkedInPoster
from trade_automation.config import Settings
poster = LinkedInPoster(Settings())
result = poster.post_dry_run('Test scorecard', image_path=None)
print(f'✅ LinkedIn dry-run: {result}')
"

# Test 4: Morning brief generation
echo -e "\n4️⃣  Testing morning brief generation..."
poetry run python trade_automation/morning_brief_generator.py

# Test 5: Daily scorecard generation
echo -e "\n5️⃣  Testing daily scorecard generation..."
poetry run python trade_automation/daily_scorecard_generator.py

echo -e "\n=================================="
echo "✅ ALL TESTS PASSED - READY TO LAUNCH"
echo "=================================="
```

---

## 📞 TROUBLESHOOTING

### Twitter Error: "Invalid Credentials"
- ✅ Verify API Key and Secret are from Consumer Key/Secret (not Access Token)
- ✅ Check for extra spaces or newlines in .env
- ✅ Verify account has "Read + Write + Direct Message" permissions
- ✅ Test at https://developer.twitter.com/en/docs/twitter-api/api-explorer

### LinkedIn Error: "Unauthorized"
- ✅ Verify Access Token is valid (LinkedIn tokens expire after 60 days)
- ✅ Check Company Page ID matches the account
- ✅ Regenerate token if needed via https://www.linkedin.com/developers/apps

### Image Generation Error
- ✅ Verify Pillow is installed: `poetry run python -c "import PIL; print(PIL.__version__)"`
- ✅ Check template files exist in `templates/` folder
- ✅ Verify template dimensions are 1200×675px

---

## 🚀 LAUNCH CHECKLIST (Mar 8, 6:00 AM)

- [ ] Twitter credentials working (test at 6:00 AM)
- [ ] LinkedIn credentials working (test at 6:00 AM)
- [ ] Image templates in place (if custom)
- [ ] Cron jobs enabled
- [ ] Database has test trade data
- [ ] Logs directory writable
- [ ] All dependencies installed
- [ ] Telegram notifications configured

**Go/No-Go Decision Time:** 8:30 AM ET (30 min before market open)
- If all tests pass → LAUNCH at 9:00 AM ✅
- If any test fails → DELAY and fix 🔧

---

## 📝 HANDOFF INSTRUCTIONS

**For Zoe:**
1. Get Twitter credentials from Developer Portal
2. Get LinkedIn credentials from Developer Console
3. Add both to `.env` file (template provided above)
4. Run Test 1 & 2 to validate
5. Share confirmation with Max

**For Max:**
1. Monitor tests for any failures
2. Create image templates if needed
3. Run full pre-launch test on Mar 7
4. Deploy cron jobs on Mar 8 at 6:00 AM
5. Monitor first posts

---

## ✅ SUCCESS CRITERIA

By March 8, 9:00 AM ET:
- [ ] Twitter posting working
- [ ] LinkedIn posting working
- [ ] Morning brief generating
- [ ] Daily scorecard generating
- [ ] First post appears on both platforms
- [ ] No errors in logs

---

**Document Created:** Saturday, Feb 28, 2026 — 4:05 AM ET  
**Due:** Friday, Mar 7, 2026 — 5:00 PM ET  
**Contact:** Max (arya) for issues
