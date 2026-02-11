#!/bin/bash
# Setup Cron Jobs for OptionsMagic
# Run once to configure all scheduled tasks

set -euo pipefail

echo "🔧 OptionsMagic Cron Job Setup"
echo "=============================="
echo

# Configuration
WORKSPACE="/home/openclaw/.openclaw/workspace/optionsmagic"
POETRY="$HOME/.local/bin/poetry"
LOGDIR="$WORKSPACE/logs"

# Ensure log directory exists
mkdir -p "$LOGDIR"

# Function to add cron job if not already present
add_cron() {
    local cron_line="$1"
    local description="$2"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -F "$description" > /dev/null; then
        echo "⏭️  $description - Already exists, skipping"
    else
        echo "✅ $description - Adding..."
        (crontab -l 2>/dev/null; echo ""; echo "# $description"; echo "$cron_line") | crontab -
    fi
}

echo "📋 Installing Cron Jobs..."
echo

# Job 1: Hourly data collection (9 AM - 4 PM ET, Mon-Fri)
add_cron \
    "0 9-16 * * 1-5 cd $WORKSPACE && $POETRY run python data_collection/finviz.py >> $LOGDIR/finviz.log 2>&1 && $POETRY run python data_collection/tradestation_options.py >> $LOGDIR/tradestation.log 2>&1 && $POETRY run python data_collection/generate_options_opportunities.py >> $LOGDIR/opportunities.log 2>&1" \
    "OptionsMagic - Hourly data collection (market hours)"

# Job 2: Weekly cleanup (Sunday 2 AM ET)
add_cron \
    "0 2 * * 0 cd $WORKSPACE && $POETRY run python data_collection/cleanup_old_data.py >> $LOGDIR/cleanup.log 2>&1" \
    "OptionsMagic - Weekly data cleanup (30-day retention)"

echo
echo "✅ Cron jobs installed!"
echo
echo "📋 Current cron schedule:"
echo
crontab -l | grep -A 1 "OptionsMagic"
echo
echo "🔍 To verify logs:"
echo "  tail -f $LOGDIR/finviz.log"
echo "  tail -f $LOGDIR/tradestation.log"
echo "  tail -f $LOGDIR/opportunities.log"
echo "  tail -f $LOGDIR/cleanup.log"
echo
echo "✅ Setup complete!"
