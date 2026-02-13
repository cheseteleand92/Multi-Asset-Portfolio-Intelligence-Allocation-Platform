"""Institutional Plotly Dash frontend with five interactive analytics pages."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dash_table, dcc, html


def _line_figure(series: list[float], title: str, y_name: str) -> Any:
    df = pd.DataFrame({"x": list(range(len(series))), y_name: series})
    return px.line(df, x="x", y=y_name, title=title, template="plotly_white")


def _bar_figure(data: Dict[str, float], title: str, x_label: str = "bucket", y_label: str = "value") -> Any:
    df = pd.DataFrame({x_label: list(data.keys()), y_label: list(data.values())})
    return px.bar(df, x=x_label, y=y_label, title=title, template="plotly_white")


def _treemap(data: Dict[str, float], title: str) -> Any:
    df = pd.DataFrame({"asset": list(data.keys()), "weight": list(data.values())})
    return px.treemap(df, path=["asset"], values="weight", title=title)


def _heatmap(matrix: Dict[str, Dict[str, float]], title: str) -> Any:
    df = pd.DataFrame(matrix)
    fig = px.imshow(df.values, x=df.columns, y=df.index, aspect="auto", color_continuous_scale="RdBu", zmin=-1, zmax=1)
    fig.update_layout(title=title, template="plotly_white")
    return fig


def _efficient_frontier(risk: list[float], ret: list[float], title: str) -> Any:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=risk, y=ret, mode="lines+markers", name="Efficient Frontier"))
    fig.update_layout(title=title, xaxis_title="Volatility", yaxis_title="Expected Return", template="plotly_white")
    return fig


def create_dashboard_app(api_payload: Dict[str, Any], server: Any | None = None, url_base_pathname: str = "/") -> Dash:
    """Create multi-page style tabbed institutional dashboard."""
    app = Dash(__name__, server=server, url_base_pathname=url_base_pathname)

    portfolio = api_payload["portfolio"]
    risk = api_payload["risk"]
    factor = api_payload["factor"]
    optimization = api_payload["optimization"]
    macro = api_payload["macro"]
    signals = api_payload["signals"]

    factor_tbl = pd.DataFrame([{"factor": k, "exposure": v} for k, v in factor["factor_exposure"].items()])

    app.layout = html.Div(
        [
            html.H2("Multi-Asset Portfolio Intelligence & Allocation Platform"),
            html.Div(f"Snapshot timestamp: {api_payload.get('timestamp', 'N/A')}", style={"marginBottom": "12px"}),
            dcc.Tabs(
                [
                    dcc.Tab(
                        label="1) Portfolio Overview",
                        children=[
                            dcc.Graph(figure=_line_figure(portfolio["nav"], "NAV Chart", "nav")),
                            dcc.Graph(figure=_treemap(portfolio["allocation"], "Allocation Treemap")),
                            dcc.Graph(figure=_line_figure(portfolio["rolling_return"], "Rolling Return", "rolling_return")),
                            dcc.Graph(figure=_bar_figure(portfolio["risk_contribution"], "Risk Contribution", "asset", "contribution")),
                        ],
                    ),
                    dcc.Tab(
                        label="2) Risk & Factor",
                        children=[
                            dash_table.DataTable(data=factor_tbl.to_dict("records"), columns=[{"name": c, "id": c} for c in factor_tbl.columns], page_size=10),
                            dcc.Graph(figure=_bar_figure(factor["factor_risk_contribution"], "Factor Risk Contribution", "factor", "contribution")),
                            dcc.Graph(figure=_heatmap(risk["correlation_matrix"], "Correlation Heatmap")),
                            dcc.Graph(figure=_bar_figure(risk["beta_exposure"], "Beta Exposure", "label", "beta")),
                            dcc.Graph(figure=_bar_figure(risk["duration_exposure"], "Duration Exposure", "label", "duration")),
                        ],
                    ),
                    dcc.Tab(
                        label="3) Optimization",
                        children=[
                            dcc.Graph(figure=_efficient_frontier(optimization["efficient_frontier_risk"], optimization["efficient_frontier_return"], "Efficient Frontier")),
                            dcc.Graph(figure=_bar_figure(optimization["weight_comparison"], "Weight Comparison", "asset", "delta_weight")),
                            dcc.Graph(figure=_bar_figure(optimization["risk_budget_allocation"], "Risk Budget Visualization", "asset", "weight")),
                            dcc.Graph(figure=_bar_figure(optimization["constraint_impact"], "Constraint Impact Visualization", "constraint", "value")),
                        ],
                    ),
                    dcc.Tab(
                        label="4) TAA / Regime",
                        children=[
                            dcc.Graph(figure=_line_figure(signals["regime_probability"], "Regime Probability", "probability")),
                            dcc.Graph(figure=_bar_figure(signals["signals"], "Signal Dashboard", "signal", "score")),
                            dcc.Graph(figure=_bar_figure(signals["suggested_allocation_shift"], "Suggested Allocation Shift", "asset", "delta_weight")),
                        ],
                    ),
                    dcc.Tab(
                        label="5) Macro Intelligence",
                        children=[
                            dcc.Graph(figure=_line_figure(macro["yield_curve"], "Yield Curve Chart", "yield")),
                            dcc.Graph(figure=_line_figure(macro["credit_spread"], "Credit Spread Chart", "spread")),
                            dcc.Graph(figure=_line_figure(macro["fx_index"], "FX Index", "fx")),
                            dcc.Graph(figure=_line_figure(macro["volatility_index"], "Volatility Index", "vix")),
                            dcc.Graph(figure=_bar_figure(macro["scenario_shock_result"], "Scenario Shock Simulation Result", "scenario", "pnl")),
                        ],
                    ),
                ]
            ),
        ],
        style={"padding": "16px"},
    )
    return app
