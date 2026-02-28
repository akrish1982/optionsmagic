#!/usr/bin/env python3
"""
Pre-Deployment Validation - Verify system is ready for launch
Run this before deploying to production (SIM or LIVE)
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from trade_automation.config import Settings
from trade_automation.supabase_client import get_supabase_client

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class PreDeploymentValidator:
    """Validate system readiness before deployment"""

    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_warning = 0
        load_dotenv(Path(__file__).parent.parent / ".env")

    def print_header(self, text):
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}{text:^60}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

    def check_pass(self, name, details=""):
        self.checks_passed += 1
        print(f"{GREEN}✅ PASS{RESET}: {name}")
        if details:
            print(f"   {details}")

    def check_fail(self, name, details=""):
        self.checks_failed += 1
        print(f"{RED}❌ FAIL{RESET}: {name}")
        if details:
            print(f"   {details}")

    def check_warning(self, name, details=""):
        self.checks_warning += 1
        print(f"{YELLOW}⚠️  WARN{RESET}: {name}")
        if details:
            print(f"   {details}")

    def validate_environment_variables(self):
        """Check 1: All required environment variables set"""
        self.print_header("1. ENVIRONMENT VARIABLES")

        settings = Settings()
        
        # Required for Phase 1
        required = [
            ("SUPABASE_URL", settings.supabase_url),
            ("SUPABASE_KEY", settings.supabase_key),
            ("TRADESTATION_ENV", settings.ts_env),
            ("TELEGRAM_BOT_TOKEN", settings.telegram_bot_token),
            ("TELEGRAM_CHAT_ID", settings.telegram_chat_id),
        ]
        
        for name, value in required:
            if value:
                self.check_pass(f"{name} configured")
            else:
                self.check_fail(f"{name} missing", f"Set in .env file")

        # Optional for Phase 1, required for Phase 2
        try:
            optional = [
                ("TWITTER_API_KEY", settings.twitter_api_key),
                ("TWITTER_API_SECRET", settings.twitter_api_secret),
                ("LINKEDIN_API_KEY", settings.linkedin_api_key),
            ]
            
            for name, value in optional:
                if value:
                    self.check_pass(f"{name} configured (Phase 2)")
                else:
                    self.check_warning(f"{name} not set", "Required for Phase 2 (Mar 8+)")
        except AttributeError:
            self.check_warning("Phase 2 API Keys", "Not yet configured - needed for Phase 2")

        return self.checks_failed == 0

    def validate_database_connection(self):
        """Check 2: Can we connect to database?"""
        self.print_header("2. DATABASE CONNECTIVITY")

        try:
            settings = Settings()
            supabase = get_supabase_client(settings)
            
            # Test connection
            result = supabase.table("options_opportunities").select("count", count="exact").execute()
            self.check_pass("Supabase connected", f"Found {result.count} opportunities")
            
            return True
        except Exception as e:
            self.check_fail("Supabase connection failed", str(e))
            return False

    def validate_database_schema(self):
        """Check 3: Are all required tables present?"""
        self.print_header("3. DATABASE SCHEMA")

        try:
            settings = Settings()
            supabase = get_supabase_client(settings)
            
            # Check tables
            tables = [
                ("options_opportunities", "Trade opportunities"),
                ("positions", "Position tracking"),
                ("trade_history", "Trade history"),
            ]
            
            for table_name, description in tables:
                try:
                    result = supabase.table(table_name).select("count", count="exact").limit(1).execute()
                    self.check_pass(f"Table '{table_name}'", description)
                except:
                    self.check_fail(f"Table '{table_name}' missing", f"Run: supabase db push (copy SQL from database/ddl/)")
            
            # Check views
            views = [
                ("v_daily_pnl", "Daily P&L view"),
                ("v_performance_metrics", "Performance metrics view"),
            ]
            
            for view_name, description in views:
                try:
                    result = supabase.table(view_name).select("*").limit(1).execute()
                    self.check_pass(f"View '{view_name}'", description)
                except:
                    self.check_warning(f"View '{view_name}' missing", "Run database migrations")
            
            return True
        except Exception as e:
            self.check_fail("Database schema check failed", str(e))
            return False

    def validate_code_files(self):
        """Check 4: Are all required code files present?"""
        self.print_header("4. CODE FILES")

        required_files = [
            ("trade_automation/approval_worker.py", "Trade approval & proposals"),
            ("trade_automation/position_manager.py", "Position tracking"),
            ("trade_automation/exit_automation.py", "Exit automation"),
            ("trade_automation/tradestation.py", "TradeStation API"),
            ("trade_automation/morning_brief_generator.py", "Morning brief (Phase 2)"),
            ("trade_automation/daily_scorecard_generator.py", "Daily scorecard (Phase 2)"),
            ("trade_automation/twitter_poster.py", "Twitter posting (Phase 2)"),
            ("trade_automation/linkedin_poster.py", "LinkedIn posting (Phase 2)"),
            ("trade_automation/social_media_orchestrator.py", "Social orchestrator (Phase 2)"),
            ("trade_automation/cron_tasks.py", "Cron tasks (Phase 2)"),
        ]
        
        project_root = Path(__file__).parent.parent
        
        for file_path, description in required_files:
            full_path = project_root / file_path
            if full_path.exists():
                size = full_path.stat().st_size
                self.check_pass(f"{file_path}", f"{size} bytes")
            else:
                self.check_fail(f"{file_path} missing", description)
        
        return self.checks_failed == 0

    def validate_configuration(self):
        """Check 5: Is configuration correct?"""
        self.print_header("5. CONFIGURATION")

        settings = Settings()
        
        # Check safe mode
        if settings.ts_env == "SIM" or settings.tradestation_dry_run:
            self.check_pass("Safe mode enabled", f"ENV={settings.ts_env}, DRY_RUN={settings.tradestation_dry_run}")
        else:
            self.check_warning("Safe mode disabled", "Make sure you intend to trade with real money!")

        # Check trade mode
        if settings.trade_mode in ["DRY_RUN", "SIM", "LIVE"]:
            self.check_pass(f"Trade mode set", f"Mode: {settings.trade_mode}")
        else:
            self.check_fail("Trade mode invalid", f"Must be DRY_RUN, SIM, or LIVE")

        return self.checks_failed == 0

    def validate_dependencies(self):
        """Check 6: Are Python dependencies installed?"""
        self.print_header("6. DEPENDENCIES")

        required_packages = [
            ("supabase", "Supabase client"),
            ("tweepy", "Twitter API (Phase 2)"),
            ("selenium", "Browser automation (Phase 2)"),
            ("pillow", "Image generation"),
            ("yfinance", "Market data"),
            ("dotenv", "Environment variables"),
        ]
        
        for package_name, description in required_packages:
            try:
                __import__(package_name.replace("-", "_"))
                self.check_pass(f"{package_name}", description)
            except ImportError:
                # tweepy, selenium are Phase 2, so warn instead of fail
                if package_name in ["tweepy", "selenium"]:
                    self.check_warning(f"{package_name} not installed", f"Needed for Phase 2. Install: poetry add {package_name}")
                else:
                    self.check_fail(f"{package_name} not installed", f"Install: poetry add {package_name}")

        return self.checks_failed == 0

    def validate_logs_directory(self):
        """Check 7: Logs directory ready?"""
        self.print_header("7. LOGGING")

        logs_dir = Path(__file__).parent.parent / "logs"
        
        if logs_dir.exists():
            self.check_pass("Logs directory exists", f"{logs_dir}")
        else:
            try:
                logs_dir.mkdir(exist_ok=True)
                self.check_pass("Logs directory created", f"{logs_dir}")
            except Exception as e:
                self.check_fail("Cannot create logs directory", str(e))
                return False

        return True

    def validate_telegram_connection(self):
        """Check 8: Can we send test message to Telegram?"""
        self.print_header("8. TELEGRAM BOT")

        try:
            from trade_automation.notifier_telegram import TelegramNotifier
            settings = Settings()
            notifier = TelegramNotifier(settings)
            
            # Don't actually send a message, just verify bot is initialized
            if notifier.is_configured():
                self.check_pass("Telegram bot configured", f"Ready to send notifications")
            else:
                self.check_fail("Telegram bot not configured", "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            
            return True
        except Exception as e:
            self.check_fail("Telegram bot check failed", str(e))
            return False

    def run_all_checks(self):
        """Run all validation checks"""
        self.print_header("PRE-DEPLOYMENT VALIDATION CHECKLIST")
        print(f"Timestamp: {datetime.now().isoformat()}\n")

        checks = [
            ("Environment Variables", self.validate_environment_variables),
            ("Database Connection", self.validate_database_connection),
            ("Database Schema", self.validate_database_schema),
            ("Code Files", self.validate_code_files),
            ("Configuration", self.validate_configuration),
            ("Dependencies", self.validate_dependencies),
            ("Logs Directory", self.validate_logs_directory),
            ("Telegram Bot", self.validate_telegram_connection),
        ]

        for name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                self.check_fail(f"{name} - exception", str(e))

        # Print summary
        self.print_header("VALIDATION SUMMARY")
        total = self.checks_passed + self.checks_failed + self.checks_warning
        print(f"{GREEN}✅ Passed:  {self.checks_passed}/{total}{RESET}")
        print(f"{RED}❌ Failed:  {self.checks_failed}/{total}{RESET}")
        print(f"{YELLOW}⚠️  Warnings: {self.checks_warning}/{total}{RESET}\n")

        if self.checks_failed == 0:
            print(f"{GREEN}{'='*60}{RESET}")
            print(f"{GREEN}✅ SYSTEM READY FOR DEPLOYMENT{RESET}")
            print(f"{GREEN}{'='*60}{RESET}\n")
            return True
        else:
            print(f"{RED}{'='*60}{RESET}")
            print(f"{RED}❌ FIX FAILURES BEFORE DEPLOYING{RESET}")
            print(f"{RED}{'='*60}{RESET}\n")
            return False


def main():
    validator = PreDeploymentValidator()
    success = validator.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
