#!/usr/bin/env python3
"""
🏥 OptionsMagic Weekend Health Check
Verifies all Phase 1 & Phase 2 systems are operational before credential deployment

Usage: poetry run python scripts/weekend_health_check.py
Expected: Exit code 0 (all systems healthy)
"""

import sys
import json
import logging
import os
from pathlib import Path
from datetime import datetime

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Track health status
health_checks = {
    "passed": [],
    "warnings": [],
    "failed": [],
    "total_checks": 0,
}


def check(name: str, condition: bool, message: str = ""):
    """Record a health check result."""
    health_checks["total_checks"] += 1
    status = "✅" if condition else "❌"
    
    if condition:
        health_checks["passed"].append(name)
        logger.info(f"{status} {name}")
    else:
        health_checks["failed"].append(f"{name}: {message}")
        logger.error(f"{status} {name}: {message}")


def warn(name: str, condition: bool, message: str = ""):
    """Record a warning."""
    if not condition:
        status = "⚠️"
        health_checks["warnings"].append(f"{name}: {message}")
        logger.warning(f"{status} {name}: {message}")


def main():
    """Run all health checks."""
    logger.info("=" * 70)
    logger.info("🏥 OptionsMagic Weekend Health Check")
    logger.info("=" * 70)
    
    # ========== ENVIRONMENT CHECKS ==========
    logger.info("\n📋 Environment Configuration")
    logger.info("-" * 70)
    
    required_env_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "TRADESTATION_ACCOUNT_ID",
    ]
    
    for var in required_env_vars:
        check(
            f"ENV: {var}",
            var in os.environ,
            f"Missing environment variable {var}"
        )
    
    # ========== DIRECTORY STRUCTURE CHECKS ==========
    logger.info("\n📁 Directory Structure")
    logger.info("-" * 70)
    
    required_dirs = [
        "trade_automation",
        "scripts",
        "database",
        "database/ddl",
        "logs",
    ]
    
    for dir_path in required_dirs:
        exists = Path(dir_path).is_dir()
        check(f"Directory: {dir_path}", exists, f"Directory not found: {dir_path}")
    
    # ========== PHASE 1 MODULE CHECKS ==========
    logger.info("\n🤖 Phase 1: Trade Execution Modules")
    logger.info("-" * 70)
    
    phase1_modules = [
        "trade_automation.config",
        "trade_automation.supabase_client",
        "trade_automation.propose_trades",
        "trade_automation.approval_worker",
        "trade_automation.tradestation",
        "trade_automation.position_manager",
        "trade_automation.exit_automation",
    ]
    
    for module_name in phase1_modules:
        try:
            __import__(module_name)
            check(f"Module: {module_name}", True)
        except ImportError as e:
            check(f"Module: {module_name}", False, str(e))
    
    # ========== PHASE 2 MODULE CHECKS ==========
    logger.info("\n📢 Phase 2: Content Generation Modules")
    logger.info("-" * 70)
    
    phase2_modules = [
        "trade_automation.morning_brief_generator",
        "trade_automation.daily_scorecard_generator",
    ]
    
    for module_name in phase2_modules:
        try:
            __import__(module_name)
            check(f"Module: {module_name}", True)
        except ImportError as e:
            check(f"Module: {module_name}", False, str(e))
    
    # ========== PHASE 3 MODULE CHECKS ==========
    logger.info("\n🌐 Phase 3: Social Media Posting Modules")
    logger.info("-" * 70)
    
    phase3_modules = [
        "trade_automation.twitter_poster",
        "trade_automation.linkedin_poster",
        "trade_automation.social_media_orchestrator",
    ]
    
    for module_name in phase3_modules:
        try:
            __import__(module_name)
            check(f"Module: {module_name}", True)
        except ImportError as e:
            check(f"Module: {module_name}", False, str(e))
    
    # ========== DEPENDENCY CHECKS ==========
    logger.info("\n📦 Required Dependencies")
    logger.info("-" * 70)
    
    dependencies = [
        "pandas",
        "numpy",
        "requests",
        "tweepy",
        "PIL",  # Pillow's module name
        "supabase",
        "pydantic",
    ]
    
    dep_names = [
        "pandas",
        "numpy",
        "requests",
        "tweepy",
        "pillow",
        "supabase",
        "pydantic",
    ]
    
    for dep, display_name in zip(dependencies, dep_names):
        try:
            __import__(dep)
            check(f"Dependency: {display_name}", True)
        except ImportError:
            check(f"Dependency: {display_name}", False, "Not installed")
    
    # ========== DATABASE CONNECTION CHECK ==========
    logger.info("\n🗄️  Database Configuration")
    logger.info("-" * 70)
    
    try:
        from trade_automation.supabase_client import get_supabase_client
        from trade_automation.config import Settings
        
        settings = Settings()
        supabase = get_supabase_client(settings)
        
        # Try a simple query to verify connection
        result = supabase.table("options_opportunities").select("count", count="exact").execute()
        check(f"Database: Supabase Connection", True)
        check(f"Database: Opportunities Table (options_opportunities)", True)
    except Exception as e:
        check(f"Database: Supabase Connection", False, str(e))
    
    # ========== TELEGRAM INTEGRATION CHECK ==========
    logger.info("\n💬 Telegram Integration")
    logger.info("-" * 70)
    
    try:
        from trade_automation.notifier_telegram import TelegramNotifier
        from trade_automation.config import Settings
        
        settings = Settings()
        telegram = TelegramNotifier(settings)
        check(f"Telegram: Notifier Initialization", True)
    except Exception as e:
        check(f"Telegram: Notifier Initialization", False, str(e))
    
    # ========== TWITTER CREDENTIAL VALIDATOR ==========
    logger.info("\n🐦 Twitter Integration")
    logger.info("-" * 70)
    
    twitter_required = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
    ]
    
    all_twitter_vars = all(var in os.environ for var in twitter_required)
    warn("Twitter: All credentials present", all_twitter_vars, 
         "Credentials due Mar 7 - not required yet")
    
    try:
        from trade_automation.twitter_poster import TwitterPoster
        check(f"Twitter: Module loads", True)
    except ImportError as e:
        check(f"Twitter: Module loads", False, str(e))
    
    # ========== LINKEDIN CREDENTIAL VALIDATOR ==========
    logger.info("\n💼 LinkedIn Integration")
    logger.info("-" * 70)
    
    linkedin_required = [
        "LINKEDIN_CLIENT_ID",
        "LINKEDIN_CLIENT_SECRET",
        "LINKEDIN_ACCESS_TOKEN",
    ]
    
    all_linkedin_vars = all(var in os.environ for var in linkedin_required)
    warn("LinkedIn: All credentials present", all_linkedin_vars,
         "Credentials due Mar 7 - not required yet")
    
    try:
        from trade_automation.linkedin_poster import LinkedInPoster
        check(f"LinkedIn: Module loads", True)
    except ImportError as e:
        check(f"LinkedIn: Module loads", False, str(e))
    
    # ========== CRON CONFIGURATION CHECK ==========
    logger.info("\n⏰ Cron Job Configuration")
    logger.info("-" * 70)
    
    cron_file = Path("CRON_JOBS_CONFIG.md")
    check(f"Cron: Config document exists", cron_file.exists(),
          "CRON_JOBS_CONFIG.md not found")
    
    # ========== DATABASE SCHEMA CHECK ==========
    logger.info("\n📊 Database Schema")
    logger.info("-" * 70)
    
    schema_file = Path("database/ddl/002_positions_and_trade_history.sql")
    check(f"Schema: Trade history DDL exists", schema_file.exists(),
          "Trade history DDL not found")
    
    # ========== DOCUMENTATION CHECK ==========
    logger.info("\n📚 Documentation")
    logger.info("-" * 70)
    
    required_docs = [
        "LAUNCH_DAY_CHECKLIST.md",
        "LAUNCH_DAY_RUNBOOK_GUIDE.md",
        "PHASE_2_CREDENTIAL_SETUP.md",
    ]
    
    for doc in required_docs:
        doc_path = Path(doc)
        check(f"Documentation: {doc}", doc_path.exists(),
              f"{doc} not found")
    
    # ========== SUMMARY REPORT ==========
    logger.info("\n" + "=" * 70)
    logger.info("📊 HEALTH CHECK SUMMARY")
    logger.info("=" * 70)
    
    passed = len(health_checks["passed"])
    failed = len(health_checks["failed"])
    warnings = len(health_checks["warnings"])
    total = health_checks["total_checks"]
    
    logger.info(f"✅ Passed:  {passed}/{total}")
    logger.info(f"❌ Failed:  {failed}/{total}")
    logger.info(f"⚠️  Warnings: {warnings}")
    
    if failed > 0:
        logger.error("\n❌ FAILED CHECKS:")
        for failure in health_checks["failed"]:
            logger.error(f"  - {failure}")
    
    if warnings > 0:
        logger.warning("\n⚠️  WARNINGS:")
        for warning in health_checks["warnings"]:
            logger.warning(f"  - {warning}")
    
    # ========== EXIT CODE ==========
    logger.info("\n" + "=" * 70)
    
    if failed == 0:
        logger.info("✅ ALL HEALTH CHECKS PASSED - SYSTEM READY FOR DEPLOYMENT")
        logger.info("=" * 70)
        return 0
    else:
        logger.error("❌ HEALTH CHECK FAILED - FIX ISSUES BEFORE DEPLOYMENT")
        logger.info("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
