from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class OptionLeg:
    contractid: str
    action: str  # e.g. "Sell", "Buy"
    quantity: int
    option_type: str  # "put" or "call"
    strike: float
    expiration: str


@dataclass
class TradeRequest:
    request_id: str
    strategy_type: str
    ticker: str
    expiration_date: str
    strike_price: float
    width: Optional[float]
    net_credit: Optional[float]
    collateral: Optional[float]
    return_pct: Optional[float]
    quantity: int
    legs: List[OptionLeg] = field(default_factory=list)
    source_opportunity_id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "pending"  # pending, approved, rejected, executed, failed
    notes: str = ""
