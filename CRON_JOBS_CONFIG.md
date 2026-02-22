# Cron Jobs Configuration - OptionsMagic Automated Tasks

**Status:** Ready to deploy  
**Location:** `/home/openclaw/.openclaw/workspace/optionsmagic`

---

## 📋 All Scheduled Tasks

### Phase 1: Trade Execution (Running Now)

#### 1. Proposal Generation - 9:15 AM ET (Weekdays)
```bash
15 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python -m trade_automation.proposal_worker
```

**What:** Generates top 2-3 trading opportunities  
**Input:** Options database  
**Output:** Telegram proposal to Ananth (approve/reject)  
**Logging:** `logs/proposal_worker.log`

---

#### 2. Exit Automation - Every 5 min (Market Hours)
```bash
*/5 9-16 * * 1-5 cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python -m trade_automation.exit_automation
```

**What:** Monitors open positions, executes exits  
**Rules:** Profit target (50%), Stop loss (200%), 21 DTE  
**Output:** Position closes, trade history logs  
**Logging:** `logs/exit_automation.log`

---

### Phase 2: Social Media Publishing (Coming Mar 8)

#### 3. Morning Brief Generator - 9:00 AM ET (Weekdays)
```bash
0 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python -m trade_automation.cron_tasks brief
```

**What:** Generates morning market brief + image  
**Input:** Market data (SPY, VIX, ES, NQ), top 3 opportunities  
**Output:** Posted to Twitter/X, LinkedIn, Instagram @ 9:30 AM  
**Logging:** `logs/cron_tasks.log`, `logs/morning_brief_generator.log`

---

#### 4. Daily Scorecard Generator - 4:00 PM ET (Weekdays)
```bash
0 16 * * 1-5 cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python -m trade_automation.cron_tasks scorecard
```

**What:** Generates daily P&L + performance scorecard  
**Input:** Closed trades from today, metrics  
**Output:** Posted to Twitter, LinkedIn, Instagram, TikTok @ 4:30 PM  
**Logging:** `logs/cron_tasks.log`, `logs/daily_scorecard_generator.log`

---

## 🔧 Installation Instructions

### Prerequisites
```bash
# Install poetry dependencies (already done)
cd /home/openclaw/.openclaw/workspace/optionsmagic
poetry install

# Verify environment variables are set
cat .env | grep -E "SUPABASE|TELEGRAM|TRADESTATION|TWITTER|LINKEDIN"
```

### Install Cron Jobs

**Option 1: Install All at Once**
```bash
# Navigate to project
cd /home/openclaw/.openclaw/workspace/optionsmagic

# Install setup script (if exists)
poetry run python scripts/setup_cron_jobs.sh
```

**Option 2: Manual Installation**
```bash
# Open crontab editor
crontab -e

# Paste all jobs below
```

### Complete Crontab Entries

```cron
# OptionsMagic - Phase 1: Trade Execution
# Proposal generation at 9:15 AM ET (weekdays only)
15 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python -m trade_automation.proposal_worker >> logs/cron.log 2>&1

# Exit automation every 5 minutes during market hours (9:30 AM - 4:00 PM ET)
*/5 9-16 * * 1-5 cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python -m trade_automation.exit_automation >> logs/cron.log 2>&1

# OptionsMagic - Phase 2: Social Media (enable after Mar 8)
# Morning brief at 9:00 AM ET (before market open)
# 0 9 * * 1-5 cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python -m trade_automation.cron_tasks brief >> logs/cron.log 2>&1

# Daily scorecard at 4:00 PM ET (after market close)
# 0 16 * * 1-5 cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python -m trade_automation.cron_tasks scorecard >> logs/cron.log 2>&1

# Weekly cleanup (Sundays 2 AM ET)
# 0 2 * * 0 cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python scripts/cleanup.py >> logs/cron.log 2>&1
```

**Note:** Phase 2 cron jobs are commented out. Uncomment them on Mar 8 when Phase 2 launches.

### Verify Installation

```bash
# List installed cron jobs
crontab -l

# Should show all entries

# Check logs
tail -f logs/cron.log

# Monitor specific task
tail -f logs/proposal_worker.log
tail -f logs/exit_automation.log
tail -f logs/morning_brief_generator.log
tail -f logs/daily_scorecard_generator.log
```

---

## 📊 Task Timeline (Eastern Time)

```
5:00 AM ET  <- Before market open
  ↓
9:00 AM ET  [PHASE 2] Morning Brief Generator
  ↓
9:15 AM ET  [PHASE 1] Proposal Worker (propose trades)
  ↓
9:30 AM ET  <- MARKET OPEN
  ↓
Every 5 min [PHASE 1] Exit Automation (monitor positions)
  ↓
4:00 PM ET  <- MARKET CLOSE
  ↓
4:00 PM ET  [PHASE 2] Daily Scorecard Generator
  ↓
5:00 PM ET  <- After market close
  ↓
11:59 PM ET <- End of day
```

---

## 🔄 Running Tasks Manually (For Testing)

### Phase 1 Tasks

#### Test Proposal Generation
```bash
cd optionsmagic
poetry run python -m trade_automation.proposal_worker
```

#### Test Exit Automation
```bash
cd optionsmagic
poetry run python -m trade_automation.exit_automation
```

### Phase 2 Tasks

#### Test Morning Brief
```bash
cd optionsmagic
poetry run python -m trade_automation.cron_tasks brief
```

#### Test Daily Scorecard
```bash
cd optionsmagic
poetry run python -m trade_automation.cron_tasks scorecard
```

---

## ⚙️ Configuration

### Environment Variables Required

#### Phase 1 (Trade Execution)
```bash
SUPABASE_URL=https://...
SUPABASE_KEY=...
TRADESTATION_ENV=SIM          # or LIVE
TRADESTATION_DRY_RUN=true     # false for SIM/LIVE
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

#### Phase 2 (Social Media)
```bash
# Twitter/X
TWITTER_BEARER_TOKEN=...
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...

# LinkedIn (browser automation)
# Uses system Chrome/Chromium browser
# No additional config needed (uses logged-in session)

# Instagram (manual posting via Zoe)
# No API credentials needed (alerts sent to Zoe)

# TikTok (manual posting via Zoe)
# No API credentials needed (alerts sent to Zoe)
```

### Override Configuration

```bash
# Force DRY_RUN mode (no real posts)
export TWITTER_API_KEY=
export TWITTER_API_SECRET=

# All posts will log instead of posting
```

---

## 📈 Monitoring & Logs

### Log Files
```
logs/
  ├── cron.log                        # All cron output
  ├── proposal_worker.log             # Proposals
  ├── exit_automation.log             # Exit automation
  ├── approval_worker.log             # Trade approvals
  ├── tradestation.log                # TradeStation orders
  ├── morning_brief_generator.log     # Morning brief
  ├── daily_scorecard_generator.log   # Daily scorecard
  ├── twitter_poster.log              # Twitter posts
  ├── linkedin_poster.log             # LinkedIn posts
  └── social_media_orchestrator.log   # Orchestration
```

### Monitor in Real-Time
```bash
# All cron logs
tail -f logs/cron.log

# Specific service
tail -f logs/morning_brief_generator.log
```

### Check Success Rate
```bash
# Count successful posts this week
grep "✅" logs/twitter_poster.log | wc -l

# Count failures
grep "❌\|Failed" logs/social_media_orchestrator.log | wc -l
```

---

## 🚨 Troubleshooting

### Cron Job Not Running

**Check 1: Is cron running?**
```bash
sudo systemctl status cron  # or crond
```

**Check 2: Is cron job installed?**
```bash
crontab -l | grep optionsmagic
```

**Check 3: Are environment variables loaded?**
```bash
# Add to crontab to load .env
0 9 * * 1-5 source /home/openclaw/.openclaw/workspace/optionsmagic/.env && cd /home/openclaw/.openclaw/workspace/optionsmagic && poetry run python -m trade_automation.cron_tasks brief
```

### Task Fails Silently

**Check logs:**
```bash
tail -100 logs/cron.log
tail -100 logs/morning_brief_generator.log
```

**Run manually to see errors:**
```bash
cd optionsmagic
poetry run python -m trade_automation.cron_tasks brief
# Will show error messages
```

### Too Many Cron Processes

**Check running processes:**
```bash
ps aux | grep poetry
```

**Kill stuck process:**
```bash
pkill -f "trade_automation"
```

---

## 📅 Deployment Timeline

### Feb 24 - SIM Testing
- Phase 1 cron jobs already running
- Monitor logs for errors
- Test proposal generation manually

### Mar 1-7 - Phase 2 Prep
- Finalize Twitter API credentials
- Test morning_brief_generator manually
- Test daily_scorecard_generator manually

### Mar 8 - Phase 2 Launch
- Uncomment Phase 2 cron jobs
- Enable morning brief @ 9:00 AM
- Enable daily scorecard @ 4:00 PM
- Monitor logs for success

---

## 🎯 Success Criteria

### Phase 1 (Running Now)
- [x] Proposals generated daily @ 9:15 AM
- [x] Exit automation runs every 5 min
- [x] All logs recorded
- [x] Notifications sent

### Phase 2 (Mar 8+)
- [ ] Morning brief posted @ 9:30 AM
- [ ] Daily scorecard posted @ 4:30 PM
- [ ] Posts appear on all platforms
- [ ] 0 failed posts (100% success rate)
- [ ] Logs show all steps completed

---

## 📞 Support

If a cron job fails:
1. Check logs: `logs/cron.log`
2. Run manually to see full error
3. Check environment variables
4. Verify database connection
5. Contact team for API issues

---

**Last Updated:** February 22, 2026  
**Status:** Ready to deploy  
**Next Action:** Uncomment Phase 2 jobs on Mar 8

