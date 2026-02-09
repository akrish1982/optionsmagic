from trade_automation.models import TradeRequest


def format_trade_request(trade: TradeRequest) -> str:
    legs = "; ".join(
        f"{leg.action} {leg.quantity} {leg.contractid} ({leg.option_type} {leg.strike}@{leg.expiration})"
        for leg in trade.legs
    )
    return (
        f"Trade Approval Request\n"
        f"ID: {trade.request_id}\n"
        f"Strategy: {trade.strategy_type}\n"
        f"Ticker: {trade.ticker}\n"
        f"Expiration: {trade.expiration_date}\n"
        f"Strike: {trade.strike_price}\n"
        f"Return%: {trade.return_pct}\n"
        f"Collateral: {trade.collateral}\n"
        f"Legs: {legs}\n"
        f"Reply with: approve {trade.request_id} or reject {trade.request_id}"
    )
