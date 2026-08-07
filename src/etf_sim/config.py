"""Simulation parameters.

Every slider in the Streamlit UI maps to exactly one field here. The engine
never reads globals or UI state: it takes a SimParams object, so any run is
fully reproducible from (params, seed).

Units convention: premiums, costs and impacts are in *basis points* (1bp =
0.01%) because that is how practitioners quote them; they are converted to
decimals only inside the arithmetic.
"""

from dataclasses import dataclass


@dataclass
class SimParams:
    # --- market clock -----------------------------------------------------
    n_steps: int = 390          # one simulated trading day, 1 step = 1 minute

    # --- the underlying basket -------------------------------------------
    n_stocks: int = 5
    initial_prices: tuple = (120.0, 80.0, 200.0, 55.0, 145.0)
    weights: tuple = (0.30, 0.20, 0.20, 0.15, 0.15)  # index weights, sum to 1
    annual_vol: float = 0.20    # per-stock annualised volatility
    correlation: float = 0.60   # pairwise correlation between stocks

    # --- fund structure ---------------------------------------------------
    initial_nav: float = 100.0        # NAV per ETF share at t=0
    shares_per_cu: int = 50_000       # ETF shares in one creation unit
    initial_cus_outstanding: int = 40 # 40 CUs x 50k = 2m shares outstanding

    # --- secondary-market price process (the premium, in bps) ------------
    initial_premium_bps: float = 0.0
    demand_shock_prob: float = 0.03   # per-step probability of a flow shock
    demand_shock_bps: float = 25.0    # typical size of a shock (signed)
    micro_noise_bps: float = 2.0      # per-step order-flow noise
    natural_reversion: float = 0.01   # weak pull to NAV even without APs
                                      # (non-AP participants also see the gap)

    # --- the AP -----------------------------------------------------------
    ap_cost_bps: float = 25.0         # all-in cost per CU: execution + fee +
                                      # hedging risk. Defines the band width.
    ap_aggressiveness: float = 0.6    # 0 = AP asleep, 1 = hits every edge
    impact_bps_per_cu: float = 6.0    # premium moved per CU created/redeemed
    max_cus_per_step: int = 5         # operational limit per minute

    seed: int = 7

    def validate(self) -> None:
        assert abs(sum(self.weights) - 1.0) < 1e-9, "weights must sum to 1"
        assert len(self.weights) == self.n_stocks == len(self.initial_prices)
        assert self.ap_cost_bps >= 0 and self.impact_bps_per_cu > 0
