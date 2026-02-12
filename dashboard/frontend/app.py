"""Plotly Dash institutional-style dashboard integrated with FastAPI."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
from dash import Dash, dash_table, dcc, html


def _line_figure(series: list[float], title: str, y_name: str) -> Any:
    df = pd.DataFrame({"x": list(range(len(series))), y_name: series})
    return px.line(df, x="x", y=y_name, title=title)


def _bar_figure(data: Dict[str, float], title: str, x_label: str = "bucket", y_label: str = "value") -> Any:
    df = pd.DataFrame({x_label: list(data.keys()), y_label: list(data.values())})
    return px.bar(df, x=x_label, y=y_label, title=title)


def create_dashboard_app(api_payload: Dict[str, Any], server: Any | None = None, url_base_pathname: str = "/") -> Dash:
    """Create institutional multi-panel Dash app.

    Args:
        api_payload: dictionary with sections matching backend payload keys.
        server: optional Flask server (used when embedding into FastAPI).
        url_base_pathname: Dash base path.
    """
    app = Dash(__name__, server=server, url_base_pathname=url_base_pathname)

    overview = api_payload["overview"]
    risk = api_payload["risk_factor"]
    optimizer = api_payload["optimization"]
    regime = api_payload["regime_taa"]
    macro = api_payload["macro"]

    factor_tbl = pd.DataFrame(
        [{"factor": k, "exposure": v} for k, v in risk["factor_exposure"].items()]
    )

    app.layout = html.Div(
        [
            html.H2("Institutional Multi-Asset Portfolio Intelligence Platform"),
            dcc.Tabs(
                [
                    dcc.Tab(
                        label="Portfolio Overview",
                        children=[
                            dcc.Graph(figure=_line_figure(overview["nav"], "NAV", "nav")),
                            dcc.Graph(figure=_bar_figure(overview["allocation"], "Allocation Treemap Proxy", "asset", "weight")),
                            dcc.Graph(figure=_bar_figure(overview["pnl_breakdown"], "PnL Breakdown", "bucket", "pnl")),
                            dcc.Graph(figure=_line_figure(overview["rolling_return"], "Rolling Return", "rolling_return")),
                        ],
                    ),
                    dcc.Tab(
                        label="Risk & Factor",
                        children=[
                            dash_table.DataTable(
                                data=factor_tbl.to_dict("records"),
                                columns=[{"name": c, "id": c} for c in factor_tbl.columns],
                            ),
                            dcc.Graph(figure=_bar_figure(risk["factor_risk_contribution"], "Factor Risk Contribution", "factor", "contribution")),
                            dcc.Graph(figure=_bar_figure(risk["beta_exposure"], "Beta Exposure", "bucket", "beta")),
                            dcc.Graph(figure=_bar_figure(risk["duration_exposure"], "Duration Exposure", "bucket", "duration")),
                        ],
                    ),
                    dcc.Tab(
                        label="Optimization",
                        children=[
                            dcc.Graph(figure=_line_figure(optimizer["efficient_frontier"], "Efficient Frontier Proxy", "return")),
                            dcc.Graph(figure=_bar_figure(optimizer["risk_budget_allocation"], "Risk Budget Allocation", "asset", "weight")),
                            dcc.Graph(figure=_bar_figure(optimizer["weight_comparison"], "Weight Comparison", "asset", "delta_weight")),
                        ],
                    ),
                    dcc.Tab(
                        label="Regime & TAA",
                        children=[
                            dcc.Graph(figure=_line_figure(regime["regime_probability"], "Regime Probability", "probability")),
                            dcc.Graph(figure=_bar_figure(regime["signals"], "Signal Dashboard", "signal", "score")),
                            dcc.Graph(figure=_bar_figure(regime["suggested_shift"], "Suggested Allocation Shift", "asset", "delta_weight")),
                        ],
                    ),
                    dcc.Tab(
                        label="Macro Intelligence",
                        children=[
                            dcc.Graph(figure=_line_figure(macro["yield_curve"], "Yield Curve", "yield")),
                            dcc.Graph(figure=_line_figure(macro["fx_dashboard"], "FX Dashboard", "value")),
                            dcc.Graph(figure=_line_figure(macro["credit_spread"], "Credit Spread", "spread")),
                            dcc.Graph(figure=_line_figure(macro["volatility_index"], "Volatility Index", "vix")),
                        ],
                    ),
                ]
            ),
        ]
    )

    return app
