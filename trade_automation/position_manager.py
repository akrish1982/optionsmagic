"""
Position Manager - Tracks open positions and exit conditions
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from supabase import Client

from trade_automation.models import TradeRequest

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages open positions and applies exit rules"""
    
    # Exit Rules
    PROFIT_TARGET_PERCENT = 50  # Close at 50% of max profit
    STOP_LOSS_PERCENT = 200     # Close at 200% of credit (spreads)
    DAYS_TO_EXPIRY_EXIT = 21    # Close 21 DTE
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    # ========================
    # CREATE & ENTRY
    # ========================
    
    async def create_position(
        self,
        request: TradeRequest,
        entry_price: float,
        quantity: int,
        execution_data: Dict
    ) -> Dict:
        """Create a new position record"""
        
        position_data = {
            "request_id": request.request_id,
            "ticker": request.ticker,
            "strategy_type": request.strategy_type,
            "status": "OPEN",
            "entry_date": datetime.utcnow().isoformat(),
            "entry_price": entry_price,
            "quantity": quantity,
            "legs": request.legs,  # Store legs as JSON
            "stop_loss": self._calculate_stop_loss(request),
            "profit_target": self._calculate_profit_target(request),
            "notes": f"Executed from request {request.request_id}"
        }
        
        # Insert into positions table
        response = self.supabase.table("positions").insert(position_data).execute()
        
        if response.data:
            position = response.data[0]
            logger.info(f"Created position {position['position_id']} for {request.ticker}")
            return position
        else:
            logger.error(f"Failed to create position for {request.request_id}")
            raise Exception(f"Failed to create position: {response}")
    
    # ========================
    # POSITION QUERIES
    # ========================
    
    async def get_open_positions(self, ticker: Optional[str] = None) -> List[Dict]:
        """Get all open positions, optionally filtered by ticker"""
        
        query = self.supabase.table("positions").select("*").eq("status", "OPEN")
        
        if ticker:
            query = query.eq("ticker", ticker)
        
        response = query.order("entry_date", desc=True).execute()
        return response.data or []
    
    async def get_position_by_request_id(self, request_id: str) -> Optional[Dict]:
        """Get position by original trade request ID"""
        
        response = (
            self.supabase.table("positions")
            .select("*")
            .eq("request_id", request_id)
            .execute()
        )
        
        return response.data[0] if response.data else None
    
    async def get_position_by_id(self, position_id: int) -> Optional[Dict]:
        """Get position by position ID"""
        
        response = (
            self.supabase.table("positions")
            .select("*")
            .eq("position_id", position_id)
            .execute()
        )
        
        return response.data[0] if response.data else None
    
    # ========================
    # EXIT CHECKS & RULES
    # ========================
    
    async def check_exit_conditions(self) -> List[Tuple[Dict, str]]:
        """
        Check all open positions for exit conditions.
        Returns: List of (position, exit_reason) tuples
        """
        
        open_positions = await self.get_open_positions()
        positions_to_close = []
        
        for position in open_positions:
            exit_reason = self._evaluate_exit_condition(position)
            if exit_reason:
                positions_to_close.append((position, exit_reason))
                logger.info(
                    f"Position {position['position_id']} ({position['ticker']}) "
                    f"triggers exit: {exit_reason}"
                )
        
        return positions_to_close
    
    def _evaluate_exit_condition(self, position: Dict) -> Optional[str]:
        """Evaluate a single position against all exit rules"""
        
        # Rule 1: Days to expiry
        if self._should_exit_by_dte(position):
            return "21dte"
        
        # Rule 2: Profit target (needs current price - we'll fetch from opportunities)
        # This requires market data, implemented in close_position with current_price
        
        # Rule 3: Stop loss (needs current price)
        # This requires market data, implemented in close_position with current_price
        
        return None
    
    def _should_exit_by_dte(self, position: Dict) -> bool:
        """Check if position should exit due to days to expiry"""
        
        legs = position.get("legs", [])
        if not legs:
            return False
        
        # Assume all legs have same expiration (they should)
        # This is a simplified check - real impl would parse leg data
        expiration_str = legs[0].get("expiration") if isinstance(legs, list) else None
        
        if not expiration_str:
            return False
        
        try:
            expiration = datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
            days_remaining = (expiration - datetime.utcnow()).days
            return days_remaining <= self.DAYS_TO_EXPIRY_EXIT
        except (ValueError, TypeError):
            return False
    
    # ========================
    # CLOSE POSITION
    # ========================
    
    async def close_position(
        self,
        position_id: int,
        exit_price: float,
        exit_reason: str,
        realized_pnl: Optional[float] = None
    ) -> Dict:
        """Close an open position"""
        
        position = await self.get_position_by_id(position_id)
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        # Calculate P&L if not provided
        if realized_pnl is None:
            entry_price = position["entry_price"]
            quantity = position["quantity"]
            realized_pnl = (exit_price - entry_price) * quantity
        
        # Calculate P&L percent
        collateral = position.get("stop_loss", 0)  # Approximate
        pnl_percent = (realized_pnl / collateral * 100) if collateral > 0 else 0
        
        # Update position
        close_data = {
            "status": "CLOSED",
            "exit_date": datetime.utcnow().isoformat(),
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "realized_pnl": realized_pnl,
            "pnl_percent": pnl_percent,
            "days_held": self._calculate_days_held(position),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        response = (
            self.supabase.table("positions")
            .update(close_data)
            .eq("position_id", position_id)
            .execute()
        )
        
        if response.data:
            logger.info(f"Closed position {position_id}: {exit_reason}, P&L: ${realized_pnl}")
            
            # Log to trade_history
            await self._log_trade_history(position, close_data)
            
            return response.data[0]
        else:
            raise Exception(f"Failed to close position: {response}")
    
    # ========================
    # TRADE HISTORY LOGGING
    # ========================
    
    async def _log_trade_history(self, position: Dict, close_data: Dict) -> None:
        """Log closed position to trade_history table"""
        
        win_loss = "WIN" if close_data["realized_pnl"] > 0 else "LOSS"
        
        history_entry = {
            "request_id": position["request_id"],
            "position_id": position["position_id"],
            "ticker": position["ticker"],
            "strategy_type": position["strategy_type"],
            "entry_date": position["entry_date"],
            "entry_price": position["entry_price"],
            "quantity": position["quantity"],
            "exit_date": close_data["exit_date"],
            "exit_price": close_data["exit_price"],
            "pnl_realized": close_data["realized_pnl"],
            "pnl_percent": close_data["pnl_percent"],
            "win_loss": win_loss,
            "status": "CLOSED",
            "executed_by": "auto",
            "closed_at": close_data["exit_date"]
        }
        
        response = self.supabase.table("trade_history").insert(history_entry).execute()
        
        if response.data:
            logger.info(f"Logged trade to history: {win_loss}")
        else:
            logger.error(f"Failed to log trade to history: {response}")
    
    # ========================
    # HELPERS
    # ========================
    
    def _calculate_stop_loss(self, request: TradeRequest) -> float:
        """Calculate stop loss level based on strategy"""
        
        if request.strategy_type == "CSP":
            # Cash-secured put: stop loss at 200% of credit received
            return (request.net_credit or 0) * 2
        elif request.strategy_type == "VPC":
            # Vertical put spread: stop loss at width of spread
            return request.width or 0
        else:
            return 0
    
    def _calculate_profit_target(self, request: TradeRequest) -> float:
        """Calculate profit target (50% of max profit)"""
        
        if request.net_credit:
            # 50% of credit received
            return request.net_credit * 0.5
        return 0
    
    def _calculate_days_held(self, position: Dict) -> int:
        """Calculate days position was held"""
        
        try:
            entry = datetime.fromisoformat(position["entry_date"].replace("Z", "+00:00"))
            exit_date = position.get("exit_date")
            if exit_date:
                exit_dt = datetime.fromisoformat(exit_date.replace("Z", "+00:00"))
            else:
                exit_dt = datetime.utcnow()
            
            return (exit_dt - entry).days
        except (ValueError, TypeError):
            return 0
    
    # ========================
    # PERFORMANCE METRICS
    # ========================
    
    async def get_performance_metrics(self) -> Dict:
        """Get overall trading performance metrics"""
        
        response = self.supabase.rpc(
            "get_performance_metrics" 
            # Uses the SQL view we created
        ).execute()
        
        # Fallback if RPC not available - query directly
        if not response.data:
            history_response = (
                self.supabase.table("trade_history")
                .select("*")
                .in_("status", ["CLOSED", "EXPIRED"])
                .execute()
            )
            
            trades = history_response.data or []
            if not trades:
                return {
                    "total_trades": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "avg_pnl": 0
                }
            
            wins = sum(1 for t in trades if t.get("win_loss") == "WIN")
            total_pnl = sum(float(t.get("pnl_realized", 0)) for t in trades)
            
            return {
                "total_trades": len(trades),
                "total_wins": wins,
                "total_losses": len(trades) - wins,
                "win_rate": (100 * wins / len(trades)) if trades else 0,
                "total_pnl": total_pnl,
                "avg_pnl": total_pnl / len(trades) if trades else 0
            }
        
        return response.data[0] if response.data else {}
    
    async def get_daily_pnl(self, date: datetime) -> Dict:
        """Get P&L summary for a specific date"""
        
        response = (
            self.supabase.table("trade_history")
            .select("*")
            .gte("entry_date", date.isoformat())
            .lt("entry_date", (date + timedelta(days=1)).isoformat())
            .in_("status", ["CLOSED", "EXPIRED"])
            .execute()
        )
        
        trades = response.data or []
        if not trades:
            return {
                "date": date.isoformat(),
                "trades": 0,
                "wins": 0,
                "win_rate": 0,
                "total_pnl": 0
            }
        
        wins = sum(1 for t in trades if t.get("win_loss") == "WIN")
        total_pnl = sum(float(t.get("pnl_realized", 0)) for t in trades)
        
        return {
            "date": date.isoformat(),
            "trades": len(trades),
            "wins": wins,
            "losses": len(trades) - wins,
            "win_rate": 100 * wins / len(trades) if trades else 0,
            "total_pnl": total_pnl,
            "avg_pnl": total_pnl / len(trades) if trades else 0
        }
