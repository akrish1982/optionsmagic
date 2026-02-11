#!/bin/bash
# OptionsMagic Production Pipeline (Latest Code)
# Adapted for latest codebase by Max 👨‍💻 - 2026-02-09
# 
# Runs hourly during market hours (9 AM - 4 PM ET, Mon-Fri)
# Features: locking, timeouts, heartbeats, comprehensive logging

set -euo pipefail

# ===== Configuration =====
BASE_DIR="/home/openclaw/.openclaw/workspace/optionsmagic"
POETRY="$HOME/.local/bin/poetry"
LOG_DIR="$BASE_DIR/logs"
HB_DIR="$BASE_DIR/heartbeat"
LOCK_DIR="$BASE_DIR/locks"
LOCK_PATH="$LOCK_DIR/optionsmagic_pipeline.lock"
STALE_HOURS=4

# ---- Timeouts (seconds) ----
T_FINVIZ=$((6 * 60))           # 6 minutes for stock scraping
T_TRADESTATION=$((30 * 60))    # 30 minutes for options data (70 tickers)
T_OPPORTUNITIES=$((6 * 60))    # 6 minutes for opportunity generation
T_PIPELINE=$((46 * 60))        # 46 minutes total pipeline timeout

# ===== Setup =====
mkdir -p "$LOG_DIR" "$HB_DIR" "$LOCK_DIR"
cd "$BASE_DIR"

log() { 
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Linux has native timeout command - use it!
run_with_timeout() {
  local timeout_secs="$1"; shift
  timeout "$timeout_secs" "$@"
}

# ===== Lock Management =====
# Stale lock protection (remove if older than STALE_HOURS)
if [ -d "$LOCK_PATH" ]; then
  if find "$LOCK_PATH" -maxdepth 0 -mmin "+$((STALE_HOURS * 60))" 2>/dev/null | grep -q .; then
    log "Stale lock detected (>$STALE_HOURS hours old). Removing."
    rm -rf "$LOCK_PATH" || true
  fi
fi

# Acquire lock (prevents concurrent runs)
if ! mkdir "$LOCK_PATH" 2>/dev/null; then
  log "Lock exists at $LOCK_PATH. Another pipeline is running. Exiting."
  exit 0
fi

# Always clean up lock on exit
cleanup() { 
  rm -rf "$LOCK_PATH" || true
}
trap cleanup EXIT INT TERM

# ===== Pipeline Step Runner =====
step() {
  local name="$1"
  local timeout_secs="$2"
  local script_path="$3"
  local logfile="$4"
  local heartbeat="$5"
  
  log "Starting ${name} (timeout ${timeout_secs}s)"
  
  set +e
  run_with_timeout "$timeout_secs" "$POETRY" run python "$script_path" >> "$logfile" 2>&1
  rc=$?
  set -e
  
  if [ "$rc" -eq 124 ]; then
    log "❌ ${name} TIMED OUT after ${timeout_secs}s"
    return 124
  elif [ "$rc" -ne 0 ]; then
    log "❌ ${name} FAILED (exit $rc)"
    return "$rc"
  fi
  
  # Success - update heartbeat
  touch "$heartbeat"
  log "✅ ${name} completed successfully"
  return 0
}

# ===== Main Pipeline =====
pipeline_main() {
  # Step 1: Scrape stock data from Finviz
  step "finviz.py" "$T_FINVIZ" \
    "data_collection/finviz.py" \
    "$LOG_DIR/finviz.log" \
    "$HB_DIR/finviz_heartbeat" || return $?
  
  # Step 2: Fetch options data from TradeStation
  step "tradestation_options.py" "$T_TRADESTATION" \
    "data_collection/tradestation_options.py" \
    "$LOG_DIR/tradestation_options.log" \
    "$HB_DIR/tradestation_heartbeat" || return $?
  
  # Step 3: Generate options opportunities (for trade automation)
  # Using simple script (works for both CSP + VPC)
  step "generate_opportunities_simple.py" "$T_OPPORTUNITIES" \
    "data_collection/generate_opportunities_simple.py" \
    "$LOG_DIR/opportunities.log" \
    "$HB_DIR/opportunities_heartbeat" || return $?
  
  return 0
}

# ===== Execute Pipeline =====
log "🚀 Pipeline start"

set +e
pipeline_main >> "$LOG_DIR/pipeline.log" 2>&1
rc=$?
set -e

if [ "$rc" -eq 0 ]; then
  log "🎉 Pipeline completed successfully"
  exit 0
elif [ "$rc" -eq 124 ]; then
  log "❌ Pipeline TIMED OUT"
  exit 124
else
  log "❌ Pipeline failed with exit $rc"
  exit "$rc"
fi
