"""
Exit Automation - Monitor positions and execute exits based on rules
Runs every 5 minutes during market hours to check exit conditions
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

from trade_automation.config import Settings
from trade_automation.models import TradeRequest, OptionLeg
from trade_automation.position_manager import PositionManager
from trade_automation.supabase_client import get_supabase_client
from trade_automation.notifier_telegram import TelegramNotifier
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
                        entry = position.get("entry_price", 0)
                        cost = await self._get_cost_to_close(position)
                        pnl = (entry - cost) if cost is not None else 0
                        self.notifier.send_message(
                            f"📊 Position {position['position_id']} exited\n"
                            f"Ticker: {position['ticker']}\n"
                            f"Reason: {reason}\n"
                            f"P&L per contract: ${pnl:.2f}\n"
                            f"Status: CLOSED"
                        )
                else:
                    # Log position status for monitoring
                    cost = await self._get_cost_to_close(position)
                    if cost is not None:
                        entry = position.get("entry_price", 0)
                        unrealized = entry - cost
                        logger.debug(f"Position {position['position_id']}: {position['ticker']} "
                                    f"- Unrealized P&L/contract: ${unrealized:.2f}")

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

        # Rule 2 & 3 need current option pricing
        cost_to_close = await self._get_cost_to_close(position)

        if cost_to_close is not None:
            # Rule 2: Profit Target (50% of credit received)
            if self._check_profit_target(position, cost_to_close):
                return True, "50% profit target reached"

            # Rule 3: Stop Loss
            if self._check_stop_loss(position, cost_to_close):
                return True, "Stop loss triggered"

        return False, None

    def _check_days_to_expiry(self, position: Dict) -> bool:
        """Check if position is within 21 days of expiration"""

        legs = position.get("legs", [])
        if not legs:
            return False

        try:
            leg = legs[0]
            exp_str = leg.get("expiration") if isinstance(leg, dict) else leg.expiration

            if exp_str:
                expiration = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                days_to_exp = (expiration - datetime.utcnow()).days

                if days_to_exp <= 21:
                    logger.info(f"Position {position['position_id']}: {days_to_exp} DTE - TRIGGER EXIT")
                    return True
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Could not parse expiration for position {position['position_id']}: {e}")

        return False

    async def _get_cost_to_close(self, position: Dict) -> Optional[float]:
        """
        Get the current net cost to close the position using latest option quotes.
        For a credit position (CSP/VPC), this is the debit required to buy back
        the short legs minus what you'd receive selling the long legs.
        Returns per-contract cost, or None if quotes unavailable.
        """
        legs = position.get("legs", [])
        if not legs:
            return None

        total_cost = 0.0
        for leg in legs:
            contractid = leg.get("contractid") if isinstance(leg, dict) else leg.contractid
            if not contractid:
                return None

            mid_price = self._get_option_mid_price(contractid)
            if mid_price is None:
                return None

            action = (leg.get("action") if isinstance(leg, dict) else leg.action).lower()

            if action == "sell":
                # We sold this leg; closing means buying it back
                total_cost += mid_price
            elif action == "buy":
                # We bought this leg; closing means selling it
                total_cost -= mid_price

        return total_cost

    def _get_option_mid_price(self, contractid: str) -> Optional[float]:
        """Get the latest mid-price for an option contract from options_quotes."""
        try:
            response = (
                self.supabase.table("options_quotes")
                .select("bid, ask, mark")
                .eq("contractid", contractid)
                .order("quote_date", desc=True)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.warning(f"No quote found for contract {contractid}")
                return None

            quote = response.data[0]
            # Prefer mark (mid) price, fall back to (bid+ask)/2
            mark = quote.get("mark")
            if mark is not None and float(mark) > 0:
                return float(mark)

            bid = float(quote.get("bid") or 0)
            ask = float(quote.get("ask") or 0)
            if bid > 0 and ask > 0:
                return (bid + ask) / 2.0

            return None
        except Exception as e:
            logger.error(f"Failed to get quote for {contractid}: {e}")
            return None

    def _check_profit_target(self, position: Dict, cost_to_close: float) -> bool:
        """
        Check if position has reached 50% profit target.
        For credit positions: profit = entry_credit - cost_to_close
        """
        entry_price = position.get("entry_price", 0)
        profit_target = position.get("profit_target", 0)

        if not entry_price or not profit_target:
            return False

        unrealized_profit = entry_price - cost_to_close

        if unrealized_profit >= profit_target:
            logger.info(f"Position {position['position_id']}: "
                       f"Profit ${unrealized_profit:.2f} >= target ${profit_target:.2f}")
            return True

        return False

    def _check_stop_loss(self, position: Dict, cost_to_close: float) -> bool:
        """
        Check if position has hit stop loss.
        For credit positions: loss = cost_to_close - entry_credit
        """
        entry_price = position.get("entry_price", 0)
        stop_loss = position.get("stop_loss", 0)

        if not entry_price or not stop_loss:
            return False

        unrealized_loss = cost_to_close - entry_price

        if unrealized_loss >= stop_loss:
            logger.info(f"Position {position['position_id']}: "
                       f"Loss ${unrealized_loss:.2f} >= stop loss ${stop_loss:.2f}")
            return True

        return False

    def _build_closing_order(self, position: Dict) -> TradeRequest:
        """Build a TradeRequest that closes the position by reversing all legs."""
        closing_legs = []
        for leg in position.get("legs", []):
            if isinstance(leg, dict):
                action = leg.get("action", "")
                contractid = leg.get("contractid", "")
                quantity = int(leg.get("quantity", 1))
                option_type = leg.get("option_type", "put")
                strike = float(leg.get("strike", 0))
                expiration = leg.get("expiration", "")
            else:
                action = leg.action
                contractid = leg.contractid
                quantity = leg.quantity
                option_type = leg.option_type
                strike = leg.strike
                expiration = leg.expiration

            closing_action = "Buy" if action.lower() == "sell" else "Sell"
            closing_legs.append(OptionLeg(
                contractid=contractid,
                action=closing_action,
                quantity=quantity,
                option_type=option_type,
                strike=strike,
                expiration=expiration,
            ))

        return TradeRequest(
            request_id=f"close-{position['position_id']}",
            strategy_type=position.get("strategy_type", ""),
            ticker=position["ticker"],
            expiration_date=closing_legs[0].expiration if closing_legs else "",
            strike_price=closing_legs[0].strike if closing_legs else 0,
            width=None,
            net_credit=None,
            collateral=None,
            return_pct=None,
            quantity=position.get("quantity", 1),
            legs=closing_legs,
        )

    async def _execute_exit(self, position: Dict, exit_reason: str) -> None:
        """Execute exit: place closing order via TradeStation, then update DB."""

        # Place closing order
        close_request = self._build_closing_order(position)
        order_note = ""
        try:
            result = self.trader.place_order(close_request)
            if not result.get("ok") and not result.get("dry_run"):
                order_note = f" (order failed: {result})"
                logger.error(f"Closing order failed for position {position['position_id']}: {result}")
            else:
                logger.info(f"Closing order placed for position {position['position_id']}: {result}")
        except Exception as e:
            order_note = f" (order error: {e})"
            logger.error(f"Error placing closing order for position {position['position_id']}: {e}")

        # Calculate realized P&L from option premiums
        cost_to_close = await self._get_cost_to_close(position)
        entry_price = position.get("entry_price", 0)
        quantity = position.get("quantity", 1)

        if cost_to_close is not None:
            # Per-contract P&L * quantity * 100 shares per contract
            realized_pnl = (entry_price - cost_to_close) * quantity * 100
            exit_price = cost_to_close
        else:
            realized_pnl = 0
            exit_price = 0

        await self.position_mgr.close_position(
            position_id=position["position_id"],
            exit_price=exit_price,
            exit_reason=exit_reason + order_note,
            realized_pnl=realized_pnl
        )

        logger.info(f"Position {position['position_id']} closed: "
                   f"Entry credit ${entry_price}, Close cost ${exit_price}, "
                   f"Realized P&L ${realized_pnl:.2f}")


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
