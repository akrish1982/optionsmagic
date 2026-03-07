#!/bin/bash
# Setup Cron Jobs for Trade Execution (Phase 1) and Social Media (Phase 2)
# Run once to install. Safe to re-run (skips existing jobs).
#
# All times are ET (server timezone is America/New_York).
# All jobs run Mon-Fri only (market days).
# TODO: Does not account for market holidays - add a holiday check wrapper if needed.

set -euo pipefail

echo "OptionsMagic Trade Automation Cron Setup"
echo "========================================="
echo

WORKSPACE="/home/openclaw/.openclaw/workspace/optionsmagic"
POETRY="$HOME/.local/bin/poetry"
LOGDIR="$WORKSPACE/logs"

mkdir -p "$LOGDIR"

add_cron() {
    local cron_line="$1"
    local description="$2"

    if crontab -l 2>/dev/null | grep -F "$description" > /dev/null; then
        echo "SKIP  $description - Already exists"
    else
        echo "ADD   $description"
        (crontab -l 2>/dev/null; echo ""; echo "# $description"; echo "$cron_line") | crontab -
    fi
}

echo "Phase 1: Trade Execution (SIM)"
echo "-------------------------------"

# 1a. Propose trades at 9:15 AM ET (after 9 AM data collection finishes)
add_cron \
    "15 9 * * 1-5 cd $WORKSPACE && $POETRY run python -m trade_automation.propose_trades >> $LOGDIR/propose_trades.log 2>&1" \
    "OptionsMagic - Propose trades (9:15 AM ET)"

# 1b. Approval worker: runs 9:16 AM - 3:55 PM ET
#     Uses flock to ensure only one instance runs at a time.
#     The worker loops internally (polls every 10s), so we start it once
#     and let it run. We re-launch every hour as a safety net in case it crashes.
add_cron \
    "16 9 * * 1-5 cd $WORKSPACE && flock -n /tmp/optionsmagic_approval.lock $POETRY run python -m trade_automation.approval_worker >> $LOGDIR/approval_worker.log 2>&1 &" \
    "OptionsMagic - Approval worker start (9:16 AM ET)"

add_cron \
    "0 10-15 * * 1-5 cd $WORKSPACE && flock -n /tmp/optionsmagic_approval.lock $POETRY run python -m trade_automation.approval_worker >> $LOGDIR/approval_worker.log 2>&1 &" \
    "OptionsMagic - Approval worker keepalive (hourly 10-3 PM ET)"

# Kill approval worker at 4:00 PM ET (market close)
add_cron \
    "0 16 * * 1-5 pkill -f 'trade_automation.approval_worker' >> $LOGDIR/approval_worker.log 2>&1 || true" \
    "OptionsMagic - Approval worker stop (4:00 PM ET)"

# 1c. Exit automation: every 5 min, 9:35 AM - 3:55 PM ET
#     Uses flock so overlapping runs are skipped.
add_cron \
    "35-59/5 9 * * 1-5 cd $WORKSPACE && flock -n /tmp/optionsmagic_exit.lock $POETRY run python -c 'import asyncio; from trade_automation.exit_automation import run_exit_check; asyncio.run(run_exit_check())' >> $LOGDIR/exit_automation.log 2>&1" \
    "OptionsMagic - Exit automation (9:35-9:55 AM ET every 5 min)"

add_cron \
    "*/5 10-15 * * 1-5 cd $WORKSPACE && flock -n /tmp/optionsmagic_exit.lock $POETRY run python -c 'import asyncio; from trade_automation.exit_automation import run_exit_check; asyncio.run(run_exit_check())' >> $LOGDIR/exit_automation.log 2>&1" \
    "OptionsMagic - Exit automation (10 AM-3:55 PM ET every 5 min)"

echo
echo "Phase 2: Social Media Publishing"
echo "---------------------------------"

# 2a. Morning Brief at 9:00 AM ET
add_cron \
    "0 9 * * 1-5 cd $WORKSPACE && $POETRY run python -m trade_automation.cron_tasks brief >> $LOGDIR/morning_brief.log 2>&1" \
    "OptionsMagic - Morning brief (9:00 AM ET)"

# 2b. Daily Scorecard at 4:15 PM ET
add_cron \
    "15 16 * * 1-5 cd $WORKSPACE && $POETRY run python -m trade_automation.cron_tasks scorecard >> $LOGDIR/daily_scorecard.log 2>&1" \
    "OptionsMagic - Daily scorecard (4:15 PM ET)"

echo
echo "Done! Current cron schedule:"
echo
crontab -l | grep -B1 "OptionsMagic" | grep -v "^--$"
echo
echo "Log files:"
echo "  tail -f $LOGDIR/propose_trades.log"
echo "  tail -f $LOGDIR/approval_worker.log"
echo "  tail -f $LOGDIR/exit_automation.log"
echo "  tail -f $LOGDIR/morning_brief.log"
echo "  tail -f $LOGDIR/daily_scorecard.log"
echo
echo "Daily schedule (Mon-Fri ET):"
echo "  9:00 AM  - Morning Brief post (Twitter + LinkedIn)"
echo "  9:00 AM  - Data collection pipeline"
echo "  9:15 AM  - Propose top trades -> Telegram"
echo "  9:16 AM  - Approval worker starts (polls for button clicks)"
echo "  9:35 AM  - Exit automation starts (every 5 min)"
echo "  10-3 PM  - Hourly data collection + approval keepalive"
echo "  4:00 PM  - Approval worker stops"
echo "  4:15 PM  - Daily Scorecard post (Twitter + LinkedIn)"
echo
echo "To remove all trade automation cron jobs:"
echo "  crontab -l | grep -v 'OptionsMagic - ' | crontab -"
