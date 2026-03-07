#!/bin/bash
# MASTER LAUNCH SEQUENCE
# Run this at 6:00 AM Saturday morning
# Single command that runs through entire pre-launch checklist

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║           OPTIONSMAGIC MASTER LAUNCH SEQUENCE                 ║"
echo "║           Saturday, March 8, 2026 — 6:00 AM ET                ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd /home/openclaw/.openclaw/workspace/optionsmagic

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

function print_step() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║ $1"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS_COUNT++))
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL_COUNT++))
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# ============================================================================
# STEP 1: Verify Credentials
# ============================================================================
print_step "STEP 1: Verify Credentials"

if [ -z "$(grep 'TWITTER_API_KEY' .env 2>/dev/null)" ]; then
    print_error "Twitter credentials not found in .env"
    echo ""
    echo "INSTRUCTIONS:"
    echo "1. Get Twitter credentials from Zoe"
    echo "2. Run: bash INSTANT_CREDENTIAL_INJECTION.sh"
    echo "3. Then run this script again"
    echo ""
    exit 1
else
    print_success "Twitter credentials found"
fi

if [ -z "$(grep 'LINKEDIN_API_KEY' .env 2>/dev/null)" ]; then
    print_error "LinkedIn credentials not found in .env"
    exit 1
else
    print_success "LinkedIn credentials found"
fi

# ============================================================================
# STEP 2: Run Full Pipeline Test
# ============================================================================
print_step "STEP 2: Running Full Pipeline Dry-Run Test"

if poetry run python scripts/full_pipeline_dryrun.py > /tmp/pipeline_test.log 2>&1; then
    TEST_RESULT=$(grep "Total:" /tmp/pipeline_test.log | tail -1)
    if echo "$TEST_RESULT" | grep -q "6/6"; then
        print_success "All 6 pipeline tests passing"
    else
        print_error "Pipeline tests not all passing"
        tail -20 /tmp/pipeline_test.log
        exit 1
    fi
else
    print_error "Pipeline test execution failed"
    tail -30 /tmp/pipeline_test.log
    exit 1
fi

# ============================================================================
# STEP 3: Validate Credentials with API Connection Tests
# ============================================================================
print_step "STEP 3: Validating Credentials (Testing API Connections)"

poetry run python scripts/inject_and_validate_credentials.py > /tmp/cred_validation.log 2>&1

if grep -q "ALL CREDENTIALS PRESENT" /tmp/cred_validation.log; then
    print_success "All credentials validated"
else
    print_error "Credential validation failed"
    cat /tmp/cred_validation.log
    exit 1
fi

if grep -q "TWITTER API WORKING" /tmp/cred_validation.log; then
    print_success "Twitter API connection working"
else
    print_warning "Twitter API connection test inconclusive"
fi

if grep -q "LINKEDIN CREDENTIALS PRESENT" /tmp/cred_validation.log; then
    print_success "LinkedIn credentials verified"
else
    print_warning "LinkedIn credentials validation incomplete"
fi

# ============================================================================
# STEP 4: Verify System Infrastructure
# ============================================================================
print_step "STEP 4: Verifying System Infrastructure"

# Check logs directory
if [ -d logs ]; then
    print_success "Logs directory exists"
else
    mkdir -p logs
    print_success "Created logs directory"
fi

# Check disk space
DISK_AVAILABLE=$(df -h . | awk 'NR==2 {print $4}')
print_success "Disk space available: $DISK_AVAILABLE"

# Check Python environment
if poetry run python -c "import sys; sys.exit(0)" 2>/dev/null; then
    print_success "Python environment working"
else
    print_error "Python environment issue"
    exit 1
fi

# Test image generation
if poetry run python -c "from PIL import Image; Image.new('RGB', (100,100)).save('/tmp/test.png')" 2>/dev/null; then
    print_success "Image generation working"
else
    print_error "Image generation not working"
    exit 1
fi

# ============================================================================
# STEP 5: Verify Cron Job Setup Script
# ============================================================================
print_step "STEP 5: Verifying Cron Job Configuration"

if [ -f scripts/setup_cron_jobs.sh ]; then
    print_success "Cron setup script found"
    
    if [ -x scripts/setup_cron_jobs.sh ]; then
        print_success "Cron setup script is executable"
    else
        chmod +x scripts/setup_cron_jobs.sh
        print_success "Made cron setup script executable"
    fi
else
    print_error "Cron setup script not found"
    exit 1
fi

# ============================================================================
# STEP 6: Final Summary
# ============================================================================
print_step "LAUNCH READINESS SUMMARY"

echo "Test Results:"
echo "  ✅ Passed: $PASS_COUNT"
echo "  ❌ Failed: $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║            🟢 READY FOR LAUNCH AT 9:00 AM! 🚀                ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "NEXT STEPS (6:30 AM):"
    echo "  1. Enable cron jobs:"
    echo "     bash scripts/setup_cron_jobs.sh"
    echo ""
    echo "  2. Verify cron jobs installed:"
    echo "     crontab -l | grep morning_brief"
    echo ""
    echo "  3. Monitor market open at 9:00 AM:"
    echo "     tail -f logs/morning_brief.log"
    echo ""
    echo "MONITORING GUIDE:"
    echo "  See: SATURDAY_MONITORING_GUIDE.md"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    exit 0
else
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║           🔴 LAUNCH BLOCKED - ISSUES FOUND 🛑                ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Fix the issues above and rerun this script."
    echo ""
    exit 1
fi
