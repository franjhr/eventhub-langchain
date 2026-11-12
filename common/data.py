"""Loads EventHub data: policies, events and orders."""

import json

from common.config import DATA_DIR


def load_policies() -> str:
    """Returns the text of policies.md as is."""
    return (DATA_DIR / "policies.md").read_text(encoding="utf-8")


def load_events() -> list[dict]:
    """Returns the list of events in events.json."""
    return json.loads((DATA_DIR / "events.json").read_text(encoding="utf-8"))


def load_orders() -> list[dict]:
    """Returns the list of orders in orders.json."""
    return json.loads((DATA_DIR / "orders.json").read_text(encoding="utf-8"))
