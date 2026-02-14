"""Analytics service — thin wrapper over core/ engines.

Adapts core/risk_engine.py actual API:
  - portfolio_volatility(weights: pd.Series, cov: pd.DataFrame) -> annualised float
  - total_risk_contribution(weights: pd.Series, cov: pd.DataFrame) -> pd.Series
  - historical_var/historical_es(returns: pd.Series, alpha) -> float
  - max_drawdown(returns: pd.Series) -> float
"""
from __future__ import annotations
from datetime import date
import numpy as np
import pandas as pd
from core.risk_engine import (
    portfolio_volatility,
    historical_var,
    historical_es,
    max_drawdown,
    total_risk_contribution,
)


DEFAULT_MONITORING_CONFIG = {
    "lookback_days": 252,
    "return_frequency": "daily",
    "confidence_level": 0.95,
    "annualization": None,
    "risk_free_rate": 0.0,
    "as_of_date": None,
}


def _normalize_config(config: dict | None) -> dict:
    payload = {**DEFAULT_MONITORING_CONFIG, **(config or {})}

    lookback = int(payload["lookback_days"])
    lookback = max(21, min(lookback, 5000))

    freq = str(payload["return_frequency"]).lower().strip()
    if freq not in {"daily", "weekly"}:
        freq = "daily"

    confidence = float(payload["confidence_level"])
    confidence = max(0.80, min(confidence, 0.995))

    annualization = payload["annualization"]
    if annualization is None:
        annualization = 252 if freq == "daily" else 52
    annualization = max(1, int(annualization))

    risk_free_rate = float(payload["risk_free_rate"])

    as_of_raw = payload.get("as_of_date")
    as_of: date | None = None
    if as_of_raw:
        as_of = pd.Timestamp(as_of_raw).date()

    return {
        "lookback_days": lookback,
        "return_frequency": freq,
        "confidence_level": confidence,
        "annualization": annualization,
        "risk_free_rate": risk_free_rate,
        "as_of_date": as_of.isoformat() if as_of else None,
    }


def _prepare_returns(returns: pd.DataFrame, config_used: dict) -> tuple[pd.DataFrame, list[str], dict]:
    warnings: list[str] = []
    prepared = returns.copy()

    as_of_date = config_used.get("as_of_date")
    if as_of_date:
        as_of_ts = pd.Timestamp(as_of_date)
        prepared = prepared[prepared.index <= as_of_ts]
        if prepared.empty:
            warnings.append("No observations found at or before selected as_of_date.")

    if not prepared.empty and config_used["return_frequency"] == "weekly":
        prepared = (1 + prepared).resample("W-FRI").prod() - 1
        prepared = prepared.dropna(how="any")
        if prepared.empty:
            warnings.append("Insufficient data after weekly resampling.")

    requested_lookback = config_used["lookback_days"]
    if len(prepared) < requested_lookback:
        warnings.append(
            f"Requested lookback {requested_lookback} exceeds available observations {len(prepared)}. "
            "Using full available history."
        )
    lookback = min(requested_lookback, len(prepared))
    if lookback > 0:
        prepared = prepared.tail(lookback)

    data_range = {
        "start": prepared.index.min().date().isoformat() if len(prepared) else None,
        "end": prepared.index.max().date().isoformat() if len(prepared) else None,
        "observations": int(len(prepared)),
    }

    return prepared, warnings, data_range


def _compute_risk_explainability(
    returns: pd.DataFrame,
    w_series: pd.Series,
    annualization: int,
    trc: pd.Series,
) -> dict:
    n_assets = len(w_series)
    if n_assets == 0 or returns.empty:
        return {}

    eq_weights = pd.Series(1.0 / n_assets, index=w_series.index)
    cov_curr = returns[w_series.index].cov()
    vol_current = float(portfolio_volatility(w_series, cov_curr, annualization=annualization))
    vol_eq_current = float(portfolio_volatility(eq_weights, cov_curr, annualization=annualization))

    split = len(returns) // 2
    if split < 20:
        cov_prev = cov_curr
    else:
        cov_prev = returns[w_series.index].iloc[:split].cov()

    vol_eq_prev = float(portfolio_volatility(eq_weights, cov_prev, annualization=annualization))

    total_delta = vol_current - vol_eq_prev
    weight_effect = vol_current - vol_eq_current
    market_effect = vol_eq_current - vol_eq_prev
    interaction = total_delta - weight_effect - market_effect

    top_contributors = [
        {"ticker": t, "trc": float(v)}
        for t, v in trc.sort_values(ascending=False).head(3).items()
    ]

    return {
        "baseline": "equal_weight_previous_regime",
        "total_delta_volatility": total_delta,
        "weight_effect": weight_effect,
        "market_effect": market_effect,
        "interaction_effect": interaction,
        "top_contributors": top_contributors,
    }


def compute_risk(returns: pd.DataFrame, weights: dict[str, float], config: dict | None = None) -> dict:
    """Compute portfolio risk metrics from asset returns and weights."""
    if returns.empty or not weights:
        return {}

    config_used = _normalize_config(config)
    prepared_returns, warnings, data_range = _prepare_returns(returns, config_used)

    tickers = [t for t in weights if t in returns.columns]
    if not tickers:
        return {}

    rets_aligned = prepared_returns[tickers].dropna()
    if rets_aligned.empty:
        return {
            "config_used": config_used,
            "data_range": data_range,
            "warnings": warnings + ["No aligned return observations after filtering."],
        }

    w_raw = np.array([weights[t] for t in tickers])
    w_norm = w_raw / w_raw.sum()
    w_series = pd.Series(w_norm, index=tickers)
    cov = rets_aligned.cov()

    port_returns = rets_aligned @ w_series
    trc = total_risk_contribution(w_series, cov)

    confidence = config_used["confidence_level"]
    annualization = config_used["annualization"]
    rf = config_used["risk_free_rate"]

    return {
        "volatility": float(portfolio_volatility(w_series, cov, annualization=annualization)),
        "var": float(historical_var(port_returns, alpha=confidence)),
        "es": float(historical_es(port_returns, alpha=confidence)),
        "var_95": float(historical_var(port_returns, alpha=0.95)),
        "es_95": float(historical_es(port_returns, alpha=0.95)),
        "max_drawdown": float(max_drawdown(port_returns)),
        "trc": {t: float(v) for t, v in trc.items()},
        "correlation": {
            t: {t2: float(rets_aligned.corr().loc[t, t2]) for t2 in tickers}
            for t in tickers
        },
        "config_used": config_used,
        "data_range": data_range,
        "warnings": warnings,
        "risk_explainability": _compute_risk_explainability(rets_aligned, w_series, annualization, trc),
        "metrics_meta": {
            "confidence_level": confidence,
            "risk_free_rate": rf,
        },
    }


def compute_nav(returns: pd.DataFrame, weights: dict[str, float], config: dict | None = None) -> dict:
    """Compute NAV series and performance metrics."""
    if returns.empty or not weights:
        return {}

    config_used = _normalize_config(config)
    prepared_returns, warnings, data_range = _prepare_returns(returns, config_used)

    tickers = [t for t in weights if t in returns.columns]
    if not tickers:
        return {}
    if prepared_returns.empty:
        return {
            "config_used": config_used,
            "data_range": data_range,
            "warnings": warnings + ["No return observations available with selected parameters."],
        }

    w_raw = np.array([weights[t] for t in tickers])
    w_norm = w_raw / w_raw.sum()
    w_series = pd.Series(w_norm, index=tickers)
    port_returns = prepared_returns[tickers].dropna() @ w_series
    if port_returns.empty:
        return {
            "config_used": config_used,
            "data_range": data_range,
            "warnings": warnings + ["No aligned return observations after filtering."],
        }

    annualization = config_used["annualization"]
    rf = config_used["risk_free_rate"]
    excess_mean = (port_returns.mean() * annualization) - rf
    annualized_vol = port_returns.std() * np.sqrt(annualization)
    sharpe = float(excess_mean / annualized_vol) if annualized_vol > 0 else 0.0

    nav = (1 + port_returns).cumprod()
    asset_nav_map: dict[str, dict[str, float]] = {}
    for t in tickers:
        series = (1 + prepared_returns[t].dropna()).cumprod()
        asset_nav_map[t] = {d.isoformat(): float(v) for d, v in series.items()}

    return {
        "nav": {d.isoformat(): float(v) for d, v in nav.items()},
        "asset_nav": asset_nav_map,
        "total_return": float(nav.iloc[-1] - 1) if len(nav) else 0.0,
        "sharpe": sharpe,
        "config_used": config_used,
        "data_range": data_range,
        "warnings": warnings,
        "metrics_meta": {
            "risk_free_rate": rf,
        },
    }
