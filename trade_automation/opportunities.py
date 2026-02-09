import hashlib
from typing import List, Optional, Dict, Any

from trade_automation.models import TradeRequest, OptionLeg
from trade_automation.supabase_client import get_supabase_client
from trade_automation.config import Settings


def _hash_id(parts: List[str]) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _format_strike(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def get_latest_option_contract(supabase, symbol: str, expiration: str, strike: float, option_type: str) -> Optional[str]:
    strike_value = round(float(strike), 2)
    response = (
        supabase.table("options_quotes")
        .select("contractid, date")
        .eq("symbol", symbol)
        .eq("expiration", expiration)
        .eq("strike", strike_value)
        .eq("type", option_type)
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0]["contractid"]
    return None


def build_trade_request(opportunity: Dict[str, Any], supabase, settings: Settings) -> Optional[TradeRequest]:
    ticker = opportunity.get("ticker")
    strategy_type = (opportunity.get("strategy_type") or "").upper()
    expiration = opportunity.get("expiration_date")
    strike_price = _format_strike(opportunity.get("strike_price"))
    width = opportunity.get("width")

    if not ticker or not strategy_type or not expiration or not strike_price:
        return None

    request_id = _hash_id([
        str(opportunity.get("opportunity_id")),
        ticker,
        strategy_type,
        str(expiration),
        f"{strike_price:.2f}",
        str(width or "")
    ])

    legs: List[OptionLeg] = []
    if strategy_type == "CSP":
        contractid = get_latest_option_contract(
            supabase, ticker, expiration, strike_price, "put"
        )
        if not contractid:
            return None
        legs.append(OptionLeg(
            contractid=contractid,
            action="Sell",
            quantity=settings.default_quantity,
            option_type="put",
            strike=strike_price,
            expiration=str(expiration),
        ))
    elif strategy_type == "VPC":
        if not width:
            return None
        short_strike = strike_price
        long_strike = strike_price - float(width)
        short_contract = get_latest_option_contract(
            supabase, ticker, expiration, short_strike, "put"
        )
        long_contract = get_latest_option_contract(
            supabase, ticker, expiration, long_strike, "put"
        )
        if not short_contract or not long_contract:
            return None
        legs.append(OptionLeg(
            contractid=short_contract,
            action="Sell",
            quantity=settings.default_quantity,
            option_type="put",
            strike=short_strike,
            expiration=str(expiration),
        ))
        legs.append(OptionLeg(
            contractid=long_contract,
            action="Buy",
            quantity=settings.default_quantity,
            option_type="put",
            strike=long_strike,
            expiration=str(expiration),
        ))
    else:
        return None

    return TradeRequest(
        request_id=request_id,
        strategy_type=strategy_type,
        ticker=ticker,
        expiration_date=str(expiration),
        strike_price=strike_price,
        width=width,
        net_credit=opportunity.get("net_credit"),
        collateral=opportunity.get("collateral"),
        return_pct=opportunity.get("return_pct"),
        quantity=settings.default_quantity,
        legs=legs,
        source_opportunity_id=opportunity.get("opportunity_id"),
    )


def fetch_opportunities(settings: Settings) -> List[Dict[str, Any]]:
    supabase = get_supabase_client(settings)
    response = (
        supabase.table(settings.opportunities_table)
        .select("*")
        .order("return_pct", desc=True)
        .limit(settings.opportunities_limit)
        .execute()
    )
    return response.data or []


def filter_opportunities(opportunities: List[Dict[str, Any]], settings: Settings) -> List[Dict[str, Any]]:
    filtered = []
    for opp in opportunities:
        return_pct = float(opp.get("return_pct") or 0)
        collateral = float(opp.get("collateral") or 0)
        strategy = (opp.get("strategy_type") or "").upper()

        if settings.strategy_types and strategy not in {s.upper() for s in settings.strategy_types}:
            continue
        if settings.min_return_pct and return_pct < settings.min_return_pct:
            continue
        if settings.max_collateral and collateral > settings.max_collateral:
            continue
        filtered.append(opp)
    return filtered
