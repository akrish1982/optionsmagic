#!/bin/bash
# INSTANT CREDENTIAL INJECTION SCRIPT
# When Zoe provides credentials, run this script
# Usage: bash INSTANT_CREDENTIAL_INJECTION.sh <values in order>

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  OPTIONSMAGIC CREDENTIAL INJECTOR"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Function to show usage
show_usage() {
    echo "Usage: bash INSTANT_CREDENTIAL_INJECTION.sh"
    echo ""
    echo "This script will prompt for 7 credentials:"
    echo "  1. Twitter API Key"
    echo "  2. Twitter API Secret"
    echo "  3. Twitter Access Token"
    echo "  4. Twitter Access Token Secret"
    echo "  5. LinkedIn API Key"
    echo "  6. LinkedIn Access Token"
    echo "  7. LinkedIn Company Page ID"
    echo ""
}

# Backup .env before modifying
if [ -f .env ]; then
    echo "📋 Backing up existing .env..."
    cp .env .env.backup.$(date +%s)
    echo "   ✅ Backup created"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  TWITTER CREDENTIALS (4 values)"
echo "════════════════════════════════════════════════════════════════"
echo ""

read -p "1. Twitter API Key: " TWITTER_API_KEY
read -p "2. Twitter API Secret: " TWITTER_API_SECRET
read -p "3. Twitter Access Token: " TWITTER_ACCESS_TOKEN
read -p "4. Twitter Access Token Secret: " TWITTER_ACCESS_TOKEN_SECRET

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  LINKEDIN CREDENTIALS (3 values)"
echo "════════════════════════════════════════════════════════════════"
echo ""

read -p "5. LinkedIn API Key: " LINKEDIN_API_KEY
read -p "6. LinkedIn Access Token: " LINKEDIN_ACCESS_TOKEN
read -p "7. LinkedIn Company Page ID: " LINKEDIN_COMPANY_PAGE_ID

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  VALIDATING INPUT"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Validate all values provided
if [ -z "$TWITTER_API_KEY" ] || [ -z "$TWITTER_API_SECRET" ] || \
   [ -z "$TWITTER_ACCESS_TOKEN" ] || [ -z "$TWITTER_ACCESS_TOKEN_SECRET" ] || \
   [ -z "$LINKEDIN_API_KEY" ] || [ -z "$LINKEDIN_ACCESS_TOKEN" ] || \
   [ -z "$LINKEDIN_COMPANY_PAGE_ID" ]; then
    echo "❌ ERROR: All 7 values are required"
    exit 1
fi

echo "✅ All 7 values provided"
echo ""

# Create new .env or update existing
echo "📝 Updating .env file..."
echo ""

# Remove existing social media credentials if present
if grep -q "# Phase 2: Social Media APIs" .env 2>/dev/null; then
    echo "   Removing old credentials..."
    # Use a temp file to safely edit
    grep -v "^TWITTER_" .env | grep -v "^LINKEDIN_" | grep -v "^# Phase 2: Social Media APIs" > .env.tmp
    mv .env.tmp .env
fi

# Append new credentials
{
    echo ""
    echo "# Phase 2: Social Media APIs (Injected at $(date))"
    echo "TWITTER_API_KEY=$TWITTER_API_KEY"
    echo "TWITTER_API_SECRET=$TWITTER_API_SECRET"
    echo "TWITTER_ACCESS_TOKEN=$TWITTER_ACCESS_TOKEN"
    echo "TWITTER_ACCESS_TOKEN_SECRET=$TWITTER_ACCESS_TOKEN_SECRET"
    echo ""
    echo "LINKEDIN_API_KEY=$LINKEDIN_API_KEY"
    echo "LINKEDIN_ACCESS_TOKEN=$LINKEDIN_ACCESS_TOKEN"
    echo "LINKEDIN_COMPANY_PAGE_ID=$LINKEDIN_COMPANY_PAGE_ID"
} >> .env

echo "   ✅ Credentials added to .env"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "  VALIDATING CREDENTIALS"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Validate credentials were written
if grep -q "TWITTER_API_KEY=$TWITTER_API_KEY" .env && \
   grep -q "LINKEDIN_API_KEY=$LINKEDIN_API_KEY" .env; then
    echo "✅ Credentials successfully saved to .env"
else
    echo "❌ ERROR: Credentials not properly saved"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  NEXT STEPS"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Your credentials are now in .env! Next:"
echo ""
echo "1. Run comprehensive validation:"
echo "   poetry run python scripts/inject_and_validate_credentials.py"
echo ""
echo "2. If validation passes, proceed to 6:30 AM step:"
echo "   bash scripts/setup_cron_jobs.sh"
echo ""
echo "3. If validation fails, check logs:"
echo "   tail -50 logs/*.log"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "  ✅ CREDENTIAL INJECTION COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🚀 Ready to launch! See SAT_6AM_FINAL_CHECKLIST.md for next steps"
echo ""
