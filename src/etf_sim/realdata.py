"""Real UCITS ETF data: tracking difference / error, and premium vs NAV.

Data honesty (an interview talking point)
-----------------------------------------
Yahoo Finance provides *market prices*. True premium/discount is market
price vs the fund's official *NAV*, which issuers publish daily on their
own sites (e.g. the iShares CSPX product page has a downloadable NAV
history). So:

- Tracking difference / tracking error: computed here from price returns
  vs a TOTAL RETURN index (^SP500TR), because accumulating UCITS ETFs
  reinvest dividends — comparing them to the price-only ^GSPC would
  overstate performance by the full dividend yield. TD from *price*
  returns also embeds premium/discount wobble at the endpoints; over long
  windows that noise is small relative to fee + withholding drag.

- Premium/discount: only computed when the user uploads an official NAV
  CSV (columns: date, nav). We do NOT fake it from prices.

Both series must be in the same currency: CSPX.L and VUAA.L trade in USD
on the LSE, matching ^SP500TR (USD). Mixing an EUR line (e.g. VWCE.DE)
with a USD index would contaminate TD with FX moves.
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252

# label -> (etf_ticker, benchmark_ticker) ; all USD-quoted pairs
PRESETS = {
    "CSPX.L — iShares Core S&P 500 UCITS (Acc)": ("CSPX.L", "^SP500TR"),
    "VUAA.L — Vanguard S&P 500 UCITS (Acc)": ("VUAA.L", "^SP500TR"),
    "SPY5.L — SPDR S&P 500 UCITS ETF": ("SPY5.L", "^SP500TR"),
}


def fetch_pair(etf: str, benchmark: str, period: str = "5y") -> pd.DataFrame:
    """Download adjusted closes for the ETF and its benchmark, aligned."""
    import yfinance as yf  # imported lazily so the sim engine has no dep

    raw = yf.download(
        [etf, benchmark], period=period, auto_adjust=True, progress=False
    )["Close"]
    df = raw.dropna().rename(columns={etf: "etf", benchmark: "index"})
    if df.empty:
        raise ValueError(
            f"No overlapping data for {etf} / {benchmark}. "
            "Check tickers or try a shorter period."
        )
    return df


def tracking_metrics(df: pd.DataFrame) -> dict:
    """Annualised tracking difference and tracking error, plus daily diffs."""
    rets = df.pct_change().dropna()
    diff = rets["etf"] - rets["index"]
    n_years = len(rets) / TRADING_DAYS

    cum_etf = (1 + rets["etf"]).prod()
    cum_idx = (1 + rets["index"]).prod()
    td_annual = (cum_etf ** (1 / n_years)) - (cum_idx ** (1 / n_years))
    te_annual = diff.std() * np.sqrt(TRADING_DAYS)

    return {
        "td_annual_bps": td_annual * 1e4,
        "te_annual_bps": te_annual * 1e4,
        "daily_diff": diff,
        "n_years": n_years,
    }


def relative_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Both series indexed to 100, plus the cumulative gap in bps."""
    out = 100.0 * df / df.iloc[0]
    out["cum_gap_bps"] = (out["etf"] / out["index"] - 1.0) * 1e4
    return out


def rolling_tracking_difference(df: pd.DataFrame, window: int = TRADING_DAYS) -> pd.Series:
    """Rolling 1y tracking difference (bps): trailing ETF return minus index."""
    ratio = df["etf"] / df["index"]
    return (ratio / ratio.shift(window) - 1.0).dropna() * 1e4


def premium_from_nav(prices: pd.Series, nav_csv: pd.DataFrame) -> pd.Series:
    """Premium/discount in bps from an official issuer NAV file.

    Expects columns (case-insensitive): date, nav.
    """
    nav = nav_csv.copy()
    nav.columns = [c.strip().lower() for c in nav.columns]
    if not {"date", "nav"}.issubset(nav.columns):
        raise ValueError("NAV file needs 'date' and 'nav' columns.")
    nav["date"] = pd.to_datetime(nav["date"])
    nav = nav.set_index("date")["nav"].astype(float)
    aligned = pd.concat([prices.rename("price"), nav.rename("nav")], axis=1).dropna()
    return (aligned["price"] / aligned["nav"] - 1.0) * 1e4
