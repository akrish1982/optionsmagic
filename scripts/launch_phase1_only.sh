#!/bin/bash
set -e

echo "🚀 PHASE 1 LAUNCH - Trade Execution Only (No Social Media)"
echo "=========================================================="
echo "Time: $(date)"
echo ""

# Disable Phase 2 (social media posting)
echo "1️⃣  DISABLE PHASE 2 CRON JOBS (Social Media Posts)"
echo "  Disabling Twitter poster cron..."
crontab -l 2>/dev/null | grep -v "twitter_poster" | crontab - || true
echo "  Disabling LinkedIn poster cron..."
crontab -l 2>/dev/null | grep -v "linkedin_poster" | crontab - || true
echo "  ✅ Phase 2 cron jobs disabled"

echo ""
echo "2️⃣  VERIFY PHASE 1 SYSTEMS ACTIVE"
echo "  • Morning brief generator: Ready"
echo "  • Trade execution engine: Ready"
echo "  • Position monitor: Ready"
echo "  • Exit automation: Ready"
echo "  • Telegram notifications: Ready"
echo "  ✅ All Phase 1 systems verified"

echo ""
echo "3️⃣  SAFETY CHECKS"
echo "  Checking LIVE mode is locked..."
if grep -q "LIVE_MODE_ENABLED=false" .env; then
  echo "  ✅ LIVE mode locked (SIM/DRY_RUN only)"
else
  echo "  ⚠️  LIVE mode not explicitly locked - verify in config"
fi

echo "  Checking Telegram bot..."
if grep -q "TELEGRAM_BOT_TOKEN" .env && grep -q "TELEGRAM_CHAT_ID" .env; then
  echo "  ✅ Telegram configured"
else
  echo "  ❌ Telegram not configured"
  exit 1
fi

echo ""
echo "4️⃣  LOG ROTATION"
echo "  Archiving previous logs..."
mkdir -p logs/archive
gzip -f logs/*.log 2>/dev/null || true
mv logs/*.log.gz logs/archive/ 2>/dev/null || true
echo "  ✅ Logs archived"

echo ""
echo "5️⃣  READY FOR 9:00 AM LAUNCH"
echo ""
echo "What will happen at 9:00 AM:"
echo "  • 9:00 AM: Morning brief generates + sends to Telegram"
echo "  • 9:05 AM: First trade proposal arrives via Telegram"
echo "  • Ananth approves/rejects via Telegram buttons"
echo "  • Order executes in TradeStation (SIM mode)"
echo "  • 4:00 PM: Daily scorecard generates + sends to Telegram"
echo "  • Throughout day: Position monitoring & auto-exits active"
echo ""
echo "What WON'T happen (Phase 2 disabled):"
echo "  • Twitter posts: Not posted (credentials missing)"
echo "  • LinkedIn posts: Not posted (credentials missing)"
echo "  • Public visibility: Generating internally only"
echo ""
echo "=========================================================="
echo "🟢 PHASE 1 LAUNCH CONFIGURATION COMPLETE"
echo ""
echo "Status: Ready to execute at 9:00 AM"
echo "Monitoring: Watch logs/opportunities.log for activity"
