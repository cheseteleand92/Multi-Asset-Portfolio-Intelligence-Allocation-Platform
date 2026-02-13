
import pytest
import pandas as pd
import numpy as np
from core.risk_engine import portfolio_volatility, marginal_risk_contribution, total_risk_contribution

def test_portfolio_volatility(sample_weights, sample_covariance):
    # Manually calculate expected vol
    w = sample_weights.values
    cov = sample_covariance.values
    # Daily vol
    daily_vol = np.sqrt(w @ cov @ w)
    # Annualized vol (default 252)
    expected_vol = daily_vol * np.sqrt(252)
    
    calc_vol = portfolio_volatility(sample_weights, sample_covariance)
    assert np.isclose(calc_vol, expected_vol)

def test_portfolio_volatility_custom_annualization(sample_weights, sample_covariance):
    calc_vol = portfolio_volatility(sample_weights, sample_covariance, annualization=1)
    # Should match daily vol
    w = sample_weights.values
    cov = sample_covariance.values
    daily_vol = np.sqrt(w @ cov @ w)
    assert np.isclose(calc_vol, daily_vol)

def test_marginal_risk_contribution(sample_weights, sample_covariance):
    mrc = marginal_risk_contribution(sample_weights, sample_covariance)
    assert len(mrc) == 3
    # Property: sum(w * mrc) = portfolio_vol (daily, since mrc is based on cov directly usually?)
    # Wait, let's check implementation of mrc. 
    # mrc = (sigma @ w) / port_vol. 
    # w * mrc = w * (sigma @ w) / port_vol = (w @ sigma @ w) / port_vol = port_vol^2 / port_vol = port_vol.
    # The implementation in risk_engine uses raw cov, so it returns daily MRC.
    
    w = sample_weights
    daily_vol = np.sqrt(w.values @ sample_covariance.values @ w.values)
    
    assert np.isclose((w * mrc).sum(), daily_vol)

def test_total_risk_contribution(sample_weights, sample_covariance):
    rc = total_risk_contribution(sample_weights, sample_covariance)
    daily_vol = np.sqrt(sample_weights.values @ sample_covariance.values @ sample_weights.values)
    assert np.isclose(rc.sum(), daily_vol)
