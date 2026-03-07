#!/bin/bash
set -e

echo "🔍 SATURDAY MORNING VALIDATION - Trade Automation System"
echo "========================================================="
echo "Time: $(date)"
echo ""

# 1. Check credentials status
echo "1️⃣  CREDENTIAL CHECK"
twitter_ready=$(grep -c "TWITTER_API_KEY" .env 2>/dev/null && echo "✅" || echo "❌")
linkedin_ready=$(grep -c "LINKEDIN_API_KEY" .env 2>/dev/null && echo "✅" || echo "❌")
echo "  Twitter credentials: $twitter_ready"
echo "  LinkedIn credentials: $linkedin_ready"

# 2. Check Python environment
echo ""
echo "2️⃣  PYTHON ENVIRONMENT"
if poetry show >/dev/null 2>&1; then
  echo "  Poetry: ✅"
  echo "  Dependencies:"
  poetry show | wc -l | xargs echo "    Packages installed:"
else
  echo "  Poetry: ❌"
fi

# 3. Check critical files
echo ""
echo "3️⃣  CRITICAL FILES"
files=(
  "trade_automation/config.py"
  "trade_automation/opportunities.py"
  "trade_automation/exit_automation.py"
  "trade_automation/position_manager.py"
  "trade_automation/morning_brief_generator.py"
  "trade_automation/daily_scorecard_generator.py"
  "trade_automation/notifier_telegram.py"
  ".env"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "  $file: ✅"
  else
    echo "  $file: ❌"
  fi
done

# 4. Test Python imports
echo ""
echo "4️⃣  PYTHON IMPORTS TEST"
poetry run python << 'PYEOF'
import sys
errors = []

try:
    from trade_automation.config import Settings
    print("  Config: ✅")
except Exception as e:
    print(f"  Config: ❌ ({str(e)[:40]})")
    errors.append("config")

try:
    from trade_automation.opportunities import fetch_opportunities
    print("  Opportunities: ✅")
except Exception as e:
    print(f"  Opportunities: ❌ ({str(e)[:40]})")
    errors.append("opportunities")

try:
    from trade_automation.position_manager import PositionManager
    print("  Position Manager: ✅")
except Exception as e:
    print(f"  Position Manager: ❌ ({str(e)[:40]})")
    errors.append("position_manager")

try:
    from trade_automation.exit_automation import ExitAutomation
    print("  Exit Automation: ✅")
except Exception as e:
    print(f"  Exit Automation: ❌ ({str(e)[:40]})")
    errors.append("exit_automation")

try:
    from trade_automation.morning_brief_generator import MorningBriefGenerator
    print("  Morning Brief: ✅")
except Exception as e:
    print(f"  Morning Brief: ❌ ({str(e)[:40]})")
    errors.append("morning_brief")

try:
    from trade_automation.daily_scorecard_generator import DailyScorecardGenerator
    print("  Daily Scorecard: ✅")
except Exception as e:
    print(f"  Daily Scorecard: ❌ ({str(e)[:40]})")
    errors.append("daily_scorecard")

try:
    from trade_automation.notifier_telegram import TelegramNotifier
    print("  Telegram Notifier: ✅")
except Exception as e:
    print(f"  Telegram Notifier: ❌ ({str(e)[:40]})")
    errors.append("telegram")

if errors:
  print(f"\n❌ {len(errors)} module(s) failed to load")
  sys.exit(1)
else:
  print("\n✅ All core modules load successfully")
PYEOF

# 5. Check logs directory
echo ""
echo "5️⃣  LOGS DIRECTORY"
if [ -d "logs" ] && [ -w "logs" ]; then
  echo "  logs/: ✅ (writable)"
  ls -lah logs/ | tail -5
else
  echo "  logs/: ❌ (doesn't exist or not writable)"
  mkdir -p logs && echo "  Created logs/ directory"
fi

# 6. Check cron status
echo ""
echo "6️⃣  CRON STATUS"
if crontab -l >/dev/null 2>&1; then
  echo "  Cron available: ✅"
  echo "  Scheduled jobs:"
  crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" | head -5 || echo "    (none scheduled yet)"
else
  echo "  Cron available: ⚠️  (might not be available in this environment)"
fi

# 7. Check Telegram bot
echo ""
echo "7️⃣  TELEGRAM BOT"
if grep -q "TELEGRAM_BOT_TOKEN" .env; then
  echo "  Telegram token: ✅"
  if grep -q "TELEGRAM_CHAT_ID" .env; then
    echo "  Telegram chat ID: ✅"
  else
    echo "  Telegram chat ID: ❌"
  fi
else
  echo "  Telegram token: ❌"
fi

# 8. Summary
echo ""
echo "========================================================="
echo "✅ VALIDATION COMPLETE"
echo ""
echo "LAUNCH READINESS:"
if [ -z "$errors" ]; then
  echo "🟢 Phase 1 (Trade Execution): READY"
else
  echo "🔴 Issues found - review above"
fi

echo ""
echo "Next step: Await decision on credentials"
echo "  • If credentials arrive: Inject + enable Phase 2"
echo "  • If no credentials: Launch Phase 1 only"
