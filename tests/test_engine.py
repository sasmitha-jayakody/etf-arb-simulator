"""Economic-invariant tests for the simulation engine.

These assert properties of ETF mechanics rather than implementation details:
if one of them fails, the model is economically wrong, not just refactored.
"""

import numpy as np
import pytest

from etf_sim.ap import decide
from etf_sim.basket import holdings_per_share, inav_series, simulate_stock_paths
from etf_sim.config import SimParams
from etf_sim.engine import run_simulation


def test_nav_starts_at_initial_nav():
    p = SimParams()
    rng = np.random.default_rng(p.seed)
    prices = simulate_stock_paths(p, rng)
    inav = inav_series(prices, p)
    assert inav[0] == pytest.approx(p.initial_nav)


def test_holdings_per_share_reprice_to_nav():
    """The basket backing one ETF share must be worth exactly NAV at t=0."""
    p = SimParams()
    h = holdings_per_share(p)
    assert float(h @ np.asarray(p.initial_prices)) == pytest.approx(p.initial_nav)


def test_creations_do_not_change_nav_per_share():
    """The core in-kind invariance.

    Run the same shock path with the AP on and off. With the AP on, shares
    outstanding move; with it off, they don't. The iNAV path per share must be
    identical either way, because pro-rata in-kind creation adds assets and
    shares in the same proportion.
    """
    p = SimParams()
    on = run_simulation(p, ap_enabled=True)
    off = run_simulation(p, ap_enabled=False)

    assert on["shares_outstanding"].nunique() > 1, "expected some AP activity"
    assert off["shares_outstanding"].nunique() == 1, "AP off should not create"
    np.testing.assert_allclose(on["inav"], off["inav"])


def test_price_is_inav_times_premium():
    p = SimParams()
    df = run_simulation(p)
    np.testing.assert_allclose(
        df["price"], df["inav"] * (1.0 + df["premium_bps"] / 1e4)
    )


def test_ap_never_acts_inside_the_band():
    p = SimParams()
    for prem in [-p.ap_cost_bps + 0.01, 0.0, p.ap_cost_bps - 0.01]:
        assert decide(prem, p).cus == 0


def test_ap_direction_matches_mispricing():
    p = SimParams()
    assert decide(p.ap_cost_bps + 50, p).cus > 0     # premium -> create
    assert decide(-p.ap_cost_bps - 50, p).cus < 0    # discount -> redeem


def test_ap_edge_is_never_negative():
    """An AP that would lose money on the marginal unit should not book a gain."""
    p = SimParams()
    for prem in np.linspace(-200, 200, 81):
        assert decide(float(prem), p).edge_bps >= 0.0


def test_ap_tames_the_premium():
    """Same shocks (same seed), AP on vs off: the AP must materially reduce
    how far the price strays from NAV."""
    p = SimParams(seed=42, demand_shock_prob=0.05, demand_shock_bps=40.0)
    on = run_simulation(p, ap_enabled=True)
    off = run_simulation(p, ap_enabled=False)
    assert on["premium_bps"].abs().max() < off["premium_bps"].abs().max()
    assert on["premium_bps"].abs().mean() < off["premium_bps"].abs().mean()


def test_wider_ap_cost_means_a_wider_band():
    """A costlier AP tolerates a bigger gap before stepping in."""
    cheap = run_simulation(SimParams(seed=3, ap_cost_bps=10.0))
    dear = run_simulation(SimParams(seed=3, ap_cost_bps=60.0))
    assert cheap["premium_bps"].abs().mean() < dear["premium_bps"].abs().mean()


def test_shares_outstanding_move_with_ap_actions():
    p = SimParams()
    df = run_simulation(p)
    implied = (
        p.initial_cus_outstanding * p.shares_per_cu
        + df["ap_cus"].cumsum() * p.shares_per_cu
    )
    np.testing.assert_allclose(df["shares_outstanding"], implied)


def test_reproducible_given_seed():
    a = run_simulation(SimParams(seed=11))
    b = run_simulation(SimParams(seed=11))
    assert a.equals(b)
