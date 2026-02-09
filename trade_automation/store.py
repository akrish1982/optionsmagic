import json
import os
from typing import Dict, Any

STATE_PATH = os.environ.get("TRADE_AUTOMATION_STATE", "trade_automation/state.json")


def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_PATH):
        return {"requests": {}, "telegram": {"last_update_id": 0}, "discord": {"last_message_id": ""}}
    with open(STATE_PATH, "r") as f:
        return json.load(f)


def save_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def upsert_request(state: Dict[str, Any], request_dict: Dict[str, Any]) -> None:
    state.setdefault("requests", {})[request_dict["request_id"]] = request_dict


def update_request_status(state: Dict[str, Any], request_id: str, status: str, notes: str = "") -> None:
    req = state.setdefault("requests", {}).get(request_id)
    if not req:
        return
    req["status"] = status
    if notes:
        req["notes"] = notes
