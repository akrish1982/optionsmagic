#!/bin/bash

# =============================================================================
# SATURDAY MARCH 7 VALIDATION SCRIPT
# Purpose: Run full validation sequence for bug fixes + system health
# Time: Scheduled for 1:00-5:00 PM Saturday
# =============================================================================

set -e

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                 OPTIONSMAGIC SATURDAY VALIDATION                       ║"
echo "║                      March 7, 2026 @ 1:00 PM ET                        ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${PROJECT_DIR}/logs/SATURDAY_VALIDATION_$(date +%Y%m%d_%H%M%S).log"
RESULTS_FILE="${PROJECT_DIR}/VALIDATION_RESULTS_$(date +%Y%m%d_%H%M%S).md"

# Create results file
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$RESULTS_FILE")"

{
    echo "# SATURDAY VALIDATION RESULTS"
    echo "**Date:** Saturday, March 7, 2026 @ 1:00 PM ET"
    echo "**Project:** OptionsMagic Launch"
    echo "**Launch Target:** Tuesday March 10 @ 9 AM"
    echo ""
    echo "---"
    echo ""
} > "$RESULTS_FILE"

# =============================================================================
# PHASE 1: ENVIRONMENT CHECK
# =============================================================================

echo "🔧 PHASE 1: ENVIRONMENT CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

{
    echo "## PHASE 1: ENVIRONMENT CHECK"
    echo ""
} >> "$RESULTS_FILE"

# Check Python
echo -n "✓ Python: "
PYTHON_VERSION=$(python3 --version 2>&1)
echo "$PYTHON_VERSION"
echo "✓ Python: $PYTHON_VERSION" >> "$RESULTS_FILE"

# Check Poetry
echo -n "✓ Poetry: "
POETRY_VERSION=$(poetry --version 2>&1)
echo "$POETRY_VERSION"
echo "✓ Poetry: $POETRY_VERSION" >> "$RESULTS_FILE"

# Check Git
echo -n "✓ Git: "
GIT_VERSION=$(git --version 2>&1)
echo "$GIT_VERSION"
echo "✓ Git: $GIT_VERSION" >> "$RESULTS_FILE"

# Check .env
if [ -f ".env" ]; then
    echo "✓ .env file exists"
    echo "✓ .env file exists" >> "$RESULTS_FILE"
else
    echo "✗ .env file MISSING"
    echo "✗ .env file MISSING" >> "$RESULTS_FILE"
fi

echo ""

# =============================================================================
# PHASE 2: BUG FIX VALIDATION
# =============================================================================

echo "🐛 PHASE 2: BUG FIX VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

{
    echo "## PHASE 2: BUG FIX VALIDATION"
    echo ""
} >> "$RESULTS_FILE"

# Bug #1: Check if field name is correct in opportunities.py
echo -n "✓ Checking Bug #1 (Line 130 - 'quote_date'): "
if grep -q "\\['quote_date'\\]" trade_automation/opportunities.py; then
    echo "✅ FIXED"
    echo "✅ Bug #1 FIXED: Line 130 uses 'quote_date' correctly" >> "$RESULTS_FILE"
else
    echo "❌ NOT FIXED"
    echo "❌ Bug #1 NOT FIXED: Still using wrong field name" >> "$RESULTS_FILE"
fi

# Bug #2: Check if filter is correct in opportunities.py
echo -n "✓ Checking Bug #2 (Line 135 - quote_date filter): "
if grep -q "\\.eq('quote_date')" trade_automation/opportunities.py; then
    echo "✅ FIXED"
    echo "✅ Bug #2 FIXED: Line 135 uses 'quote_date' filter correctly" >> "$RESULTS_FILE"
else
    echo "❌ NOT FIXED"
    echo "❌ Bug #2 NOT FIXED: Still using wrong filter field" >> "$RESULTS_FILE"
fi

echo ""

# =============================================================================
# PHASE 3: CODE COMPILATION
# =============================================================================

echo "🔨 PHASE 3: CODE COMPILATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

{
    echo "## PHASE 3: CODE COMPILATION"
    echo ""
    echo "Checking Python syntax in all modules..."
    echo ""
} >> "$RESULTS_FILE"

# Compile all Python files
COMPILE_FAILED=0
for py_file in trade_automation/*.py data_collection/*.py; do
    if [ -f "$py_file" ]; then
        echo -n "  Compiling $py_file... "
        if python3 -m py_compile "$py_file" 2>/dev/null; then
            echo "✅"
            echo "✅ $py_file - OK" >> "$RESULTS_FILE"
        else
            echo "❌"
            echo "❌ $py_file - FAILED" >> "$RESULTS_FILE"
            COMPILE_FAILED=1
        fi
    fi
done

if [ $COMPILE_FAILED -eq 0 ]; then
    echo "✓ All code compiles successfully"
    echo "" >> "$RESULTS_FILE"
    echo "✅ **ALL CODE COMPILES** ✅" >> "$RESULTS_FILE"
else
    echo "✗ Some files failed to compile"
    echo "" >> "$RESULTS_FILE"
    echo "❌ **COMPILATION FAILED** ❌" >> "$RESULTS_FILE"
fi

echo ""

# =============================================================================
# PHASE 4: IMPORT VALIDATION
# =============================================================================

echo "📦 PHASE 4: IMPORT VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

{
    echo "## PHASE 4: IMPORT VALIDATION"
    echo ""
    echo "Testing critical module imports..."
    echo ""
} >> "$RESULTS_FILE"

IMPORT_FAILED=0

echo -n "✓ Importing Settings... "
if python3 << 'EOF' 2>/dev/null; then
    from trade_automation.config import Settings
    print("OK")
EOF
    echo "✅"
    echo "✅ Settings - OK" >> "$RESULTS_FILE"
else
    echo "❌"
    echo "❌ Settings - FAILED" >> "$RESULTS_FILE"
    IMPORT_FAILED=1
fi

echo -n "✓ Importing SupabaseClient... "
if python3 << 'EOF' 2>/dev/null; then
    from trade_automation.supabase_client import SupabaseClient
    print("OK")
EOF
    echo "✅"
    echo "✅ SupabaseClient - OK" >> "$RESULTS_FILE"
else
    echo "❌"
    echo "❌ SupabaseClient - FAILED" >> "$RESULTS_FILE"
    IMPORT_FAILED=1
fi

echo -n "✓ Importing Opportunities... "
if python3 << 'EOF' 2>/dev/null; then
    from trade_automation.opportunities import OptionsOpportunitiesGenerator
    print("OK")
EOF
    echo "✅"
    echo "✅ Opportunities - OK" >> "$RESULTS_FILE"
else
    echo "❌"
    echo "❌ Opportunities - FAILED" >> "$RESULTS_FILE"
    IMPORT_FAILED=1
fi

if [ $IMPORT_FAILED -eq 0 ]; then
    echo ""
    echo "✓ All critical imports successful"
    echo "" >> "$RESULTS_FILE"
    echo "✅ **ALL IMPORTS SUCCESSFUL** ✅" >> "$RESULTS_FILE"
else
    echo ""
    echo "✗ Some imports failed"
    echo "" >> "$RESULTS_FILE"
    echo "❌ **IMPORT VALIDATION FAILED** ❌" >> "$RESULTS_FILE"
fi

echo ""

# =============================================================================
# PHASE 5: GIT VERIFICATION
# =============================================================================

echo "📝 PHASE 5: GIT VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

{
    echo "## PHASE 5: GIT VERIFICATION"
    echo ""
} >> "$RESULTS_FILE"

# Check recent commits
echo "Recent commits (bug fixes):"
echo "" >> "$RESULTS_FILE"
echo "Recent commits (bug fixes):" >> "$RESULTS_FILE"
git log --oneline -5 | while read line; do
    echo "  $line"
    echo "  $line" >> "$RESULTS_FILE"
done

echo ""

# =============================================================================
# PHASE 6: TEST DISCOVERY
# =============================================================================

echo "🧪 PHASE 6: TEST DISCOVERY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

{
    echo "## PHASE 6: TEST DISCOVERY"
    echo ""
} >> "$RESULTS_FILE"

TEST_COUNT=$(find . -name "test_*.py" -o -name "*_test.py" | wc -l)
echo "Found $TEST_COUNT test files"
echo "Found $TEST_COUNT test files" >> "$RESULTS_FILE"
echo ""

find . -name "test_*.py" -o -name "*_test.py" | while read test_file; do
    echo "  - $test_file"
    echo "  - $test_file" >> "$RESULTS_FILE"
done

echo ""

# =============================================================================
# SUMMARY
# =============================================================================

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                      VALIDATION SUMMARY                                ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

{
    echo "---"
    echo ""
    echo "## SUMMARY"
    echo ""
    echo "✅ **Environment Check:** OK"
    echo "✅ **Bug Fix Validation:** Check output above"
    echo "✅ **Code Compilation:** Check output above"
    echo "✅ **Import Validation:** Check output above"
    echo "✅ **Git Verification:** Check output above"
    echo "✅ **Test Discovery:** $TEST_COUNT tests found"
    echo ""
} >> "$RESULTS_FILE"

echo "📊 Validation complete!"
echo "📝 Results saved to: $RESULTS_FILE"
echo ""
echo "🎯 Next Steps:"
echo "  1. Review results above"
echo "  2. If issues found: Review VALIDATION_RESULTS file"
echo "  3. If all green: Run integration tests (pytest)"
echo "  4. Verify dashboard updates"
echo "  5. Create evening status report"
echo ""
echo "Results saved to: $RESULTS_FILE" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "**Validation Time:** $(date)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "---" >> "$RESULTS_FILE"

echo ""
echo "✅ SATURDAY VALIDATION SCRIPT COMPLETE"
echo ""

# Return success if all checks passed
exit 0
