# 🚨 LAUNCH DAY EMERGENCY PROCEDURES
**OptionsMagic Trading Bot - Phase 1 Launch (Monday, March 10, 2026)**  
**Document:** Critical failure response guide  
**Scope:** 9:00 AM - 5:00 PM ET (market hours)  
**Prepared:** Sunday, March 1, 2026

---

## 🎯 OVERVIEW

This document outlines emergency procedures for critical failures during Phase 1 launch day. Use only during actual emergencies.

**Normal Contact:** Reach out to Ananth via Telegram  
**Emergency Contact:** Reach out to Ananth + Sky via Telegram (group)  
**Escalation:** If no response within 5 minutes, execute fallback procedure

---

## ⚠️ CRITICAL FAILURE SCENARIOS

### SCENARIO 1: Database Unreachable

**Detection:**
- Multiple query failures in rapid succession
- Telegram notifications fail (database used for state)
- All position queries returning errors

**Immediate Actions (First 2 minutes):**
1. ✅ Check Supabase status page (https://status.supabase.io)
2. ✅ Verify network connectivity (ping google.com)
3. ✅ Check .env file (SUPABASE_URL, SUPABASE_KEY valid?)
4. ✅ Log entry: "Database failure detected - [timestamp]"

**If Database is Down (Supabase issue):**
- Contact Supabase support immediately
- ETA: Wait up to 15 minutes for service recovery
- Action: Pause new trade proposals (use manual approval)
- Position tracking: Use last known data from logs

**If Database is Up (Connection issue):**
- Restart application: `poetry run python trade_automation/proposal_worker.py`
- Check logs: `tail -100 logs/trade_automation.log`
- Attempt reconnect: System auto-retries (30 sec intervals)

**Escalation (After 5 min of failure):**
1. Notify Ananth: "Database unreachable - system in fallback mode"
2. Action: No new trades until resolved
3. Option: Manually close critical positions if needed

**Recovery:**
- Once database restored: Verify all data consistency
- Sync check: Positions match TradeStation reality
- Resume: System automatically resumes normal operation

---

### SCENARIO 2: Telegram Not Responding (Approval Cannot Be Sent)

**Detection:**
- 9:15 AM proposal would fail to send
- Multiple Telegram API errors
- Message queue backing up

**Immediate Actions (First 2 minutes):**
1. ✅ Test Telegram: Send manual message to yourself
2. ✅ Check token: `echo $TELEGRAM_BOT_TOKEN | head -c 20`
3. ✅ Verify chat ID: Correct in .env?
4. ✅ Check internet: Telegram API reachable?

**If Telegram is Down:**
- Contact Telegram support (minimal chance)
- Use fallback: Manual Slack/email approval workflow
- Action: Skip Telegram, wait for manual approval

**If Token Expired:**
- Need new token from Ananth
- Ananth must generate in @BotFather
- Deploy new token to .env
- Restart application

**Escalation (After 5 min of failure):**
1. Skip this proposal
2. Notify Ananth: "Telegram down - manual approval needed for next proposal"
3. Wait for response (max 5 min)
4. If no response: Auto-reject this proposal, continue to next

**Recovery:**
- Replace token (if needed)
- Verify test message sends successfully
- Resume normal operation

---

### SCENARIO 3: TradeStation API Unavailable

**Detection:**
- Order submission fails with "Connection refused"
- Cannot fetch position data
- API latency > 10 seconds (unusually high)

**Immediate Actions (First 2 minutes):**
1. ✅ Check TradeStation status page
2. ✅ Test connection: `curl https://api.tradestation.com/v3/accounts`
3. ✅ Verify credentials in .env (still valid?)
4. ✅ Check logs: `grep ERROR logs/trade_automation.log`

**If TradeStation is Down:**
- Check their status page: https://status.tradestation.com
- ETA: Usually brief (5-30 minutes)
- Action: Pause order submission, wait for recovery
- Position monitoring: Fallback to last known data

**If Credentials Expired:**
- Need refresh token from Ananth
- Deploy to .env
- System auto-refreshes token

**If Network Issue:**
- Check VPN/firewall
- Restart network connection
- Retry after 30 seconds

**Escalation (After 5 min of failure):**
1. Notify Ananth: "TradeStation unreachable"
2. Hold trade proposals (don't send)
3. Monitor positions manually
4. Wait for TradeStation to recover

**Recovery:**
- Once TradeStation is back:
  1. Verify token is valid
  2. Test order submission with small test order
  3. Check position sync with reality
  4. Resume normal operation

---

### SCENARIO 4: Position Exit Fails (Stop Loss Should Have Triggered)

**Detection:**
- 50% profit reached but exit failed
- Position should be closed but isn't
- Alert: "Exit order submission failed"

**Immediate Actions (First 2 minutes):**
1. ✅ Check position current value
2. ✅ Calculate P&L manually
3. ✅ Log entry: "Exit failure - position [XXX] still open"
4. ✅ Check why: API error? Order rejected? Network timeout?

**If Order Was Rejected:**
- Note rejection reason (e.g., "after hours")
- System retries automatically (every 5 min)
- Action: Wait for retry, OR manually exit if urgent

**If Order Timed Out:**
- System automatically retries after 5 min
- Monitor: Position still profitable?
- Action: Wait for retry

**If Multiple Failures (3+):**
1. Escalate to Ananth immediately
2. Current position: [details]
3. Attempted exits: [count]
4. Suggested action: Manual intervention needed

**Manual Exit Procedure:**
1. Log into TradeStation
2. Find position [details]
3. Create exit order (opposite direction)
4. Submit order
5. Confirm fill
6. Log action: "Manual exit - [reason]"

**Recovery:**
- Once position is closed: Update database
- Update trade history with actual exit price
- Resume normal operation

---

### SCENARIO 5: Duplicate Order Submitted (Same Proposal Sent Twice)

**Detection:**
- Alert: "Duplicate order detected"
- Two orders exist for same proposal
- Both have same request ID

**Immediate Actions (First 2 minutes):**
1. ✅ Verify both orders exist in TradeStation
2. ✅ Check: Do they have same quantity/strike?
3. ✅ Decision: Both needed or duplicate?

**If Confirmed Duplicate:**
1. Close second order immediately
2. Go to TradeStation
3. Find order (newer one)
4. Cancel it
5. Log: "Duplicate order cancelled - [ID]"

**If Both Orders Needed (edge case):**
- Keep both
- Adjust position size assumptions
- Update database to reflect 2x position

**Recovery:**
- Verify only one order remains
- Update P&L calculations
- Resume normal operation

---

### SCENARIO 6: Twitter/LinkedIn Posting Fails

**Detection:**
- Morning brief due at 9:30 AM, doesn't post
- Alert: "Twitter posting failed"
- Content stuck in queue

**Immediate Actions (First 2 minutes):**
1. ✅ Check Twitter API status
2. ✅ Verify credentials (not expired?)
3. ✅ Check logs: "Twitter API error - [reason]"

**If Rate Limited:**
- Wait 15 minutes, system retries
- Action: None needed, retry automatic

**If Credentials Expired:**
- Need new credentials from Zoe
- Deploy to .env
- Restart posting system
- Retry failed post

**If Permanent Failure:**
1. Manual fallback: Zoe posts manually (if available)
2. Content saved: Not deleted, retry in 30 min
3. Trading continues: Social posting independent

**Recovery:**
- Post gets sent on next retry
- Engagement metrics tracked
- Resume normal operation

---

### SCENARIO 7: System Crashes (Application Dies)

**Detection:**
- No proposals generated at 9:15 AM
- Cron logs show: "Failed to execute"
- System not responding

**Immediate Actions (First 2 minutes):**
1. ✅ Check process: `ps aux | grep python`
2. ✅ Check logs: `tail -50 logs/trade_automation.log`
3. ✅ Look for error traceback

**Recovery Steps (In Order):**
1. Kill process: `pkill -f proposal_worker.py`
2. Restart: `poetry run python trade_automation/proposal_worker.py`
3. Verify: Check logs for "Successfully started"
4. Test: Send test proposal via Telegram

**If Restart Fails:**
1. Check .env (credentials valid?)
2. Check database (reachable?)
3. Check dependencies (poetry install)
4. If still failing: Check error logs for specific issue

**Data Integrity Check (After Restart):**
1. Fetch last order from database
2. Verify in TradeStation
3. Check positions match
4. If mismatch: Investigate and reconcile

**Recovery:**
- Once running again: System resumes normal schedule
- Next proposal: Will be sent on next cycle

---

### SCENARIO 8: Market Halts/Circuit Breaker

**Detection:**
- Market halted (exchange stops trading)
- Cron still runs but orders rejected
- Alert: "Market halted - orders rejected"

**Immediate Actions:**
1. ✅ Check market status (is trading halted?)
2. ✅ Monitor: When will it resume?
3. ✅ Log entry: "Market halt detected - [time]"

**During Halt:**
- New trade proposals: Rejected (safety)
- Existing positions: Monitored but no exits
- Resume: When market reopens, resume normal

**Action:**
- Wait for market to reopen
- System automatically resumes (no manual action needed)
- Check positions after restart

**Recovery:**
- Market reopens
- System resumes normal operation
- Process any pending proposals

---

## 🚨 CRITICAL DECISION POINTS

### Decision Tree: When to Manually Intervene

```
Is the system still trading?
  ├─ YES: Can positions be exited automatically?
  │   ├─ YES: Monitor, let system handle
  │   └─ NO: Escalate to Ananth
  └─ NO: System paused
      └─ How long? <5 min? Let it recover
         >5 min? Manual intervention needed
```

### When to Stop Everything (KILL SWITCH)

**Execute KILL SWITCH if ANY of:**
1. ❌ Unlimited position size (risk controls failed)
2. ❌ Loss exceeds -$10,000 (drawdown limit broken)
3. ❌ Database & TradeStation both inaccessible
4. ❌ Multiple orders failed to cancel (duplicate exposure)
5. ❌ System behavior is clearly incorrect (serious bug)

**How to Execute KILL SWITCH:**
1. Stop proposal generator: `pkill -f proposal_worker.py`
2. Stop position monitor: `pkill -f position_manager.py`
3. Manually close all positions in TradeStation
4. Notify Ananth immediately: "KILL SWITCH executed - reason: [details]"

---

## 📞 COMMUNICATION PROTOCOL

### Level 1: Monitoring (Auto-handled)
- System detects issue
- Logs it with timestamp
- Retries automatically (max 3x)
- If resolved: Log "Recovered"

### Level 2: Alert (Send Notification)
- Issue persists after 3 retries (5+ minutes)
- Send Telegram: "@Ananth Issue detected: [details]"
- Wait for response: 5 minutes
- If no response: Execute fallback

### Level 3: Escalation (Emergency)
- Critical failure identified
- Multiple systems down
- Loss exceeding limits
- Action: Send to group: "@Ananth @Sky EMERGENCY: [details]"

### Communication Template:
```
🚨 [LEVEL]: [SYSTEM]
Issue: [What failed]
Time: [When it started]
Impact: [What's affected]
Action: [What we're doing]
ETA: [When it should be fixed]
```

---

## 🔄 RECOVERY CHECKLIST (After Any Failure)

After any critical failure is resolved, verify:

- [ ] System is running: Check `ps aux | grep python`
- [ ] Database connected: Query returns data
- [ ] Telegram working: Test message sends
- [ ] TradeStation accessible: API responding
- [ ] Positions match: Database = TradeStation reality
- [ ] P&L correct: Manual calc vs system calc
- [ ] No orphaned orders: All orders accounted for
- [ ] Logging working: New entries in log files
- [ ] Cron ready: Next scheduled job ready to run

Once all checked: Resume normal operation

---

## 📊 POST-INCIDENT REVIEW

After any incident:

1. **Document:** What happened? When? Why?
2. **Root cause:** Was it preventable?
3. **Detection:** How quickly was it caught?
4. **Response:** Was response procedure effective?
5. **Resolution:** What fixed it?
6. **Prevention:** Can we prevent this again?

Store incident report in: `logs/incidents/YYYY-MM-DD-[issue].log`

---

## ✅ PRE-LAUNCH VALIDATION

Before 9:00 AM launch:

- [ ] All services running (proposal, position, exit)
- [ ] Telegram bot responsive (send test message)
- [ ] TradeStation authenticated (fetch account balance)
- [ ] Database accessible (query executes)
- [ ] Logs initialized (today's log file created)
- [ ] Twitter/LinkedIn credentials in .env (or will deploy after 7 AM)
- [ ] No orphaned processes (clean startup)

---

## 📋 QUICK REFERENCE

| Failure | Detection | Immediate Action | Escalation |
|---------|-----------|------------------|------------|
| **DB Down** | Queries fail | Wait 5 min / Check status page | Notify Ananth |
| **Telegram** | Can't send message | Verify token / Restart | Manual approval |
| **TradeStation** | Order rejected | Check status / Verify token | Hold proposals |
| **Exit fails** | Position still open | Retry automatically | Manual exit |
| **Duplicate order** | Two orders found | Cancel duplicate | Close order |
| **Twitter down** | Post fails | System retries (30 min) | Manual post |
| **Crash** | No activity | Restart app / Check logs | Full restart |
| **Market halt** | Orders rejected | Wait for reopen | Monitor & resume |

---

## 🎯 FINAL NOTES

- **Stay calm:** Most failures auto-recover
- **Log everything:** Timestamps matter
- **Communicate:** Let Ananth know immediately
- **Verify:** Double-check after recovery
- **Document:** For post-mortem analysis

**Most importantly:** The system is designed to be resilient. Trust the safety mechanisms.

---

**Document Version:** 1.0  
**Created:** Sunday, March 1, 2026  
**Approved for:** Monday, March 10, 2026 Launch  
**Author:** Max (Trading Bot Agent)  

**EMERGENCY PROCEDURES READY FOR DEPLOYMENT**
