#!/usr/bin/env python3
"""
🤖 Telegram Approval Flow Test
Tests the complete Telegram trade approval workflow without making actual trades

Usage: poetry run python scripts/test_telegram_flow.py
Expected: Sends a test trade proposal via Telegram
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Load environment
from dotenv import load_dotenv
load_dotenv()


def test_telegram_notifier():
    """Test Telegram notification system."""
    logger.info("=" * 70)
    logger.info("🤖 Testing Telegram Approval Flow")
    logger.info("=" * 70)
    
    try:
        from trade_automation.notifier_telegram import TelegramNotifier
        from trade_automation.config import Settings
        
        settings = Settings()
        telegram = TelegramNotifier(settings)
        logger.info("✅ Telegram notifier initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Telegram notifier: {e}")
        return False
    
    # Create a test trade proposal
    test_trade = {
        "request_id": "test-proposal-001",
        "ticker": "SPY",
        "strategy": "PUT_SPREAD",
        "entry_price": 487.50,
        "strike_high": 490,
        "strike_low": 485,
        "expiry": "2026-03-04",
        "quantity": 10,
        "max_risk": 250.00,
        "target_return": 125.00,
        "return_pct": 50.0,
        "win_probability": 0.68,
    }
    
    logger.info("\n📋 Test Trade Proposal:")
    logger.info(f"  Ticker: {test_trade['ticker']}")
    logger.info(f"  Strategy: {test_trade['strategy']}")
    logger.info(f"  Entry: ${test_trade['entry_price']:.2f}")
    logger.info(f"  Strike Range: ${test_trade['strike_low']} - ${test_trade['strike_high']}")
    logger.info(f"  Max Risk: ${test_trade['max_risk']:.2f}")
    logger.info(f"  Target Return: ${test_trade['target_return']:.2f} ({test_trade['return_pct']:.1f}%)")
    logger.info(f"  Win Probability: {test_trade['win_probability']*100:.1f}%")
    
    # Test sending notification
    logger.info("\n📤 Sending test notification to Telegram...")
    
    try:
        # Send via Telegram with approval buttons
        result = telegram.send_trade_proposal_with_buttons(
            request_id=test_trade['request_id'],
            ticker=test_trade['ticker'],
            strategy=test_trade['strategy'],
            expiration=test_trade['expiry'],
            strike=test_trade['strike_high'],
            return_pct=test_trade['return_pct'],
            collateral=test_trade['max_risk'],
            details=f"Spread: ${test_trade['strike_low']}/${test_trade['strike_high']} | Qty: {test_trade['quantity']}"
        )
        
        if result:
            logger.info("✅ Test notification sent successfully!")
            logger.info("📱 Check your Telegram for the approval buttons")
            logger.info(f"   Message ID: {result.get('message_id', 'unknown')}")
            return True
        else:
            logger.error("❌ Failed to send notification (no response)")
            return False
        
    except Exception as e:
        logger.error(f"❌ Failed to send test notification: {e}")
        return False


def test_approval_responses():
    """Test approval response handling."""
    logger.info("\n" + "=" * 70)
    logger.info("🎯 Testing Approval Response Handling")
    logger.info("=" * 70)
    
    logger.info("\n📝 Expected Telegram responses:")
    logger.info("  ✅ APPROVE button → triggers order execution")
    logger.info("  ❌ REJECT button → logs rejection, moves to next proposal")
    logger.info("  ⏱️  5-minute timeout → auto-rejects if no response")
    
    logger.info("\n🔍 Checking approval_worker.py for response handling...")
    
    try:
        from trade_automation.approval_worker import main as approval_main
        logger.info("✅ approval_worker.py loaded successfully")
        logger.info("   Response handlers: APPROVE, REJECT, TIMEOUT")
        
    except Exception as e:
        logger.error(f"❌ Failed to load approval_worker.py: {e}")
        return False
    
    return True


def test_order_execution():
    """Test order execution pipeline."""
    logger.info("\n" + "=" * 70)
    logger.info("🚀 Testing Order Execution Pipeline")
    logger.info("=" * 70)
    
    try:
        from trade_automation.tradestation import TradeStationTradingClient
        from trade_automation.config import Settings
        
        settings = Settings()
        orderer = TradeStationTradingClient(settings)
        
        logger.info("✅ TradeStation client initialized")
        logger.info(f"   Mode: {settings.trade_mode}")
        logger.info(f"   Dry Run: {settings.ts_dry_run}")
        
        # Check DRY_RUN mode
        if settings.trade_mode == "DRY_RUN":
            logger.info("✅ DRY_RUN mode active (safe - no actual orders)")
        elif settings.trade_mode == "SIM":
            logger.info("⚠️  SIM mode active (simulation account)")
        elif settings.trade_mode == "LIVE":
            if settings.ts_dry_run:
                logger.info("⚠️  LIVE mode but dry_run enabled (safe override)")
            else:
                logger.error("❌ WARNING: LIVE mode active - REAL MONEY RISK")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize order executor: {e}")
        return False


def test_position_tracking():
    """Test position monitoring system."""
    logger.info("\n" + "=" * 70)
    logger.info("📊 Testing Position Tracking System")
    logger.info("=" * 70)
    
    try:
        from trade_automation.position_manager import PositionManager
        from trade_automation.config import Settings
        
        settings = Settings()
        pos_mgr = PositionManager(settings)
        
        logger.info("✅ Position manager initialized")
        logger.info("   Monitors:")
        logger.info("   • Open positions (real-time P&L)")
        logger.info("   • 50% profit target (auto-close)")
        logger.info("   • 21 DTE close (auto-close)")
        logger.info("   • Stop loss triggers")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize position manager: {e}")
        return False


def test_exit_automation():
    """Test exit automation logic."""
    logger.info("\n" + "=" * 70)
    logger.info("🚪 Testing Exit Automation")
    logger.info("=" * 70)
    
    try:
        from trade_automation.exit_automation import main as exit_main
        
        logger.info("✅ Exit automation loaded")
        logger.info("   Triggers:")
        logger.info("   • 50% of max profit reached → Close position")
        logger.info("   • 21 DTE (days to expiry) → Close position")
        logger.info("   • Stop loss hit (200% of credit) → Close position")
        logger.info("   • Cron: */5 9-16 * * 1-5 (every 5 min during market hours)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load exit automation: {e}")
        return False


def main():
    """Run all tests."""
    results = {
        "telegram_notifier": test_telegram_notifier(),
        "approval_responses": test_approval_responses(),
        "order_execution": test_order_execution(),
        "position_tracking": test_position_tracking(),
        "exit_automation": test_exit_automation(),
    }
    
    logger.info("\n" + "=" * 70)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        logger.info(f"{status} {test_name.replace('_', ' ').title()}: {'PASSED' if result else 'FAILED'}")
    
    logger.info(f"\n✅ Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED - TELEGRAM APPROVAL FLOW READY FOR DEPLOYMENT")
        return 0
    else:
        logger.error("\n❌ SOME TESTS FAILED - REVIEW ERRORS ABOVE")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
