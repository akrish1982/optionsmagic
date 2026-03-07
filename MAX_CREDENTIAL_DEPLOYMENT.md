# 🚀 MAX'S CREDENTIAL DEPLOYMENT PROCEDURE
**Created:** Saturday, March 7, 2026 @ 4:08 AM EST  
**Status:** READY FOR DEPLOYMENT (waiting for Zoe)  
**Owner:** Max  
**Timeline:** Can deploy in <5 minutes once credentials arrive

---

## 📋 REQUIRED CREDENTIALS (From Zoe)

When Zoe provides these 7 values, you'll add them to `.env`:

### Twitter API v2 (4 values)
```
TWITTER_API_KEY = [Consumer Key]
TWITTER_API_SECRET = [Consumer Secret]
TWITTER_ACCESS_TOKEN = [Access Token]
TWITTER_ACCESS_TOKEN_SECRET = [Access Token Secret]
```

### LinkedIn API (2 values + Company Page ID)
```
LINKEDIN_API_KEY = [Client ID]
LINKEDIN_ACCESS_TOKEN = [Access Token]
LINKEDIN_COMPANY_PAGE_ID = [Company Page ID number]
```

---

## ✅ DEPLOYMENT CHECKLIST (When Credentials Arrive)

### Step 1: Add Credentials to .env (2 minutes)
```bash
cd /home/openclaw/.openclaw/workspace/optionsmagic

# Add these lines to .env:
cat >> .env << 'EOF'

# Phase 2: Social Media APIs (Added by Max on $(date +%Y-%m-%d))
TWITTER_API_KEY=YOUR_API_KEY
TWITTER_API_SECRET=YOUR_API_SECRET
TWITTER_ACCESS_TOKEN=YOUR_ACCESS_TOKEN
TWITTER_ACCESS_TOKEN_SECRET=YOUR_ACCESS_TOKEN_SECRET
LINKEDIN_API_KEY=YOUR_LINKEDIN_API_KEY
LINKEDIN_ACCESS_TOKEN=YOUR_LINKEDIN_ACCESS_TOKEN
LINKEDIN_COMPANY_PAGE_ID=YOUR_COMPANY_PAGE_ID
EOF
```

### Step 2: Validate Credentials (1 minute)
```bash
python3 scripts/inject_and_validate_credentials.py

# Expected output:
# ✅ Twitter credentials validated
# ✅ LinkedIn credentials validated
# ✅ All credentials ready for deployment
```

### Step 3: Deploy Phase 2 (1 minute)
```bash
# Activate cron jobs for social media posting
python3 -c "from trade_automation.social_media_orchestrator import activate_phase2; activate_phase2()"

# Verify cron jobs:
crontab -l | grep -E "morning_brief|daily_scorecard"
```

### Step 4: Run First Dry-Run Test (1 minute)
```bash
# Generate morning brief (dry-run, no actual post)
python3 trade_automation/morning_brief_generator.py --dry-run

# Generate daily scorecard (dry-run, no actual post)
python3 trade_automation/daily_scorecard_generator.py --dry-run

# Expected: Images created in /tmp/ directory
ls -la /tmp/morning_brief_*.png
ls -la /tmp/daily_scorecard_*.png
```

### Step 5: Confirm Live Posting Ready (1 minute)
```bash
# Check that posting is enabled
grep -i "DRY_RUN\|LIVE_POSTING" .env | head -5

# Should see: LIVE_POSTING=true (or similar)
```

---

## 🎯 SUCCESS CRITERIA

After deployment, verify:

- [ ] ✅ Morning Brief Generator: Ready to post to Twitter + LinkedIn at 9 AM
- [ ] ✅ Daily Scorecard Generator: Ready to post to Twitter + LinkedIn at 4 PM
- [ ] ✅ All cron jobs active and verified
- [ ] ✅ Dry-run images generated successfully
- [ ] ✅ .env credentials loaded without errors
- [ ] ✅ Both APIs responding to connection test

---

## ⏱️ TIMELINE

| Phase | Task | Timeline | Status |
|-------|------|----------|--------|
| **Phase 1** | Trade Execution | LIVE NOW | ✅ ACTIVE |
| **Phase 2** | Social Media | Mon Mar 8 @ 9 AM | ⏳ WAITING |
| **Phase 3** | Viability Test | Apr 5 - Apr 30 | 📅 SCHEDULED |

---

## 📞 COMMUNICATION

**When Zoe sends credentials:**
1. Max receives message
2. Max runs this checklist (5 minutes)
3. Phase 2 goes LIVE
4. Ananth gets notification with confirmation
5. Trading automation posts first content at 9 AM Monday

---

## 🔐 SECURITY NOTES

- Credentials are secrets - keep in .env, NEVER in git
- .env is in .gitignore (verified ✅)
- Only Max and Ananth should handle deployment
- After deployment, credentials can only be seen by Ananth (account owner)

---

**Ready to deploy. Waiting for Zoe's message.**

Created by: Max (AI Assistant)  
Session: Weekend Heartbeat (MAX mode)
