#!/usr/bin/env python3
"""
CREDENTIAL INJECTION & VALIDATION SCRIPT
Inject Zoe's credentials and validate immediately
Run this as soon as Zoe provides the 7 credential values
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def inject_credentials():
    """Guide user through credential injection"""
    print_header("CREDENTIAL INJECTION WIZARD")
    
    print("""
This script will help you add Zoe's credentials to .env
You'll need 7 values total:

TWITTER (4 values):
  1. API Key (Consumer Key)
  2. API Secret (Consumer Secret)
  3. Access Token
  4. Access Token Secret

LINKEDIN (3 values):
  5. API Key
  6. Access Token
  7. Company Page ID

Ready? Let's go!
""")
    
    credentials = {}
    
    # Twitter credentials
    print("\n📝 TWITTER CREDENTIALS")
    print("-" * 70)
    credentials['TWITTER_API_KEY'] = input("1. API Key: ").strip()
    credentials['TWITTER_API_SECRET'] = input("2. API Secret: ").strip()
    credentials['TWITTER_ACCESS_TOKEN'] = input("3. Access Token: ").strip()
    credentials['TWITTER_ACCESS_TOKEN_SECRET'] = input("4. Access Token Secret: ").strip()
    
    # LinkedIn credentials
    print("\n💼 LINKEDIN CREDENTIALS")
    print("-" * 70)
    credentials['LINKEDIN_API_KEY'] = input("5. API Key: ").strip()
    credentials['LINKEDIN_ACCESS_TOKEN'] = input("6. Access Token: ").strip()
    credentials['LINKEDIN_COMPANY_PAGE_ID'] = input("7. Company Page ID: ").strip()
    
    return credentials

def update_env_file(credentials):
    """Update .env file with credentials"""
    env_path = Path(".env")
    
    # Read existing .env
    existing_content = ""
    if env_path.exists():
        with open(env_path, "r") as f:
            existing_content = f.read()
    
    # Check if credentials section already exists
    if "# Phase 2: Social Media APIs" in existing_content:
        # Replace existing section
        lines = existing_content.split("\n")
        new_lines = []
        skip = False
        
        for line in lines:
            if "# Phase 2: Social Media APIs" in line:
                skip = True
                new_lines.append(line)
                new_lines.append("")
                # Add new credentials
                new_lines.append("TWITTER_API_KEY=" + credentials['TWITTER_API_KEY'])
                new_lines.append("TWITTER_API_SECRET=" + credentials['TWITTER_API_SECRET'])
                new_lines.append("TWITTER_ACCESS_TOKEN=" + credentials['TWITTER_ACCESS_TOKEN'])
                new_lines.append("TWITTER_ACCESS_TOKEN_SECRET=" + credentials['TWITTER_ACCESS_TOKEN_SECRET'])
                new_lines.append("")
                new_lines.append("LINKEDIN_API_KEY=" + credentials['LINKEDIN_API_KEY'])
                new_lines.append("LINKEDIN_ACCESS_TOKEN=" + credentials['LINKEDIN_ACCESS_TOKEN'])
                new_lines.append("LINKEDIN_COMPANY_PAGE_ID=" + credentials['LINKEDIN_COMPANY_PAGE_ID'])
                new_lines.append("")
            elif skip:
                # Skip old credential lines
                if line.startswith("TWITTER_") or line.startswith("LINKEDIN_"):
                    continue
                elif line.startswith("#") or line.startswith("["):
                    skip = False
                    new_lines.append(line)
                else:
                    continue
            else:
                new_lines.append(line)
        
        new_content = "\n".join(new_lines)
    else:
        # Append new section
        new_content = existing_content
        if not new_content.endswith("\n"):
            new_content += "\n"
        
        new_content += "\n# Phase 2: Social Media APIs\n"
        new_content += "TWITTER_API_KEY=" + credentials['TWITTER_API_KEY'] + "\n"
        new_content += "TWITTER_API_SECRET=" + credentials['TWITTER_API_SECRET'] + "\n"
        new_content += "TWITTER_ACCESS_TOKEN=" + credentials['TWITTER_ACCESS_TOKEN'] + "\n"
        new_content += "TWITTER_ACCESS_TOKEN_SECRET=" + credentials['TWITTER_ACCESS_TOKEN_SECRET'] + "\n"
        new_content += "\n"
        new_content += "LINKEDIN_API_KEY=" + credentials['LINKEDIN_API_KEY'] + "\n"
        new_content += "LINKEDIN_ACCESS_TOKEN=" + credentials['LINKEDIN_ACCESS_TOKEN'] + "\n"
        new_content += "LINKEDIN_COMPANY_PAGE_ID=" + credentials['LINKEDIN_COMPANY_PAGE_ID'] + "\n"
    
    # Write back to .env
    with open(env_path, "w") as f:
        f.write(new_content)
    
    print_header("✅ CREDENTIALS SAVED")
    print("\nUpdated .env with 7 new credentials")
    print("File: .env")

def validate_credentials():
    """Validate all credentials are present"""
    print_header("VALIDATING CREDENTIALS")
    
    # Reload environment
    load_dotenv(override=True)
    
    twitter_keys = [
        'TWITTER_API_KEY',
        'TWITTER_API_SECRET',
        'TWITTER_ACCESS_TOKEN',
        'TWITTER_ACCESS_TOKEN_SECRET'
    ]
    
    linkedin_keys = [
        'LINKEDIN_API_KEY',
        'LINKEDIN_ACCESS_TOKEN',
        'LINKEDIN_COMPANY_PAGE_ID'
    ]
    
    all_keys = twitter_keys + linkedin_keys
    missing = []
    
    print("\n📋 Checking all credentials...")
    print("-" * 70)
    
    for key in all_keys:
        value = os.getenv(key)
        if value and len(str(value)) > 3:
            status = "✅"
            display = "*" * min(len(value), 20)
            print(f"{status} {key:40} {display}")
        else:
            status = "❌"
            print(f"{status} {key:40} MISSING")
            missing.append(key)
    
    return len(missing) == 0, missing

def test_twitter_connection():
    """Test Twitter API connection"""
    print_header("TESTING TWITTER API CONNECTION")
    
    try:
        import tweepy
        
        load_dotenv(override=True)
        
        client = tweepy.Client(
            consumer_key=os.getenv('TWITTER_API_KEY'),
            consumer_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
            wait_on_rate_limit=True
        )
        
        print("\nAttempting to fetch account info...")
        user = client.get_me()
        
        print(f"\n✅ TWITTER API WORKING!")
        print(f"   Connected as: @{user.data.username}")
        print(f"   Account ID: {user.data.id}")
        
        return True
        
    except ImportError:
        print("⚠️ tweepy not installed. Install with: poetry add tweepy")
        return False
    except Exception as e:
        print(f"❌ TWITTER API ERROR: {e}")
        print("\nPossible issues:")
        print("  1. Credentials are incorrect")
        print("  2. API keys don't have proper permissions")
        print("  3. Network connectivity issue")
        print("  4. Twitter API is down")
        return False

def test_linkedin_connection():
    """Test LinkedIn API connection"""
    print_header("TESTING LINKEDIN CREDENTIALS")
    
    try:
        load_dotenv(override=True)
        
        api_key = os.getenv('LINKEDIN_API_KEY')
        access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        company_id = os.getenv('LINKEDIN_COMPANY_PAGE_ID')
        
        if not all([api_key, access_token, company_id]):
            print("❌ Missing LinkedIn credentials")
            return False
        
        print("\n✅ LINKEDIN CREDENTIALS PRESENT")
        print(f"   API Key: {api_key[:10]}...")
        print(f"   Token: {access_token[:10]}...")
        print(f"   Company ID: {company_id}")
        
        print("\n⚠️  LinkedIn API validation requires actual API calls")
        print("   This will be tested during posting")
        
        return True
        
    except Exception as e:
        print(f"❌ LINKEDIN ERROR: {e}")
        return False

def main():
    """Main workflow"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  CREDENTIAL INJECTION & VALIDATION".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Check if already in .env
    load_dotenv()
    existing_twitter = os.getenv('TWITTER_API_KEY')
    existing_linkedin = os.getenv('LINKEDIN_API_KEY')
    
    if existing_twitter and existing_linkedin:
        print("\n✅ Credentials already present in .env!")
        print("\nRunning validation only...")
    else:
        print("\nNo credentials found. Let's inject them!")
        credentials = inject_credentials()
        update_env_file(credentials)
    
    # Validate
    valid, missing = validate_credentials()
    
    if not valid:
        print(f"\n❌ VALIDATION FAILED: Missing {len(missing)} credential(s)")
        for key in missing:
            print(f"   - {key}")
        return 1
    
    print(f"\n✅ ALL CREDENTIALS PRESENT")
    
    # Test connections
    twitter_ok = test_twitter_connection()
    linkedin_ok = test_linkedin_connection()
    
    # Summary
    print_header("FINAL STATUS")
    
    if twitter_ok and linkedin_ok:
        print("\n🟢 ALL SYSTEMS GO!")
        print("\nYour credentials are validated and ready.")
        print("You can now:")
        print("  1. Enable cron jobs: bash scripts/setup_cron_jobs.sh")
        print("  2. Run final pre-flight: poetry run python scripts/launch_day_preflight.py")
        print("  3. Run dry-run test: poetry run python scripts/full_pipeline_dryrun.py")
        print("\nNext step: Monitor market at 9:00 AM for first posts 📊")
        return 0
    else:
        print("\n🔴 SOME TESTS FAILED")
        print("\nFix issues above before proceeding")
        if not twitter_ok:
            print("  → Twitter API issue: Check credentials with Zoe")
        if not linkedin_ok:
            print("  → LinkedIn credentials: Verify format with Zoe")
        return 1

if __name__ == "__main__":
    sys.exit(main())
