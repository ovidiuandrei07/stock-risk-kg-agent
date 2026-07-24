"""Risk features derived from a return series. Pure pandas/numpy — no Neo4j here,
so this module is easy to unit test (see tests/test_risk_score.py).
"""
import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def annualized_volatility(returns: pd.Series) -> float:
    """Std dev of daily returns, annualized by sqrt(252)."""
    return float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def beta(stock_returns: pd.Series, market_returns: pd.Series) -> float:
    """Covariance(stock, market) / Variance(market) over the overlapping dates."""
    aligned = pd.concat([stock_returns, market_returns], axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return float("nan")
    stock_col, market_col = aligned.columns
    covariance = aligned[stock_col].cov(aligned[market_col])
    market_variance = aligned[market_col].var()
    if market_variance == 0:
        return float("nan")
    return float(covariance / market_variance)


def max_drawdown(returns: pd.Series) -> float:
    """Largest peak-to-trough decline of the cumulative return curve, as a negative fraction."""
    cumulative = (1 + returns.fillna(0)).cumprod()
    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1
    return float(drawdown.min())


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Annualized Sharpe ratio using a constant daily risk-free rate."""
    excess = returns - risk_free_rate / TRADING_DAYS_PER_YEAR
    std = excess.std()
    if std == 0 or np.isnan(std):
        return float("nan")
    return float(excess.mean() / std * np.sqrt(TRADING_DAYS_PER_YEAR))


def compute_features(stock_returns: pd.Series, market_returns: pd.Series) -> dict:
    return {
        "volatility": annualized_volatility(stock_returns),
        "beta": beta(stock_returns, market_returns),
        "max_drawdown": max_drawdown(stock_returns),
        "sharpe": sharpe_ratio(stock_returns),
    }
