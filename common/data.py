"""Loads EventHub data: policies, events and orders.

The extra step writes reservations to a copy of the data (data/runtime/), so the loaders
take the folder as an optional argument. Steps 1 to 3 always read data/.
"""

import json
from pathlib import Path

from common.config import DATA_DIR


def load_policies() -> str:
    """Returns the text of policies.md as is."""
    return (DATA_DIR / "policies.md").read_text(encoding="utf-8")


def load_events(data_dir: Path = DATA_DIR) -> list[dict]:
    """Returns the list of events in events.json."""
    return json.loads((data_dir / "events.json").read_text(encoding="utf-8"))


def load_orders(data_dir: Path = DATA_DIR) -> list[dict]:
    """Returns the list of orders in orders.json."""
    return json.loads((data_dir / "orders.json").read_text(encoding="utf-8"))
