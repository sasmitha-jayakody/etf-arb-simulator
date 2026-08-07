"""Synthetic underlying basket and iNAV.

The fund holds `holdings[i]` shares of stock i *per ETF share*. Because
creations are in-kind and pro-rata, this vector is constant: when an AP
creates a unit it delivers the same basket per new share, so NAV per share
is unaffected by primary-market activity. That invariance is a core piece
of ETF plumbing and is asserted in the test suite.

iNAV_t = sum_i holdings[i] * S_i(t)  — i.e. reprice the disclosed basket
with live prices, which is exactly what a real iNAV calculation agent does
(published every ~15 seconds on exchanges).
"""

import numpy as np

from .config import SimParams

TRADING_DAYS = 252


def holdings_per_share(p: SimParams) -> np.ndarray:
    """Stock quantities backing one ETF share, chosen so NAV(0)=initial_nav.

    holdings[i] = initial_nav * weight[i] / S_i(0)
    """
    s0 = np.asarray(p.initial_prices, dtype=float)
    w = np.asarray(p.weights, dtype=float)
    return p.initial_nav * w / s0


def simulate_stock_paths(p: SimParams, rng: np.random.Generator) -> np.ndarray:
    """Correlated geometric Brownian motion, minute frequency.

    Returns array of shape (n_steps + 1, n_stocks) including t=0.
    Correlation is imposed via a Cholesky factor of a single-factor
    correlation matrix (rho off-diagonal) — simple, always positive
    semi-definite for rho in [0, 1).
    """
    n, k = p.n_steps, p.n_stocks
    dt = 1.0 / (TRADING_DAYS * p.n_steps)          # fraction of a year
    sigma = p.annual_vol

    corr = np.full((k, k), p.correlation)
    np.fill_diagonal(corr, 1.0)
    chol = np.linalg.cholesky(corr)

    z = rng.standard_normal((n, k)) @ chol.T
    increments = (-0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    log_paths = np.vstack([np.zeros(k), np.cumsum(increments, axis=0)])
    return np.asarray(p.initial_prices) * np.exp(log_paths)


def inav_series(prices: np.ndarray, p: SimParams) -> np.ndarray:
    """iNAV path: live basket value of one ETF share."""
    return prices @ holdings_per_share(p)
