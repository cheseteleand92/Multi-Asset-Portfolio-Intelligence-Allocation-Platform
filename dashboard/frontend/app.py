"""Institutional Plotly Dash frontend with interactive analytics."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, dcc, html, ctx
from dash import dash_table

# --- Theme & Style Constants ---
THEME = {
    "background": "#121212",
    "paper": "#1e1e1e",
    "text": "#e0e0e0",
    "accent": "#00bcd4",  # Cyan
    "accent_secondary": "#ff4081",  # Pink
    "font": "Roboto, sans-serif",
}

GRAPH_TEMPLATE = "plotly_dark"

STYLE_CONTAINER = {
    "backgroundColor": THEME["background"],
    "color": THEME["text"],
    "fontFamily": THEME["font"],
    "minHeight": "100vh",
    "padding": "20px",
}

STYLE_CARD = {
    "backgroundColor": THEME["paper"],
    "borderRadius": "8px",
    "padding": "16px",
    "marginBottom": "20px",
    "boxShadow": "0 4px 6px rgba(0,0,0,0.3)",
}

STYLE_TAB = {
    "borderBottom": f"1px solid {THEME['paper']}",
    "padding": "12px",
    "backgroundColor": THEME["background"],
    "color": THEME["text"],
}

STYLE_TAB_SELECTED = {
    "borderTop": f"3px solid {THEME['accent']}",
    "borderBottom": f"1px solid {THEME['background']}",
    "backgroundColor": THEME["paper"],
    "color": THEME["accent"],
    "fontWeight": "bold",
    "padding": "12px",
}

# --- Helper Functions ---

def _line_figure(series: list[float], title: str, y_name: str) -> go.Figure:
    df = pd.DataFrame({"x": list(range(len(series))), y_name: series})
    fig = px.line(df, x="x", y=y_name, title=title, template=GRAPH_TEMPLATE)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def _bar_figure(data: Dict[str, float], title: str, x_label: str = "bucket", y_label: str = "value") -> go.Figure:
    df = pd.DataFrame({x_label: list(data.keys()), y_label: list(data.values())})
    fig = px.bar(df, x=x_label, y=y_label, title=title, template=GRAPH_TEMPLATE)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig.update_traces(marker_color=THEME["accent"])
    return fig

def _treemap(data: Dict[str, float], title: str) -> go.Figure:
    df = pd.DataFrame({"asset": list(data.keys()), "weight": list(data.values())})
    fig = px.treemap(df, path=["asset"], values="weight", title=title, template=GRAPH_TEMPLATE)
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
    return fig

def _heatmap(matrix: Dict[str, Dict[str, float]], title: str) -> go.Figure:
    df = pd.DataFrame(matrix)
    fig = px.imshow(
        df.values, x=df.columns, y=df.index, aspect="auto", 
        color_continuous_scale="RdBu", zmin=-1, zmax=1, template=GRAPH_TEMPLATE
    )
    fig.update_layout(title=title, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def _efficient_frontier(risk: list[float], ret: list[float], title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=risk, y=ret, mode="lines+markers", name="Efficient Frontier",
        line=dict(color=THEME["accent"], width=3)
    ))
    fig.update_layout(
        title=title, 
        xaxis_title="Volatility", yaxis_title="Expected Return", 
        template=GRAPH_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# --- Dashboard App Factory ---

def create_dashboard_app(initial_payload: Dict[str, Any], server: Any | None = None, url_base_pathname: str = "/") -> Dash:
    """Create multi-page style tabbed institutional dashboard."""
    app = Dash(__name__, server=server, url_base_pathname=url_base_pathname)  # removed prevent_initial_callbacks

    # We use a store to hold the data, initialized with payload
    # In a real app, strict separation might be needed, but this works for simpler caching
    
    app.layout = html.Div(
        style=STYLE_CONTAINER,
        children=[
            # Header
            html.Div(
                [
                    html.H1("QUANT PLATFORM // Multi-Asset Intelligence", style={"marginBottom": "0px", "color": THEME["accent"]}),
                    html.Div(
                        [
                            html.Span("LIVE", style={"backgroundColor": "red", "color": "white", "padding": "2px 6px", "borderRadius": "4px", "fontSize": "10px", "marginRight": "10px"}),
                            html.Span(f"System Time: {initial_payload.get('timestamp', 'N/A')}", id="timestamp-display", style={"fontSize": "12px", "color": "#888"}),
                        ],
                        style={"display": "flex", "alignItems": "center", "marginTop": "8px"}
                    )
                ],
                style={"marginBottom": "24px", "borderBottom": "1px solid #333", "paddingBottom": "16px"}
            ),

            # Controls
            html.Div(
                [
                    # dcc.Interval(id="interval-component", interval=60*1000, n_intervals=0), # Auto-refresh every 60s
                    html.Button("REFRESH DATA", id="refresh-btn", style={"backgroundColor": THEME["paper"], "color": THEME["accent"], "border": f"1px solid {THEME['accent']}", "padding": "8px 16px", "cursor": "pointer"}),
                ],
                style={"marginBottom": "20px", "display": "flex", "justifyContent": "flex-end"}
            ),

            dcc.Store(id="data-store", data=initial_payload),

            dcc.Tabs(
                parent_style={"backgroundColor": THEME["background"]},
                style={"backgroundColor": THEME["background"]},
                children=[
                    dcc.Tab(
                        label="PORTFOLIO OVERVIEW",
                        style=STYLE_TAB, selected_style=STYLE_TAB_SELECTED,
                        children=[
                            html.Div([
                                html.Div(dcc.Graph(id="nav-chart"), style={**STYLE_CARD, "width": "65%"}),
                                html.Div(dcc.Graph(id="allocation-treemap"), style={**STYLE_CARD, "width": "33%"}),
                            ], style={"display": "flex", "justifyContent": "space-between"}),
                            
                            html.Div([
                                html.Div(dcc.Graph(id="rolling-return-chart"), style={**STYLE_CARD, "width": "49%"}),
                                html.Div(dcc.Graph(id="risk-contrib-chart"), style={**STYLE_CARD, "width": "49%"}),
                            ], style={"display": "flex", "justifyContent": "space-between"}),
                        ],
                    ),
                    dcc.Tab(
                        label="RISK & FACTORS",
                        style=STYLE_TAB, selected_style=STYLE_TAB_SELECTED,
                        children=[
                            html.Div(dcc.Graph(id="correlation-heatmap"), style=STYLE_CARD),
                            html.Div([
                                html.Div(dcc.Graph(id="factor-risk-chart"), style={**STYLE_CARD, "width": "49%"}),
                                html.Div(dcc.Graph(id="beta-exposure-chart"), style={**STYLE_CARD, "width": "49%"}),
                            ], style={"display": "flex", "justifyContent": "space-between"}),
                            html.Div("Factor Exposures (Table)", style={"marginBottom": "10px", "fontWeight": "bold"}),
                            html.Div(id="factor-table-container", style=STYLE_CARD),
                        ],
                    ),
                    dcc.Tab(
                        label="OPTIMIZATION",
                        style=STYLE_TAB, selected_style=STYLE_TAB_SELECTED,
                        children=[
                            html.Div([
                                html.Div(dcc.Graph(id="efficient-frontier"), style={**STYLE_CARD, "width": "60%"}),
                                html.Div(dcc.Graph(id="weight-comparison"), style={**STYLE_CARD, "width": "38%"}),
                            ], style={"display": "flex", "justifyContent": "space-between"}),
                            html.Div(dcc.Graph(id="risk-budget-chart"), style=STYLE_CARD),
                        ],
                    ),
                    dcc.Tab(
                        label="MACRO & SIGNALS",
                        style=STYLE_TAB, selected_style=STYLE_TAB_SELECTED,
                        children=[
                             html.Div([
                                html.Div(dcc.Graph(id="regime-prob-chart"), style={**STYLE_CARD, "width": "49%"}),
                                html.Div(dcc.Graph(id="signal-dashboard"), style={**STYLE_CARD, "width": "49%"}),
                            ], style={"display": "flex", "justifyContent": "space-between"}),
                            html.Div([
                                html.Div(dcc.Graph(id="yield-curve"), style={**STYLE_CARD, "width": "32%"}),
                                html.Div(dcc.Graph(id="credit-spread"), style={**STYLE_CARD, "width": "32%"}),
                                html.Div(dcc.Graph(id="vix-chart"), style={**STYLE_CARD, "width": "32%"}),
                            ], style={"display": "flex", "justifyContent": "space-between"}),
                        ]
                    )
                ]
            )
        ]
    )

    # --- Callbacks ---
    
    # In a real deployed app, we would use a server-side cache.
    # Here we simulate fetching fresh data (which is just synthetic for now)
    
    @app.callback(
        Output("data-store", "data"),
        Input("refresh-btn", "n_clicks"),
        State("data-store", "data"),
    )
    def update_data(n_clicks, current_data):
        if n_clicks is None:
            return current_data
        
        # Determine how to fetch data. 
        # Since we are inside the function, we need to access the Service singleton
        try:
            from dashboard.backend.dependencies import get_data_service
            service = get_data_service()
            return service.get_payload()
        except ImportError:
            return current_data

    @app.callback(
        [
            Output("timestamp-display", "children"),
            Output("nav-chart", "figure"),
            Output("allocation-treemap", "figure"),
            Output("rolling-return-chart", "figure"),
            Output("risk-contrib-chart", "figure"),
            Output("correlation-heatmap", "figure"),
            Output("factor-risk-chart", "figure"),
            Output("beta-exposure-chart", "figure"),
            Output("factor-table-container", "children"),
            Output("efficient-frontier", "figure"),
            Output("weight-comparison", "figure"),
            Output("risk-budget-chart", "figure"),
            Output("regime-prob-chart", "figure"),
            Output("signal-dashboard", "figure"),
            Output("yield-curve", "figure"),
            Output("credit-spread", "figure"),
            Output("vix-chart", "figure"),
        ],
        Input("data-store", "data")
    )
    def update_graphs(data):
        if not data:
             return ["N/A"] + [go.Figure()] * 16

        portfolio = data["portfolio"]
        risk = data["risk"]
        factor = data["factor"]
        opt = data["optimization"]
        macro = data["macro"]
        signals = data["signals"]
        
        # Tbl
        factor_tbl = pd.DataFrame([{"factor": k, "exposure": v} for k, v in factor["factor_exposure"].items()])
        tbl_comp = dash_table.DataTable(
            data=factor_tbl.to_dict("records"), 
            columns=[{"name": c, "id": c} for c in factor_tbl.columns],
            style_header={'backgroundColor': THEME['paper'], 'color': THEME['text']},
            style_cell={'backgroundColor': THEME['background'], 'color': THEME['text']},
        )
        
        return (
            f"System Time: {data.get('timestamp')}",
            _line_figure(portfolio["nav"], "NAV Performance", "nav"),
            _treemap(portfolio["allocation"], "Current Allocation"),
            _line_figure(portfolio["rolling_return"], "Rolling Returns", "return"),
            _bar_figure(portfolio["risk_contribution"], "Risk Contribution", "asset", "risk"),
            _heatmap(risk["correlation_matrix"], "Correlation Matrix"),
            _bar_figure(factor["factor_risk_contribution"], "Factor Risk", "factor", "risk"),
            _bar_figure(risk["beta_exposure"], "Beta Exposure", "type", "beta"),
            tbl_comp,
            _efficient_frontier(opt["efficient_frontier_risk"], opt["efficient_frontier_return"], "Efficient Frontier"),
            _bar_figure(opt["weight_comparison"], "Weight vs Benchmark", "asset", "diff"),
            _bar_figure(opt["risk_budget_allocation"], "Risk Budgeting", "asset", "budget"),
            _line_figure(signals["regime_probability"], "Regime Probability", "prob"),
            _bar_figure(signals["signals"], "Signal Strength", "signal", "score"),
            _line_figure(macro["yield_curve"], "Yield Curve", "yield"),
            _line_figure(macro["credit_spread"], "Credit Spreads", "spread"),
            _line_figure(macro["volatility_index"], "VIX", "vol")
        )

    return app
