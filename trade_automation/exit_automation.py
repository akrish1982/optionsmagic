"""
Exit Automation - Monitor positions and execute exits based on rules
Runs every 5 minutes during market hours to check exit conditions
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import os

from trade_automation.config import Settings
from trade_automation.position_manager import PositionManager
from trade_automation.supabase_client import get_supabase_client
from trade_automation.notifier_telegram import TelegramNotifier
from trade_automation.opportunities import OpportunitiesFetcher
from trade_automation.tradestation import TradeStationTradingClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/exit_automation.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class ExitAutomation:
    """Monitors positions and executes exits"""
    
    def __init__(self, settings: Settings, supabase, position_mgr: PositionManager):
        self.settings = settings
        self.supabase = supabase
        self.position_mgr = position_mgr
        self.notifier = TelegramNotifier(settings) if "telegram" in settings.approval_backends else None
        self.trader = TradeStationTradingClient(settings)
        self.opportunities = OpportunitiesFetcher(settings, supabase)
    
    async def monitor_and_exit(self) -> int:
        """
        Monitor all open positions and exit those that meet criteria.
        Returns: Number of positions exited
        """
        
        logger.info("Checking open positions for exit conditions...")
        
        # Get all open positions
        open_positions = await self.position_mgr.get_open_positions()
        
        if not open_positions:
            logger.info("No open positions to monitor")
            return 0
        
        logger.info(f"Found {len(open_positions)} open positions")
        
        exits_executed = 0
        
        for position in open_positions:
            try:
                should_exit, reason = await self._evaluate_position(position)
                
                if should_exit:
                    logger.info(f"Exiting position {position['position_id']}: {reason}")
                    await self._execute_exit(position, reason)
                    exits_executed += 1
                    
                    if self.notifier:
                        self.notifier.send_message(
                            f"📊 Position {position['position_id']} exited\n"
                            f"Ticker: {position['ticker']}\n"
                            f"Reason: {reason}\n"
                            f"Status: CLOSED"
                        )
                else:
                    # Log position status for monitoring
                    pnl = position.get("unrealized_pnl", 0) or 0
                    logger.debug(f"Position {position['position_id']}: {position['ticker']} "
                                f"- Unrealized P&L: ${pnl}")
            
            except Exception as e:
                logger.error(f"Error evaluating position {position['position_id']}: {e}")
                continue
        
        if exits_executed > 0:
            logger.info(f"Exited {exits_executed} positions")
        
        return exits_executed
    
    async def _evaluate_position(self, position: Dict) -> Tuple[bool, str]:
        """
        Evaluate a single position for exit conditions.
        Returns: (should_exit, reason)
        """
        
        # Rule 1: Days to Expiry (21 DTE)
        if self._check_days_to_expiry(position):
            return True, "21 DTE reached"
        
        # Rule 2: Profit Target (50% profit)
        current_price = await self._get_current_price(position["ticker"])
        if current_price and self._check_profit_target(position, current_price):
            return True, "50% profit target reached"
        
        # Rule 3: Stop Loss (200% of credit for spreads)
        if current_price and self._check_stop_loss(position, current_price):
            return True, "Stop loss triggered"
        
        return False, None
    
    def _check_days_to_expiry(self, position: Dict) -> bool:
        """Check if position is within 21 days of expiration"""
        
        legs = position.get("legs", [])
        if not legs:
            return False
        
        # Extract expiration from first leg
        try:
            if isinstance(legs, list) and len(legs) > 0:
                leg = legs[0]
                if isinstance(leg, dict):
                    exp_str = leg.get("expiration")
                else:
                    # OptionLeg object
                    exp_str = leg.expiration
                
                if exp_str:
                    expiration = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                    days_to_exp = (expiration - datetime.utcnow()).days
                    
                    if days_to_exp <= 21:
                        logger.info(f"Position {position['position_id']}: {days_to_exp} DTE - TRIGGER EXIT")
                        return True
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Could not parse expiration for position {position['position_id']}: {e}")
        
        return False
    
    async def _get_current_price(self, ticker: str) -> float:
        """Get current price for a ticker"""
        
        try:
            # Try to get from opportunities (includes current price)
            opportunities = await self.opportunities.fetch_opportunities(
                limit=1,
                min_return_pct=0
            )
            
            for opp in opportunities:
                if opp.get("ticker") == ticker:
                    return opp.get("stock_price", 0)
            
            # Fallback: query stock_quotes
            response = (
                self.supabase.table("stock_quotes")
                .select("price")
                .eq("ticker", ticker)
                .order("quote_date", desc=True)
                .limit(1)
                .execute()
            )
            
            if response.data:
                return float(response.data[0]["price"])
        
        except Exception as e:
            logger.error(f"Failed to get price for {ticker}: {e}")
        
        return None
    
    def _check_profit_target(self, position: Dict, current_price: float) -> bool:
        """Check if position has reached 50% profit target"""
        
        entry_price = position.get("entry_price", 0)
        profit_target = position.get("profit_target", 0)
        
        if not entry_price or not profit_target:
            return False
        
        # Calculate current P&L
        current_pnl = (current_price - entry_price) * position.get("quantity", 1)
        
        # Check if we've hit 50% of max profit
        max_profit = profit_target * 2  # profit_target is 50% of max
        
        if current_pnl >= (max_profit * 0.5):
            logger.info(f"Position {position['position_id']}: "
                       f"Current P&L ${current_pnl} >= target ${profit_target}")
            return True
        
        return False
    
    def _check_stop_loss(self, position: Dict, current_price: float) -> bool:
        """Check if position has hit stop loss"""
        
        entry_price = position.get("entry_price", 0)
        stop_loss = position.get("stop_loss", 0)
        
        if not entry_price or not stop_loss:
            return False
        
        # Calculate current loss
        current_loss = abs((current_price - entry_price) * position.get("quantity", 1))
        
        # For spreads, check if loss exceeds width (stop_loss value)
        if current_loss >= stop_loss:
            logger.info(f"Position {position['position_id']}: "
                       f"Loss ${current_loss} >= stop loss ${stop_loss}")
            return True
        
        return False
    
    async def _execute_exit(self, position: Dict, exit_reason: str) -> None:
        """Execute exit for a position"""
        
        # For now, close at market (simplified)
        # In production, would use TradeStation API to close positions
        current_price = await self._get_current_price(position["ticker"])
        exit_price = current_price or position.get("entry_price", 0)
        
        # Calculate realized P&L
        entry_price = position.get("entry_price", 0)
        quantity = position.get("quantity", 1)
        realized_pnl = (exit_price - entry_price) * quantity
        
        # Close position in database
        await self.position_mgr.close_position(
            position_id=position["position_id"],
            exit_price=exit_price,
            exit_reason=exit_reason,
            realized_pnl=realized_pnl
        )
        
        logger.info(f"Position {position['position_id']} closed: "
                   f"Entry ${entry_price}, Exit ${exit_price}, P&L ${realized_pnl}")


async def run_exit_check():
    """Run the exit check once"""
    
    settings = Settings()
    
    try:
        supabase = get_supabase_client(settings)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase: {e}")
        return
    
    position_mgr = PositionManager(supabase)
    exit_automation = ExitAutomation(settings, supabase, position_mgr)
    
    try:
        exits = await exit_automation.monitor_and_exit()
        logger.info(f"Exit check completed: {exits} positions exited")
    except Exception as e:
        logger.error(f"Error in exit automation: {e}")


def main():
    """Run exit automation loop"""
    
    logger.info("Starting exit automation")
    
    # Run continuously, checking every 5 minutes
    while True:
        try:
            asyncio.run(run_exit_check())
        except KeyboardInterrupt:
            logger.info("Shutting down")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        
        # Sleep for 5 minutes (300 seconds)
        time.sleep(300)


if __name__ == "__main__":
    main()
