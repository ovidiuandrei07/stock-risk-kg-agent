import numpy as np
import pandas as pd
import pytest

from src.risk.features import annualized_volatility, beta, max_drawdown, sharpe_ratio
from src.risk.risk_score import classify_risk_level, compute_composite_score

RNG = np.random.default_rng(42)


def _returns(n=252, scale=0.01):
    return pd.Series(RNG.normal(0, scale, n))


def test_annualized_volatility_scales_with_daily_std():
    calm = _returns(scale=0.005)
    wild = _returns(scale=0.05)
    assert annualized_volatility(wild) > annualized_volatility(calm)


def test_beta_of_market_with_itself_is_one():
    market = _returns()
    assert beta(market, market) == pytest.approx(1.0, rel=1e-6)


def test_beta_handles_no_overlap():
    a = pd.Series([0.01, 0.02], index=[0, 1])
    b = pd.Series([0.01], index=[5])
    assert np.isnan(beta(a, b))


def test_max_drawdown_is_negative_and_reflects_the_worst_decline():
    returns = pd.Series([0.1, -0.3, 0.05, -0.1])
    dd = max_drawdown(returns)
    assert -0.4 < dd < 0


def test_max_drawdown_zero_when_returns_always_positive():
    returns = pd.Series([0.01, 0.02, 0.03])
    assert max_drawdown(returns) == pytest.approx(0.0, abs=1e-9)


def test_sharpe_ratio_prefers_positive_low_variance_returns():
    steady_gain = pd.Series([0.001] * 100)
    noisy_flat = pd.Series(RNG.normal(0, 0.02, 100))
    assert sharpe_ratio(steady_gain) > sharpe_ratio(noisy_flat)


def test_classify_risk_level_thresholds():
    assert classify_risk_level(10) == "scazut"
    assert classify_risk_level(33) == "mediu"
    assert classify_risk_level(66) == "ridicat"
    assert classify_risk_level(99) == "ridicat"


def test_compute_composite_score_ranks_higher_volatility_as_more_risky():
    features = pd.DataFrame(
        {
            "volatility": [0.1, 0.5, 0.9],
            "beta": [0.5, 1.0, 1.5],
            "max_drawdown": [-0.05, -0.2, -0.4],
            "sharpe": [1.0, 0.5, -0.2],
        },
        index=["LOW", "MID", "HIGH"],
    )
    scores = compute_composite_score(features)
    assert scores["LOW"] < scores["MID"] < scores["HIGH"]
