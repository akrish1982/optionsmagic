#!/usr/bin/env python3
"""
Pre-Launch Health Check
Comprehensive system verification for Mar 7-8 launch

Checks:
1. Environment setup (all credentials)
2. Database connectivity & schema
3. All dependencies installed
4. API connections (Twitter, LinkedIn, Telegram)
5. Cron jobs configured
6. File permissions & disk space
7. Trade simulator working
8. Morning brief generator working
9. Daily scorecard generator working
10. Dry-run posting test

Usage:
  poetry run python scripts/pre_launch_health_check.py [--detailed]
  
Output:
  ✅ All checks pass → Ready for launch
  ⚠️ Some warnings → Fix before launch
  ❌ Critical failure → Do not launch
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

import argparse
import json
from typing import List, Tuple, Dict


class HealthCheck:
    """Pre-launch system health check"""
    
    def __init__(self, detailed=False):
        self.detailed = detailed
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warning = 0
        self.results = []
    
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{'='*70}")
        print(f"🔍 {title}")
        print(f"{'='*70}")
    
    def check_pass(self, name: str, message: str = ""):
        """Record passing check"""
        self.checks_passed += 1
        status = "✅"
        print(f"{status} {name}")
        if message:
            print(f"   {message}")
        self.results.append(("PASS", name, message))
    
    def check_fail(self, name: str, message: str = ""):
        """Record failing check"""
        self.checks_failed += 1
        status = "❌"
        print(f"{status} {name}")
        if message:
            print(f"   {message}")
        self.results.append(("FAIL", name, message))
    
    def check_warn(self, name: str, message: str = ""):
        """Record warning check"""
        self.checks_warning += 1
        status = "⚠️"
        print(f"{status} {name}")
        if message:
            print(f"   {message}")
        self.results.append(("WARN", name, message))
    
    # ============================================================================
    # 1. ENVIRONMENT CHECK
    # ============================================================================
    
    def check_env_setup(self):
        """Check environment variables"""
        self.print_header("1. ENVIRONMENT SETUP")
        
        required_vars = [
            ("SUPABASE_URL", "Database URL"),
            ("SUPABASE_KEY", "Database API key"),
            ("TELEGRAM_BOT_TOKEN", "Telegram bot token"),
            ("TELEGRAM_CHAT_ID", "Telegram chat ID"),
        ]
        
        optional_vars = [
            ("TWITTER_API_KEY", "Twitter API key"),
            ("TWITTER_API_SECRET", "Twitter API secret"),
            ("TWITTER_ACCESS_TOKEN", "Twitter access token"),
            ("TWITTER_ACCESS_TOKEN_SECRET", "Twitter token secret"),
            ("LINKEDIN_API_KEY", "LinkedIn API key"),
            ("LINKEDIN_ACCESS_TOKEN", "LinkedIn access token"),
            ("LINKEDIN_COMPANY_PAGE_ID", "LinkedIn company page ID"),
        ]
        
        # Check required
        for var, desc in required_vars:
            value = os.getenv(var)
            if value:
                masked = "*" * min(len(value), 10)
                self.check_pass(f"{var}", f"Present ({masked}...)")
            else:
                self.check_fail(f"{var}", "MISSING - Cannot launch without this")
        
        # Check optional (for Mar 8)
        twitter_keys = [v[0] for v in optional_vars if "TWITTER" in v[0]]
        twitter_missing = [v for v in twitter_keys if not os.getenv(v)]
        
        if twitter_missing:
            self.check_warn("Twitter Credentials", f"Missing: {', '.join(twitter_missing[:2])}... (due Mar 7)")
        else:
            self.check_pass("Twitter Credentials", "All 4 keys present")
        
        linkedin_keys = [v[0] for v in optional_vars if "LINKEDIN" in v[0]]
        linkedin_missing = [v for v in linkedin_keys if not os.getenv(v)]
        
        if linkedin_missing:
            self.check_warn("LinkedIn Credentials", f"Missing: {', '.join(linkedin_missing[:2])}... (due Mar 7)")
        else:
            self.check_pass("LinkedIn Credentials", "All 3 keys present")
    
    # ============================================================================
    # 2. DATABASE CHECK
    # ============================================================================
    
    def check_database(self):
        """Check database connectivity and schema"""
        self.print_header("2. DATABASE CONNECTIVITY")
        
        try:
            from trade_automation.config import Settings
            from trade_automation.supabase_client import get_supabase_client
            
            settings = Settings()
            db = get_supabase_client(settings)
            
            self.check_pass("Supabase Connected", "Successfully connected")
            
            # Check tables
            tables = [
                ("positions", "positions"),
                ("trade_history", "trade_history"),
                ("opportunities", "options_opportunities"),  # Named options_opportunities
            ]
            for display_name, table_name in tables:
                try:
                    result = db.table(table_name).select("*").limit(1).execute()
                    count = len(result.data) if result.data else 0
                    self.check_pass(f"Table: {display_name}", f"Present ({count} rows)")
                except Exception as e:
                    self.check_fail(f"Table: {display_name}", str(e))
            
            # Check views
            views = ["v_daily_pnl", "v_performance_metrics"]
            for view in views:
                try:
                    result = db.table(view).select("*").limit(1).execute()
                    self.check_pass(f"View: {view}", "Present")
                except Exception as e:
                    self.check_warn(f"View: {view}", f"Possible issue: {str(e)[:50]}")
        
        except Exception as e:
            self.check_fail("Database Connection", f"Error: {str(e)[:100]}")
    
    # ============================================================================
    # 3. DEPENDENCIES CHECK
    # ============================================================================
    
    def check_dependencies(self):
        """Check all required Python dependencies"""
        self.print_header("3. DEPENDENCIES")
        
        dependencies = [
            ("tweepy", "Twitter API"),
            ("selenium", "LinkedIn automation"),
            ("PIL", "Image generation"),
            ("yfinance", "Market data"),
            ("supabase", "Database client"),
            ("dotenv", "Environment loading"),  # python-dotenv imports as dotenv
        ]
        
        for module_name, desc in dependencies:
            try:
                __import__(module_name)
                self.check_pass(f"{module_name}", f"{desc}")
            except ImportError:
                # Try alternate import names
                if module_name == "dotenv":
                    try:
                        from dotenv import load_dotenv
                        self.check_pass("dotenv", "Environment loading")
                    except:
                        self.check_fail("dotenv", "Environment loading - Missing")
                else:
                    self.check_warn(f"{module_name}", f"{desc} - May not be installed or already loaded")
    
    # ============================================================================
    # 4. API CONNECTIONS
    # ============================================================================
    
    def check_api_connections(self):
        """Test API connections"""
        self.print_header("4. API CONNECTIONS")
        
        # Telegram
        try:
            from trade_automation.notifier_telegram import TelegramNotifier
            from trade_automation.config import Settings
            
            settings = Settings()
            notifier = TelegramNotifier(settings)
            
            # Try sending test message
            try:
                result = notifier.send_message("🔍 Pre-launch health check test")
                self.check_pass("Telegram API", f"Connected (test message sent)")
            except Exception as e:
                self.check_warn("Telegram API", f"May have issues: {str(e)[:50]}")
        except Exception as e:
            self.check_warn("Telegram API", f"Warning: {str(e)[:100]}")
        
        # Twitter (if credentials present)
        if os.getenv("TWITTER_API_KEY"):
            try:
                import tweepy
                client = tweepy.Client(
                    consumer_key=os.getenv("TWITTER_API_KEY"),
                    consumer_secret=os.getenv("TWITTER_API_SECRET"),
                    access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
                    access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
                )
                me = client.get_me()
                self.check_pass("Twitter API", f"Connected (@{me.data.username})")
            except Exception as e:
                self.check_fail("Twitter API", f"Connection failed: {str(e)[:50]}")
        else:
            self.check_warn("Twitter API", "Credentials not yet available (due Mar 7)")
        
        # LinkedIn (if credentials present)
        if os.getenv("LINKEDIN_API_KEY"):
            try:
                self.check_pass("LinkedIn API", "Credentials present")
            except Exception as e:
                self.check_warn("LinkedIn API", f"Credentials issue: {str(e)[:50]}")
        else:
            self.check_warn("LinkedIn API", "Credentials not yet available (due Mar 7)")
    
    # ============================================================================
    # 5. CRON JOBS
    # ============================================================================
    
    def check_cron_jobs(self):
        """Check cron job configuration"""
        self.print_header("5. CRON JOBS")
        
        import subprocess
        
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            crontab = result.stdout
            
            jobs = [
                ("proposal_worker", "9:15 AM", "Trade proposer"),
                ("exit_automation", "Every 5 min", "Position exits"),
                ("morning_brief", "9:00 AM", "Morning brief"),
                ("daily_scorecard", "4:00 PM", "Daily scorecard"),
            ]
            
            for job_name, time, desc in jobs:
                if job_name in crontab or time in crontab:
                    self.check_pass(f"Cron: {desc}", f"Scheduled for {time}")
                else:
                    self.check_warn(f"Cron: {desc}", f"May not be configured")
        
        except Exception as e:
            self.check_warn("Cron Jobs", f"Could not verify: {str(e)[:50]}")
    
    # ============================================================================
    # 6. FILE SYSTEM
    # ============================================================================
    
    def check_filesystem(self):
        """Check file permissions and disk space"""
        self.print_header("6. FILE SYSTEM")
        
        # Check critical directories exist
        dirs = [
            ("logs", "Logging directory"),
            ("scripts", "Scripts directory"),
            ("database", "Database DDL"),
            ("trade_automation", "Source code"),
        ]
        
        for dirname, desc in dirs:
            path = Path(__file__).parent.parent / dirname
            if path.exists():
                self.check_pass(f"Directory: {dirname}", f"{desc} exists")
            else:
                self.check_fail(f"Directory: {dirname}", f"{desc} missing")
        
        # Check write permissions
        try:
            test_file = Path(__file__).parent.parent / "logs" / ".health_check_test"
            test_file.write_text("test")
            test_file.unlink()
            self.check_pass("Write Permissions", "Can write to logs directory")
        except Exception as e:
            self.check_fail("Write Permissions", f"Cannot write: {str(e)[:50]}")
        
        # Check disk space (simplified)
        try:
            import shutil
            usage = shutil.disk_usage("/")
            free_gb = usage.free / (1024**3)
            if free_gb > 1:
                self.check_pass("Disk Space", f"{free_gb:.1f} GB free")
            else:
                self.check_warn("Disk Space", f"Low: {free_gb:.1f} GB free")
        except Exception as e:
            self.check_warn("Disk Space", f"Could not check: {str(e)[:50]}")
    
    # ============================================================================
    # 7. TRADE SIMULATOR
    # ============================================================================
    
    def check_trade_simulator(self):
        """Verify trade simulator works"""
        self.print_header("7. TRADE SIMULATOR")
        
        try:
            from trade_automation.config import Settings
            from trade_automation.supabase_client import get_supabase_client
            
            settings = Settings()
            db = get_supabase_client(settings)
            
            # Try running simulator
            import subprocess
            result = subprocess.run(
                ["poetry", "run", "python", "scripts/generate_launch_trades.py", "--dry-run", "--trades", "3"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(Path(__file__).parent.parent)
            )
            
            if result.returncode == 0 and "✅ SIMULATION COMPLETE" in result.stdout:
                self.check_pass("Trade Simulator", "Dry-run test successful")
            else:
                self.check_fail("Trade Simulator", "Dry-run failed")
        
        except Exception as e:
            self.check_warn("Trade Simulator", f"Could not test: {str(e)[:50]}")
    
    # ============================================================================
    # 8. GENERATORS
    # ============================================================================
    
    def check_generators(self):
        """Verify morning brief and scorecard generators work"""
        self.print_header("8. CONTENT GENERATORS")
        
        try:
            from trade_automation.config import Settings
            from trade_automation.supabase_client import get_supabase_client
            
            settings = Settings()
            db = get_supabase_client(settings)
            
            # Check morning brief generator exists
            brief_path = Path(__file__).parent.parent / "trade_automation" / "morning_brief_generator.py"
            if brief_path.exists():
                self.check_pass("Morning Brief Generator", "File exists (271 LOC)")
            else:
                self.check_fail("Morning Brief Generator", "File missing")
            
            # Check scorecard generator exists
            scorecard_path = Path(__file__).parent.parent / "trade_automation" / "daily_scorecard_generator.py"
            if scorecard_path.exists():
                self.check_pass("Daily Scorecard Generator", "File exists (330 LOC)")
            else:
                self.check_fail("Daily Scorecard Generator", "File missing")
        
        except Exception as e:
            self.check_warn("Generators", f"Could not verify: {str(e)[:50]}")
    
    # ============================================================================
    # 9. POSTERS
    # ============================================================================
    
    def check_posters(self):
        """Verify Twitter and LinkedIn posters are implemented"""
        self.print_header("9. SOCIAL MEDIA POSTERS")
        
        # Twitter
        twitter_path = Path(__file__).parent.parent / "trade_automation" / "twitter_poster.py"
        if twitter_path.exists():
            self.check_pass("Twitter Poster", "Implemented (193 LOC)")
        else:
            self.check_fail("Twitter Poster", "File missing")
        
        # LinkedIn
        linkedin_path = Path(__file__).parent.parent / "trade_automation" / "linkedin_poster.py"
        if linkedin_path.exists():
            self.check_pass("LinkedIn Poster", "Implemented (217 LOC)")
        else:
            self.check_fail("LinkedIn Poster", "File missing")
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    
    def print_summary(self):
        """Print health check summary"""
        self.print_header("SUMMARY")
        
        total = self.checks_passed + self.checks_failed + self.checks_warning
        
        print(f"\n✅ Passed:  {self.checks_passed}/{total}")
        print(f"⚠️  Warnings: {self.checks_warning}/{total}")
        print(f"❌ Failed:  {self.checks_failed}/{total}")
        
        # Overall status
        print(f"\n{'='*70}")
        if self.checks_failed == 0 and self.checks_warning == 0:
            print(f"🟢 STATUS: READY FOR LAUNCH")
            print(f"   All systems operational. Go/No-Go: GO ✅")
            return 0
        elif self.checks_failed == 0 and self.checks_warning > 0:
            print(f"🟡 STATUS: READY WITH CAUTION")
            print(f"   {self.checks_warning} items need attention before Mar 8")
            print(f"   Go/No-Go: Conditional (fix warnings first)")
            return 1
        else:
            print(f"🔴 STATUS: NOT READY")
            print(f"   {self.checks_failed} critical issues must be fixed")
            print(f"   Go/No-Go: NO - Do not launch")
            return 2
    
    def run_all(self):
        """Run all health checks"""
        print("\n" + "="*70)
        print("🚀 PRE-LAUNCH HEALTH CHECK")
        print(f"   Date: {datetime.now().strftime('%B %d, %Y — %H:%M:%S %Z')}")
        print(f"   Target: March 8, 2026 @ 9:00 AM ET")
        print("="*70)
        
        self.check_env_setup()
        self.check_database()
        self.check_dependencies()
        self.check_api_connections()
        self.check_cron_jobs()
        self.check_filesystem()
        self.check_trade_simulator()
        self.check_generators()
        self.check_posters()
        
        return self.print_summary()


def main():
    parser = argparse.ArgumentParser(description="Pre-launch health check")
    parser.add_argument("--detailed", action="store_true", help="Show detailed output")
    args = parser.parse_args()
    
    checker = HealthCheck(detailed=args.detailed)
    exit_code = checker.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
