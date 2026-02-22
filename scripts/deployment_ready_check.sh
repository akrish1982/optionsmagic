#!/bin/bash

# Deployment Ready Check - Run this Monday morning before enabling cron jobs
# Ensures all systems are operational and ready for trading

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
}

check_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    exit 1
}

check_warning() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

print_header "DEPLOYMENT READY CHECK - Monday Morning Verification"
echo "Timestamp: $(date)"
echo "Project: $PROJECT_DIR"

# Check 1: Python environment
print_header "1. Python Environment"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    check_pass "Python installed: $PYTHON_VERSION"
else
    check_fail "Python3 not found"
fi

# Check 2: Poetry environment
print_header "2. Poetry Environment"
if command -v poetry &> /dev/null; then
    POETRY_VERSION=$(poetry --version)
    check_pass "Poetry installed: $POETRY_VERSION"
else
    check_fail "Poetry not found"
fi

# Check 3: Environment file
print_header "3. Environment Configuration"
if [ -f ".env" ]; then
    check_pass ".env file exists"
    
    # Check required variables
    if grep -q "SUPABASE_URL" .env; then
        check_pass "SUPABASE_URL configured"
    else
        check_fail "SUPABASE_URL not in .env"
    fi
    
    if grep -q "TRADESTATION_ENV" .env; then
        check_pass "TRADESTATION_ENV configured"
    else
        check_fail "TRADESTATION_ENV not in .env"
    fi
    
    if grep -q "TELEGRAM_BOT_TOKEN" .env; then
        check_pass "TELEGRAM_BOT_TOKEN configured"
    else
        check_fail "TELEGRAM_BOT_TOKEN not in .env"
    fi
else
    check_fail ".env file not found"
fi

# Check 4: Required directories
print_header "4. Directory Structure"
for dir in logs database/ddl trade_automation tests scripts; do
    if [ -d "$dir" ]; then
        check_pass "Directory exists: $dir"
    else
        check_fail "Directory missing: $dir"
    fi
done

# Check 5: Key code files
print_header "5. Code Files"
for file in \
    "trade_automation/proposal_worker.py" \
    "trade_automation/approval_worker.py" \
    "trade_automation/position_manager.py" \
    "trade_automation/exit_automation.py"; do
    if [ -f "$file" ]; then
        check_pass "File exists: $file"
    else
        check_fail "File missing: $file"
    fi
done

# Check 6: Database migration file
print_header "6. Database Migration"
if [ -f "database/ddl/002_positions_and_trade_history.sql" ]; then
    check_pass "Migration file exists: 002_positions_and_trade_history.sql"
    check_warning "Remember: Migration must be applied manually in Supabase SQL editor"
else
    check_fail "Migration file not found: database/ddl/002_positions_and_trade_history.sql"
fi

# Check 7: Run Python validation
print_header "7. Python Package Validation"
if poetry run python3 scripts/pre_deployment_validation.py; then
    check_pass "Pre-deployment validation passed"
else
    check_fail "Pre-deployment validation failed - see errors above"
fi

# Check 8: Git status
print_header "8. Version Control"
if command -v git &> /dev/null; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    check_pass "Git branch: $BRANCH, commit: $COMMIT"
else
    check_warning "Git not found - version control unavailable"
fi

# Check 9: Last successful test run
print_header "9. Test Status"
if [ -d "tests" ]; then
    TEST_COUNT=$(find tests -name "test_*.py" | wc -l)
    check_pass "Found $TEST_COUNT test files"
    check_warning "Run: poetry run pytest tests/ -v (before production)"
else
    check_warning "Tests directory not found"
fi

# Check 10: Logs directory writable
print_header "10. Logs Directory"
if [ -w "logs" ]; then
    check_pass "Logs directory writable"
else
    check_warning "Logs directory not writable - will try to create logs on first run"
fi

# Final summary
print_header "DEPLOYMENT READY CHECK COMPLETE"

echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ SYSTEM READY FOR DEPLOYMENT${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo "1. Verify Telegram bot receives messages (test proposal_worker manually)"
echo "2. Check Supabase database is accessible"
echo "3. Enable cron jobs (follow CRON_JOBS_CONFIG.md)"
echo "4. Monitor logs: tail -f logs/cron.log"
echo ""
echo "To run first proposal manually:"
echo "  poetry run python -m trade_automation.proposal_worker"
echo ""
echo "To test exit automation:"
echo "  poetry run python -m trade_automation.exit_automation"
echo ""

exit 0
