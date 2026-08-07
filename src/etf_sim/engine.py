"""One simulated trading day of ETF secondary-market life.

Design decisions worth defending
--------------------------------
1. We model the *premium* directly and define price = iNAV * (1 + premium).
   Modelling the spread rather than two separate price levels isolates the
   thing the project is about (the price/NAV gap) from basket volatility.

2. Timing per step: shocks/noise hit first, then the AP observes the
   resulting premium and acts, then impact applies. The AP therefore reacts
   with an effective one-step lag — it cannot front-run the shock.

3. The premium has three drivers:
     - demand shocks: rare, lumpy flow imbalances (Bernoulli * Normal)
     - micro noise: constant small order-flow wobble (Normal)
     - natural reversion: weak mean-reversion even with the AP off, because
       other participants (stat-arb desks, informed buyers) also lean
       against obvious mispricings — just without primary-market access.
   With the AP off you still get a stationary but wide premium process;
   the AP is what *caps* it near the cost band. That contrast is the
   pedagogical point of the app's "AP off" toggle.

4. AP P&L is booked as units * CU_value * edge_bps: a stylised, hedged
   arbitrage profit, not a mark-to-market of inventory (the AP is assumed
   flat after each round trip).
"""

import numpy as np
import pandas as pd

from .ap import decide
from .basket import inav_series, simulate_stock_paths
from .config import SimParams


def run_simulation(p: SimParams, ap_enabled: bool = True) -> pd.DataFrame:
    p.validate()
    rng = np.random.default_rng(p.seed)

    prices = simulate_stock_paths(p, rng)          # (n_steps+1, n_stocks)
    inav = inav_series(prices, p)                  # (n_steps+1,)

    n = p.n_steps
    premium = np.empty(n + 1)
    premium[0] = p.initial_premium_bps
    ap_cus = np.zeros(n + 1, dtype=int)
    shares_out = np.empty(n + 1)
    shares_out[0] = p.initial_cus_outstanding * p.shares_per_cu
    ap_pnl = np.zeros(n + 1)

    # Pre-draw randomness so ap_enabled=True/False share identical shocks —
    # this makes the on/off comparison in the UI apples-to-apples.
    shock_hits = rng.random(n) < p.demand_shock_prob
    shock_sizes = rng.normal(0.0, p.demand_shock_bps, size=n)
    noise = rng.normal(0.0, p.micro_noise_bps, size=n)

    for t in range(1, n + 1):
        prem = premium[t - 1]
        prem *= (1.0 - p.natural_reversion)               # weak non-AP pull
        prem += noise[t - 1]
        if shock_hits[t - 1]:
            prem += shock_sizes[t - 1]

        action = decide(prem, p) if ap_enabled else decide(prem, _ap_off(p))
        if action.cus != 0:
            prem -= action.cus * p.impact_bps_per_cu      # impact closes gap
            cu_value = p.shares_per_cu * inav[t]
            ap_pnl[t] = abs(action.cus) * cu_value * action.edge_bps / 1e4

        premium[t] = prem
        ap_cus[t] = action.cus
        shares_out[t] = shares_out[t - 1] + action.cus * p.shares_per_cu
        ap_pnl[t] += ap_pnl[t - 1]

    df = pd.DataFrame(
        {
            "minute": np.arange(n + 1),
            "inav": inav,
            "premium_bps": premium,
            "ap_cus": ap_cus,
            "shares_outstanding": shares_out,
            "ap_pnl_cum": ap_pnl,
        }
    )
    df["price"] = df["inav"] * (1.0 + df["premium_bps"] / 1e4)
    for i in range(p.n_stocks):
        df[f"stock_{i}"] = prices[:, i]
    return df


def _ap_off(p: SimParams) -> SimParams:
    """Copy of params with an infinitely lazy AP (for the comparison toggle)."""
    from dataclasses import replace

    return replace(p, ap_aggressiveness=0.0)
