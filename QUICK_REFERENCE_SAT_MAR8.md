# ⚡ QUICK REFERENCE - SATURDAY MARCH 8

**Print this page. Keep it visible during market hours.**

---

## ⏰ TIMELINE

| Time | What Happens | Check For |
|------|--------------|-----------|
| 6:00 AM | Verify credentials | All credentials in .env |
| 8:30 AM | Go/no-go decision | All systems green? |
| 9:00 AM | Market opens | Morning brief posts |
| 9:15 AM | First proposal | Telegram message |
| 9:20-3:55 | Monitor positions | Every 5 min exit check |
| 4:00 PM | Market closes | Scorecard posts |
| 5:00 PM | Send report | Summary to Ananth |

---

## 🎯 EXPECTED SIGNALS

### 9:00 AM Morning Brief
✅ Appears on Twitter within 1 minute  
✅ Appears on LinkedIn within 1 minute  
✅ Includes market data (SPY, VIX)  
✅ Shows top 3 opportunities  
✅ Image attached to post

### 9:15 AM Trade Proposal
✅ Message arrives via Telegram  
✅ Shows ticker, strategy, risk/return  
✅ Has APPROVE and REJECT buttons  
✅ Times out after 5 minutes

### 4:00 PM Daily Scorecard
✅ Appears on Twitter within 1 minute  
✅ Appears on LinkedIn within 1 minute  
✅ Shows: trades, win rate, P&L  
✅ Image with profit/loss coloring

---

## 🔍 QUICK TROUBLESHOOTING

### "Nothing happened at 9:00 AM"
```bash
# Check immediately
tail -30 logs/morning_brief.log | grep -E "ERROR|Exception"
```

**Fix options:**
- [ ] Twitter credentials missing? Contact Zoe
- [ ] Database offline? Check Supabase status
- [ ] Network issue? Check internet connection
- [ ] Rate limited? Wait 15 min and retry

### "No trade proposal arrived at 9:15 AM"
```bash
tail -30 logs/proposal_worker.log
```

**Check:**
- [ ] Telegram token valid?
- [ ] Opportunities in database?
- [ ] Cron job running? `crontab -l`

### "Posts appear but look wrong"
- [ ] Image broken? Check image file exists
- [ ] Content incorrect? Check database data quality
- [ ] Formatting off? Check templates and CSS

---

## 📋 CRITICAL FILES

| File | Purpose | Location |
|------|---------|----------|
| .env | Credentials | Root directory |
| Logs | Real-time errors | logs/ directory |
| Config | Settings | trade_automation/config.py |
| Cron jobs | Schedule | crontab -l |

---

## 🚨 NUCLEAR OPTIONS (If Things Break)

### Option 1: Skip Social Media, Keep Trading
```bash
# Disable posting, keep trading
export SOCIAL_DRY_RUN=true
# Phase 1 (trading) continues
# Phase 2 (posting) paused
```

### Option 2: Restart Everything
```bash
# Stop all processes
pkill -f python
# Disable cron temporarily
crontab -r
# Then re-enable: bash scripts/setup_cron_jobs.sh
```

### Option 3: Manual Post
- If automation fails, copy content and post manually
- Twitter: @OptionsMagic account
- LinkedIn: OptionsMagic company page

---

## ✅ PRE-9:00 AM CHECKLIST (8:30 AM)

```
☐ Credentials loaded in .env?
☐ Can connect to Twitter API?
☐ Can connect to LinkedIn API?
☐ Cron jobs enabled?
☐ Logs directory writable?
☐ No critical errors in logs?
☐ Database has opportunities?
☐ Telegram bot responds?

ALL CHECKED? → 🟢 GO FOR LAUNCH
ANY UNCHECKED? → 🔴 ABORT AND FIX
```

---

## 📊 METRICS AT A GLANCE

**Track these numbers during the day:**

```
9:00 AM:  Morning brief posts: ___/2 (Twitter, LinkedIn)
9:15 AM:  Trade proposals received: ___
10:00 AM: Position monitoring runs: ___/12 (every 5 min)
4:00 PM:  Daily scorecard posts: ___/2 (Twitter, LinkedIn)
4:00 PM:  Trades executed today: ___
5:00 PM:  Win rate: ___%
5:00 PM:  Total P&L: $______
```

---

## 💬 WHAT TO SAY IF SOMETHING BREAKS

**To Ananth:**
> "Phase 1 trading is running fine, Phase 2 social posts had [ISSUE]. Working on fix. ETA [TIME]. Will keep you posted."

**To Zoe (if credentials problem):**
> "Getting [ERROR] with credentials. Can you double-check they're correct? Do I need to regenerate?"

**To self (if panicking):**
> "Everything is tested. Calmly review logs, follow troubleshooting guide, escalate if stuck."

---

## 🟢 REMEMBER

- **Testing is DONE** - 6/6 tests passing
- **Code is SOLID** - All unit tests passing  
- **Safety LOCKED** - LIVE mode requires manual override
- **You got THIS** - You've prepared for every scenario

**If anything breaks, you have:**
- ✅ Logs to diagnose
- ✅ Rollback procedures
- ✅ Escalation contacts
- ✅ Emergency procedures

**Confidence level: 🟢 MAXIMUM**

You're ready. Let's launch. 🚀

---

**Print date:** Friday, March 6, 2026 — 10:15 PM ET  
**For use:** Saturday, March 8, 2026 — 6:00 AM onwards  
**Created by:** Max (arya)
