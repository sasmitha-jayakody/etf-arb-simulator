"""Authorised Participant decision rule.

Economic logic
--------------
The AP faces an all-in cost per creation/redemption (execution of the
basket, the issuer's CU fee, hedging risk), quoted in bps of value. This
cost defines a no-arbitrage band around NAV:

    -cost_bps  <  premium  <  +cost_bps      -> no profitable trade, do nothing
    premium    >  +cost_bps                  -> CREATE: buy basket, deliver
                                                in-kind, sell new ETF shares
    premium    <  -cost_bps                  -> REDEEM: buy ETF shares, redeem
                                                for basket, sell the basket

Intensity scales with the *excess* gap (premium beyond cost): a 60bp
premium against a 25bp cost is hit far harder than a 27bp one, because the
profit-to-risk ratio is higher and more APs compete for it. `aggressiveness`
proxies AP competition / engagement; `max_cus_per_step` proxies operational
throughput (order cut-offs, balance-sheet limits).

Creation units are indivisible, hence the floor(): mispricings worth less
than ~1 CU of edge persist. That is realistic and visible in the output.
"""

from dataclasses import dataclass

import numpy as np

from .config import SimParams


@dataclass
class APAction:
    cus: int          # +n = create n units (adds supply), -n = redeem n units
    edge_bps: float   # per-unit profit captured, in bps (0 if no action)


def decide(premium_bps: float, p: SimParams) -> APAction:
    gap = abs(premium_bps) - p.ap_cost_bps
    if gap <= 0:
        return APAction(cus=0, edge_bps=0.0)

    # How many units would it take to push the premium back to the band edge?
    units_to_band = gap / p.impact_bps_per_cu
    n = int(np.floor(p.ap_aggressiveness * units_to_band))
    n = min(n, p.max_cus_per_step)
    if n == 0:
        return APAction(cus=0, edge_bps=0.0)

    sign = 1 if premium_bps > 0 else -1          # premium -> create
    # Average edge on the units traded: the first unit earns ~gap, the last
    # earns ~gap - n*impact; approximate with the midpoint.
    avg_edge = max(gap - 0.5 * n * p.impact_bps_per_cu, 0.0)
    return APAction(cus=sign * n, edge_bps=avg_edge)
