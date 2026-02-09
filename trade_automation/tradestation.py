import json
import logging
from typing import Dict, Any, List

import requests

from trade_automation.config import Settings
from trade_automation.models import TradeRequest, OptionLeg

logger = logging.getLogger(__name__)

SIGNIN_URL = "https://signin.tradestation.com/oauth/token"


class TradeStationTradingClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.access_token = None

    def refresh_access_token(self) -> bool:
        if not self.settings.ts_refresh_token:
            logger.error("No TRADESTATION_REFRESH_TOKEN set")
            return False

        response = requests.post(
            SIGNIN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "client_id": self.settings.ts_client_id,
                "client_secret": self.settings.ts_client_secret,
                "refresh_token": self.settings.ts_refresh_token,
            },
            timeout=20,
        )

        if response.ok:
            data = response.json()
            self.access_token = data["access_token"]
            return True

        logger.error("Token refresh failed: %s", response.text[:500])
        return False

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    def _request(self, method: str, url: str, **kwargs):
        if not self.access_token:
            if not self.refresh_access_token():
                raise RuntimeError("TradeStation auth failed")

        response = requests.request(method, url, headers=self._headers(), **kwargs)
        if response.status_code == 401:
            logger.warning("Access token expired, refreshing...")
            if not self.refresh_access_token():
                raise RuntimeError("TradeStation auth failed: refresh token rejected")
            response = requests.request(method, url, headers=self._headers(), **kwargs)
        return response

    def _build_leg(self, leg: OptionLeg) -> Dict[str, Any]:
        return {
            "Symbol": leg.contractid,
            "Quantity": str(leg.quantity),
            "TradeAction": leg.action.upper(),
            "AssetType": "Option",
        }

    def build_order_payload(self, trade: TradeRequest) -> Dict[str, Any]:
        if not self.settings.ts_account_id:
            raise ValueError("TRADESTATION_ACCOUNT_ID must be set")

        order_type = self.settings.ts_order_type
        time_in_force = {"Duration": self.settings.ts_time_in_force}

        if len(trade.legs) == 1:
            leg = trade.legs[0]
            payload = {
                "AccountID": self.settings.ts_account_id,
                "Symbol": leg.contractid,
                "Quantity": str(leg.quantity),
                "OrderType": order_type,
                "TradeAction": leg.action.upper(),
                "TimeInForce": time_in_force,
                "Route": "Intelligent",
            }
        else:
            payload = {
                "AccountID": self.settings.ts_account_id,
                "OrderType": order_type,
                "TimeInForce": time_in_force,
                "Legs": [self._build_leg(leg) for leg in trade.legs],
            }

        if self.settings.ts_limit_price:
            payload["LimitPrice"] = str(self.settings.ts_limit_price)

        return payload

    def place_order(self, trade: TradeRequest) -> Dict[str, Any]:
        payload = self.build_order_payload(trade)
        if self.settings.ts_dry_run:
            logger.info("DRY RUN: would place order %s", json.dumps(payload))
            return {"dry_run": True, "payload": payload}

        url = self.settings.ts_order_endpoint()
        response = self._request("POST", url, json=payload, timeout=20)
        if not response.ok:
            logger.error("Order failed: %s", response.text[:500])
            return {"ok": False, "status": response.status_code, "body": response.text}

        return {"ok": True, "status": response.status_code, "body": response.json()}
