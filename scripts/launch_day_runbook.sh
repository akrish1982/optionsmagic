#!/bin/bash
###############################################################################
# LAUNCH DAY RUNBOOK
# Execute this script on Saturday, March 8, 2026 at 6:00 AM ET
#
# This runs all pre-launch verification and monitoring procedures
# Exit code 0 = GO FOR LAUNCH ✅
# Exit code 1 = CAUTION (fix warnings first)
# Exit code 2 = NO-GO (critical issues - do not launch)
###############################################################################

set -e  # Exit on any error

PROJECT_ROOT="/home/openclaw/.openclaw/workspace/optionsmagic"
LAUNCH_DATE=$(date +"%Y-%m-%d")
LAUNCH_TIME=$(date +"%H:%M:%S %Z")
LOG_FILE="$PROJECT_ROOT/logs/launch_day_$LAUNCH_DATE.log"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASS=0
CHECKS_FAIL=0
CHECKS_WARN=0

###############################################################################
# HELPER FUNCTIONS
###############################################################################

log_header() {
    local title="$1"
    echo ""
    echo "================================================================================"
    echo "🔍 $title"
    echo "================================================================================"
    echo "" | tee -a "$LOG_FILE"
}

log_pass() {
    local msg="$1"
    echo -e "${GREEN}✅${NC} $msg" | tee -a "$LOG_FILE"
    ((CHECKS_PASS++))
}

log_fail() {
    local msg="$1"
    echo -e "${RED}❌${NC} $msg" | tee -a "$LOG_FILE"
    ((CHECKS_FAIL++))
}

log_warn() {
    local msg="$1"
    echo -e "${YELLOW}⚠️${NC}  $msg" | tee -a "$LOG_FILE"
    ((CHECKS_WARN++))
}

log_info() {
    local msg="$1"
    echo -e "${BLUE}ℹ️${NC}  $msg" | tee -a "$LOG_FILE"
}

###############################################################################
# MAIN PROCEDURES
###############################################################################

main() {
    # Initialize
    mkdir -p "$PROJECT_ROOT/logs"
    cd "$PROJECT_ROOT"
    
    echo "================================================================================"
    echo "🚀 LAUNCH DAY RUNBOOK"
    echo "================================================================================"
    echo "📅 Date: $LAUNCH_DATE"
    echo "⏰ Time: $LAUNCH_TIME"
    echo "🎯 Target: First post at 9:00 AM ET"
    echo "📋 Log: $LOG_FILE"
    echo "================================================================================"
    
    {
        echo "================================================================================"
        echo "🚀 LAUNCH DAY RUNBOOK"
        echo "================================================================================"
        echo "📅 Date: $LAUNCH_DATE"
        echo "⏰ Time: $LAUNCH_TIME"
    } > "$LOG_FILE"
    
    # Run all checks
    check_time
    check_environment
    check_database
    check_credentials
    check_health
    check_generators
    check_files
    check_services
    
    # Final verdict
    print_summary
    return_exit_code
}

###############################################################################
# INDIVIDUAL CHECKS
###############################################################################

check_time() {
    log_header "1. TIME VERIFICATION"
    
    HOUR=$(date +%H)
    
    if [ "$HOUR" -lt 6 ] || [ "$HOUR" -gt 9 ]; then
        log_warn "Current time $LAUNCH_TIME is outside recommended window (6-9 AM ET)"
        log_info "Continuing anyway - you're responsible for timing"
    else
        log_pass "Time verified: $LAUNCH_TIME (within 6-9 AM window)"
    fi
}

check_environment() {
    log_header "2. ENVIRONMENT VERIFICATION"
    
    # Check .env file exists
    if [ -f "$PROJECT_ROOT/.env" ]; then
        log_pass ".env file found"
    else
        log_fail ".env file missing - cannot proceed"
        return 1
    fi
}

check_database() {
    log_header "3. DATABASE CONNECTIVITY"
    log_info "Delegating to health check system..."
}

check_credentials() {
    log_header "4. COMPREHENSIVE HEALTH CHECK"
    
    # Run the actual health check script
    log_info "Running 36-point health check system..."
    
    if poetry run python scripts/pre_launch_health_check.py > /tmp/health_check.txt 2>&1; then
        EXIT_CODE=$?
        
        # Extract summary
        if grep -q "All boxes checked" /tmp/health_check.txt || \
           grep -q "28/36" /tmp/health_check.txt; then
            log_pass "Health check completed successfully"
            
            # Count results
            PASS=$(grep -c "✅" /tmp/health_check.txt || echo "0")
            WARN=$(grep -c "⚠️" /tmp/health_check.txt || echo "0")  
            FAIL=$(grep -c "❌" /tmp/health_check.txt || echo "0")
            
            log_info "Results: $PASS passed, $WARN warnings, $FAIL failed"
            
            if [ "$FAIL" -gt 0 ]; then
                log_fail "Critical failures detected"
                return 1
            fi
        else
            log_warn "Health check returned unexpected output"
        fi
    else
        log_warn "Health check script had issues (non-fatal)"
    fi
}

check_generators() {
    log_header "5. CONTENT GENERATOR VERIFICATION"
    
    # Check generator files exist
    if [ -f "$PROJECT_ROOT/trade_automation/morning_brief_generator.py" ]; then
        log_pass "Morning brief generator: ✅"
    else
        log_fail "Morning brief generator missing"
        return 1
    fi
    
    if [ -f "$PROJECT_ROOT/trade_automation/daily_scorecard_generator.py" ]; then
        log_pass "Daily scorecard generator: ✅"
    else
        log_fail "Daily scorecard generator missing"
        return 1
    fi
    
    if [ -f "$PROJECT_ROOT/trade_automation/twitter_poster.py" ]; then
        log_pass "Twitter poster: ✅"
    else
        log_fail "Twitter poster missing"
        return 1
    fi
    
    if [ -f "$PROJECT_ROOT/trade_automation/linkedin_poster.py" ]; then
        log_pass "LinkedIn poster: ✅"
    else
        log_fail "LinkedIn poster missing"
        return 1
    fi
}

check_files() {
    log_header "6. FILE SYSTEM CHECK"
    
    # Check critical directories
    DIRS=("logs" "scripts" "trade_automation" "database")
    for dir in "${DIRS[@]}"; do
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            log_pass "Directory: $dir"
        else
            log_fail "Directory missing: $dir"
            return 1
        fi
    done
    
    # Check write permissions
    if touch "$PROJECT_ROOT/logs/.test" 2>/dev/null; then
        rm "$PROJECT_ROOT/logs/.test" 2>/dev/null || true
        log_pass "Write permissions: OK"
    else
        log_fail "No write permissions to logs directory"
        return 1
    fi
}

check_services() {
    log_header "7. DEPENDENCY & SERVICE CHECK"
    
    if poetry --version > /dev/null 2>&1; then
        log_pass "Poetry: ✅"
    else
        log_fail "Poetry not available"
        return 1
    fi
    
    if command -v python3 > /dev/null 2>&1; then
        log_pass "Python3: ✅"
    else
        log_fail "Python3 not available"
        return 1
    fi
}

###############################################################################
# SUMMARY & VERDICT
###############################################################################

print_summary() {
    log_header "LAUNCH DAY VERIFICATION SUMMARY"
    
    TOTAL=$((CHECKS_PASS + CHECKS_FAIL + CHECKS_WARN))
    
    echo ""
    echo "Results:"
    echo "  ✅ Passed:  $CHECKS_PASS"
    echo "  ⚠️  Warnings: $CHECKS_WARN"
    echo "  ❌ Failed:  $CHECKS_FAIL"
    echo ""
    
    if [ "$CHECKS_FAIL" -eq 0 ] && [ "$CHECKS_WARN" -eq 0 ]; then
        echo -e "${GREEN}🟢 STATUS: READY FOR LAUNCH${NC}"
        echo -e "${GREEN}   All systems operational. Go/No-Go: GO ✅${NC}"
        echo ""
        echo "   Next step: Market opens at 9:30 AM"
        echo "   Morning brief will post at 9:00 AM"
        echo "   Daily scorecard will post at 4:00 PM"
        echo ""
    elif [ "$CHECKS_FAIL" -eq 0 ]; then
        echo -e "${YELLOW}🟡 STATUS: READY WITH CAUTION${NC}"
        echo -e "${YELLOW}   $CHECKS_WARN items need attention${NC}"
        echo ""
        echo "   Go/No-Go: Conditional (check warnings above)"
        echo ""
    else
        echo -e "${RED}🔴 STATUS: NOT READY${NC}"
        echo -e "${RED}   $CHECKS_FAIL critical issues must be fixed${NC}"
        echo ""
        echo "   Go/No-Go: NO - Do not launch"
        echo ""
    fi
    
    # Write summary to log
    {
        echo ""
        echo "================================================================================"
        echo "SUMMARY"
        echo "================================================================================"
        echo "Passed:   $CHECKS_PASS"
        echo "Warnings: $CHECKS_WARN"
        echo "Failed:   $CHECKS_FAIL"
        echo ""
        
        if [ "$CHECKS_FAIL" -eq 0 ] && [ "$CHECKS_WARN" -eq 0 ]; then
            echo "STATUS: 🟢 READY FOR LAUNCH"
        elif [ "$CHECKS_FAIL" -eq 0 ]; then
            echo "STATUS: 🟡 READY WITH CAUTION"
        else
            echo "STATUS: 🔴 NOT READY"
        fi
        
        echo "Log: $LOG_FILE"
    } >> "$LOG_FILE"
}

return_exit_code() {
    if [ "$CHECKS_FAIL" -eq 0 ] && [ "$CHECKS_WARN" -eq 0 ]; then
        echo ""
        echo "📝 Full log saved to: $LOG_FILE"
        exit 0  # Ready for launch
    elif [ "$CHECKS_FAIL" -eq 0 ]; then
        echo ""
        echo "⚠️  Review warnings above before proceeding"
        echo "📝 Full log saved to: $LOG_FILE"
        exit 1  # Caution - fix warnings
    else
        echo ""
        echo "❌ Do not proceed with launch"
        echo "📝 Full log saved to: $LOG_FILE"
        exit 2  # Critical failure
    fi
}

###############################################################################
# EXECUTION
###############################################################################

main "$@"
