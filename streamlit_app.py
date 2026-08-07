"""ETF Creation/Redemption & Premium/Discount Simulator — Streamlit UI.

This file is UI only. All model logic lives in src/etf_sim/ (pure Python,
unit-tested with pytest). Streamlit Cloud auto-detects this filename at the
repo root as the app entry point.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))  # src/ layout, no install step

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from etf_sim.config import SimParams
from etf_sim.engine import run_simulation

st.set_page_config(page_title="ETF Arbitrage Simulator", page_icon="📈", layout="wide")

st.title("ETF creation/redemption & premium/discount simulator")
st.caption(
    "How the Authorised Participant arbitrage mechanism keeps an ETF's market "
    "price anchored to its NAV. Educational project — not investment advice."
)

tab_sim, tab_real, tab_explain = st.tabs(
    ["🔬 Simulator", "📊 Real UCITS ETF data", "📖 Explainer"]
)

# ---------------------------------------------------------------- simulator
with tab_sim:
    with st.sidebar:
        st.header("Simulation parameters")

        st.subheader("Market")
        vol = st.slider("Basket volatility (annualised, %)", 5, 60, 20) / 100
        shock_prob = st.slider("Demand-shock probability per minute (%)", 0, 15, 3) / 100
        shock_bps = st.slider("Demand-shock size (bps)", 5, 100, 25)
        noise_bps = st.slider("Order-flow noise (bps/min)", 0.0, 10.0, 2.0, 0.5)

        st.subheader("Fund")
        cu_size = st.select_slider(
            "Creation-unit size (ETF shares)",
            options=[10_000, 25_000, 50_000, 100_000],
            value=50_000,
        )

        st.subheader("Authorised Participant")
        ap_cost = st.slider("AP all-in cost (bps) — the band half-width", 0, 100, 25)
        aggr = st.slider("AP aggressiveness (competition proxy)", 0.0, 1.0, 0.6, 0.05)
        impact = st.slider("Price impact per creation unit (bps)", 1.0, 20.0, 6.0, 0.5)

        seed = st.number_input("Random seed", 0, 9999, 7)
        compare = st.checkbox("Overlay a no-AP counterfactual (same shocks)", True)

    params = SimParams(
        annual_vol=vol,
        demand_shock_prob=shock_prob,
        demand_shock_bps=float(shock_bps),
        micro_noise_bps=float(noise_bps),
        shares_per_cu=int(cu_size),
        ap_cost_bps=float(ap_cost),
        ap_aggressiveness=float(aggr),
        impact_bps_per_cu=float(impact),
        seed=int(seed),
    )

    df = run_simulation(params, ap_enabled=True)
    df_off = run_simulation(params, ap_enabled=False) if compare else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Max |premium|", f"{df['premium_bps'].abs().max():.0f} bps")
    c2.metric(
        "Time outside band",
        f"{(df['premium_bps'].abs() > params.ap_cost_bps).mean():.0%}",
    )
    n_creates = int(df.loc[df["ap_cus"] > 0, "ap_cus"].sum())
    n_redeems = int(-df.loc[df["ap_cus"] < 0, "ap_cus"].sum())
    c3.metric("CUs created / redeemed", f"{n_creates} / {n_redeems}")
    c4.metric("AP arbitrage P&L", f"${df['ap_pnl_cum'].iloc[-1]:,.0f}")

    left, right = st.columns(2)

    with left:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(df["minute"], df["inav"], label="iNAV", lw=1.6)
        ax.plot(df["minute"], df["price"], label="Market price (AP on)", lw=1.0, alpha=0.9)
        if df_off is not None:
            ax.plot(
                df_off["minute"], df_off["price"],
                label="Market price (no AP)", lw=1.0, ls="--", alpha=0.7,
            )
        ax.set_xlabel("Minute of trading day")
        ax.set_ylabel("Value per ETF share")
        ax.set_title("Price vs iNAV")
        ax.legend(fontsize=8)
        st.pyplot(fig)
        plt.close(fig)

    with right:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.axhspan(-params.ap_cost_bps, params.ap_cost_bps, alpha=0.15,
                   label="No-arbitrage band (±AP cost)")
        ax.plot(df["minute"], df["premium_bps"], lw=1.0, label="Premium (AP on)")
        if df_off is not None:
            ax.plot(df_off["minute"], df_off["premium_bps"], lw=1.0, ls="--",
                    alpha=0.7, label="Premium (no AP)")
        ax.axhline(0, color="black", lw=0.5)
        ax.set_xlabel("Minute of trading day")
        ax.set_ylabel("Premium / discount (bps)")
        ax.set_title("Premium vs the no-arbitrage band")
        ax.legend(fontsize=8)
        st.pyplot(fig)
        plt.close(fig)

    left2, right2 = st.columns(2)

    with left2:
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ax.step(df["minute"], df["shares_outstanding"] / 1e6, where="post", lw=1.2)
        ax.set_xlabel("Minute of trading day")
        ax.set_ylabel("Shares outstanding (m)")
        ax.set_title("Primary-market activity: shares outstanding")
        st.pyplot(fig)
        plt.close(fig)

    with right2:
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ax.plot(df["minute"], df["ap_pnl_cum"] / 1e3, lw=1.2)
        ax.set_xlabel("Minute of trading day")
        ax.set_ylabel("Cumulative AP P&L ($k)")
        ax.set_title("AP arbitrage profits (stylised, hedged)")
        st.pyplot(fig)
        plt.close(fig)

    with st.expander("What am I looking at?"):
        st.markdown(
            """
- **iNAV** is the live value of the fund's disclosed basket per share.
- The **market price** is pushed around by demand shocks and order-flow noise.
- Whenever the premium/discount exceeds the **AP's all-in cost** (shaded band),
  the AP creates units (premium: sell new supply) or redeems (discount: retire
  supply), and the **price impact** of that activity drags the price back.
- Toggle the **no-AP counterfactual** to see the same shock path without the
  arbitrage mechanism. On the default settings the worst gap of the day roughly
  doubles and the price spends about twice as long outside the band.
- Try: raise AP cost to 80bp (illiquid basket) → wider band, bigger persistent
  gaps. Raise aggressiveness to 1.0 (many competing APs) → gaps snap shut.
"""
        )

# ---------------------------------------------------------------- real data
with tab_real:
    from etf_sim.realdata import (
        PRESETS,
        fetch_pair,
        premium_from_nav,
        relative_performance,
        rolling_tracking_difference,
        tracking_metrics,
    )

    st.subheader("Irish-domiciled UCITS ETFs vs their benchmark")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        preset = st.selectbox("ETF (all USD-quoted vs S&P 500 total return)", list(PRESETS))
    with col_b:
        period = st.selectbox("History", ["2y", "5y", "10y", "max"], index=1)

    etf_ticker, bench_ticker = PRESETS[preset]

    @st.cache_data(ttl=3600, show_spinner="Downloading prices…")
    def _load(etf: str, bench: str, per: str) -> pd.DataFrame:
        return fetch_pair(etf, bench, per)

    try:
        data = _load(etf_ticker, bench_ticker, period)
        m = tracking_metrics(data)

        k1, k2, k3 = st.columns(3)
        k1.metric("Annualised tracking difference", f"{m['td_annual_bps']:+.0f} bps")
        k2.metric("Annualised tracking error", f"{m['te_annual_bps']:.0f} bps")
        k3.metric("Sample length", f"{m['n_years']:.1f} years")

        rel = relative_performance(data)
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.plot(rel.index, rel["etf"], label=etf_ticker, lw=1.2)
        ax.plot(rel.index, rel["index"], label=bench_ticker, lw=1.2, alpha=0.8)
        ax.set_title("Growth of 100 (both USD)")
        ax.legend(fontsize=8)
        st.pyplot(fig)
        plt.close(fig)

        roll = rolling_tracking_difference(data)
        if not roll.empty:
            fig, ax = plt.subplots(figsize=(9, 3.2))
            ax.plot(roll.index, roll, lw=1.0)
            ax.axhline(0, color="black", lw=0.5)
            ax.set_title("Rolling 1-year tracking difference (bps)")
            ax.set_ylabel("bps")
            st.pyplot(fig)
            plt.close(fig)

        with st.expander("Why is the tracking difference not just the TER?"):
            st.markdown(
                """
The TER is only one drag. **Withholding tax** on US dividends costs an
Irish-domiciled fund 15% of the ~1.3% S&P 500 yield (~20bp/yr) — already
reflected in the *net* total-return benchmarks issuers track, and the reason
Irish funds beat Luxembourg equivalents (30% withholding). **Securities-lending
revenue** adds a few bp back. **Sampling and execution** add noise. And because
this app uses *market prices* (Yahoo has no official NAVs), endpoint
premium/discount wobble leaks into short-window figures.
"""
            )

        st.divider()
        st.subheader("Premium/discount — requires official NAV data")
        st.markdown(
            "Yahoo provides market prices only. True premium/discount is price vs the "
            "fund's **official NAV**, published daily by the issuer (e.g. the iShares "
            "CSPX product page → *NAV history* download). Upload it as a CSV with "
            "`date` and `nav` columns:"
        )
        upload = st.file_uploader("Issuer NAV history (CSV)", type="csv")
        if upload is not None:
            nav_df = pd.read_csv(upload)
            prem = premium_from_nav(data["etf"], nav_df)
            fig, ax = plt.subplots(figsize=(9, 3.2))
            ax.plot(prem.index, prem, lw=0.9)
            ax.axhline(0, color="black", lw=0.5)
            ax.set_title(f"{etf_ticker}: premium/discount to official NAV (bps)")
            ax.set_ylabel("bps")
            st.pyplot(fig)
            plt.close(fig)
            st.metric("Mean |premium|", f"{prem.abs().mean():.0f} bps")

    except Exception as e:  # network hiccups, delisted tickers, etc.
        st.warning(
            f"Could not load data ({e}). Yahoo Finance occasionally rate-limits "
            "or renames tickers — try again or pick a different preset."
        )

# ---------------------------------------------------------------- explainer
with tab_explain:
    explainer_path = Path(__file__).parent / "content" / "explainer.md"
    st.markdown(explainer_path.read_text())
