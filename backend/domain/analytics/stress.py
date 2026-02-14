"""Built-in stress test scenarios."""
from __future__ import annotations

SCENARIOS: dict[str, dict[str, float]] = {
    "2008_gfc": {
        "description": "2008 Global Financial Crisis",
        "Equity": -0.50,
        "FixedIncome": 0.05,
        "Commodity": -0.30,
        "FX": -0.10,
        "Cash": 0.01,
    },
    "2020_covid": {
        "description": "2020 COVID Crash (Feb-Mar)",
        "Equity": -0.34,
        "FixedIncome": 0.08,
        "Commodity": -0.25,
        "FX": -0.05,
        "Cash": 0.01,
    },
    "2022_rate_shock": {
        "description": "2022 Rate Hike Cycle",
        "Equity": -0.20,
        "FixedIncome": -0.15,
        "Commodity": 0.20,
        "FX": 0.05,
        "Cash": 0.03,
    },
}


def run_scenario(
    positions: list,  # list of Position ORM objects
    scenario: dict[str, float],
) -> dict:
    total_value = sum(p.quantity * p.cost_price for p in positions)
    pnl = 0.0
    breakdown = {}
    for pos in positions:
        asset_class = pos.asset_class
        shock = scenario.get(asset_class, scenario.get("Equity", -0.20))
        pos_value = pos.quantity * pos.cost_price
        pos_pnl = pos_value * shock
        pnl += pos_pnl
        breakdown[pos.ticker] = {
            "shock_pct": shock,
            "pnl": round(pos_pnl, 2),
            "weight": round(pos_value / total_value, 4) if total_value else 0,
        }
    return {
        "total_pnl": round(pnl, 2),
        "pnl_pct": round(pnl / total_value, 4) if total_value else 0,
        "breakdown": breakdown,
    }
