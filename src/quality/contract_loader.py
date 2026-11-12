"""Load simple YAML data rules for TripPilot tables."""

from pathlib import Path
from typing import Any

import yaml


def load_contract(path: str | Path) -> dict[str, Any]:
    """Read a YAML data-rules file and return its contents."""
    contract_path = Path(path)

    if not contract_path.exists():
        raise FileNotFoundError(
            f"Data-rules file not found: {contract_path}"
        )

    with contract_path.open("r", encoding="utf-8") as file:
        contract = yaml.safe_load(file)

    if not isinstance(contract, dict):
        raise TypeError(
            f"Data-rules file must contain a YAML mapping: {contract_path}"
        )

    return contract


def get_table_rules(
    contract: dict[str, Any],
    table_name: str,
) -> dict[str, Any]:
    """Return the rules for one table, such as silver_listings."""
    rules = contract.get(table_name)

    if not isinstance(rules, dict):
        raise TypeError(
            f"Missing rules for table: {table_name}"
        )

    return rules
