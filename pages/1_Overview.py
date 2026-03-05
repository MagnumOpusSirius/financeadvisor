"""
Overview page — upload CSVs, compute key metrics, show summary dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from styles import inject_css
from core.parser import load_csvs, load_positions_csv, get_trades, get_transfers, get_dividends, is_standard_ticker
from core.portfolio import (
    match_trades_fifo,
    open_positions,
    symbol_summary,
    cumulative_pnl_series,
    total_deposited,
    unmatched_sells,
)
from core.metrics import (
    sharpe_ratio,
    max_drawdown,
    win_rate,
    profit_factor,
    avg_win_loss_ratio,
    trade_frequency,
    holding_period_distribution,
    risk_score,
)
from market.fetcher import enrich_open_positions

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
inject_css()
st.title("📊 Portfolio Overview")

# ── Demo mode state ────────────────────────────────────────────────────────
demo_df = st.session_state.get("demo_df")

# ── Sidebar: CSV upload ────────────────────────────────────────────────────
with st.sidebar:
    if demo_df is not None:
        st.markdown('<div class="fa-demo-banner">🚀 Demo mode active</div>', unsafe_allow_html=True)
        if st.button("✕ Exit Demo", use_container_width=True):
            del st.session_state["demo_df"]
            st.rerun()
        st.divider()
    else:
        st.header("Upload CSVs")
        uploaded = st.file_uploader(
            "Fidelity Account History CSVs",
            type=["csv"],
            accept_multiple_files=True,
            help="Export from Fidelity: Accounts & Trade → Account History → Download",
        )
        if uploaded:
            st.success(f"{len(uploaded)} file(s) loaded")

        st.divider()
        st.subheader("Fidelity Realized Gains (optional)")
        uploaded_positions = st.file_uploader(
            "Portfolio Positions / Realized Gains CSV",
            type=["csv"],
            accept_multiple_files=False,
            help="Export from Fidelity: Portfolio → Positions → Realized Gain/Loss → Download. "
                 "Used as the official reference to validate our FIFO calculations.",
            key="positions_upload",
        )
        st.divider()

    st.caption("Finance Advisor v0.1 — Phase 1")

# ── Load data ──────────────────────────────────────────────────────────────
if demo_df is not None:
    df = demo_df
    uploaded = None
    uploaded_positions = None
elif not uploaded:
    st.info("Upload your Fidelity CSV files in the sidebar to get started.", icon="👈")
    st.stop()

@st.cache_data
def load_data(file_contents: list[tuple[str, bytes]]) -> pd.DataFrame:
    import tempfile, os
    tmp_paths = []
    for name, content in file_contents:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        tmp.write(content)
        tmp.close()
        tmp_paths.append(tmp.name)
    df = load_csvs(tmp_paths)
    for p in tmp_paths:
        os.unlink(p)
    return df

if demo_df is None:
    file_contents = [(f.name, f.read()) for f in uploaded]
    for f in uploaded:
        f.seek(0)
    with st.spinner("Parsing transactions..."):
        df = load_data(file_contents)

trades = get_trades(df)
transfers = get_transfers(df)
dividends = get_dividends(df)
closed = match_trades_fifo(trades)
open_pos = open_positions(trades)
orphaned = unmatched_sells(trades)

# ── Account filter ─────────────────────────────────────────────────────────
all_accounts = sorted(df["account"].dropna().unique().tolist())

# Auto-exclude employer/plan accounts (TANDYM, etc.) — they use CUSIPs and
# aren't part of the self-directed trading strategy
plan_accounts = [a for a in all_accounts if a.upper() not in
                 ("INDIVIDUAL", "INDIVIDUAL - TOD", "ROTH IRA", "TRADITIONAL IRA")]
default_excluded = set(plan_accounts)

with st.sidebar:
    st.divider()
    st.subheader("Account Filter")
    selected_accounts = st.multiselect(
        "Include accounts",
        options=all_accounts,
        default=[a for a in all_accounts if a not in default_excluded],
        help="Employer/plan accounts (TANDYM, etc.) are excluded by default — "
             "they use CUSIP identifiers and aren't part of your self-directed strategy.",
    )

if not selected_accounts:
    selected_accounts = all_accounts  # fallback: show everything

selected_account = "All accounts"  # kept for legacy compatibility below

trades_f = trades[trades["account"].isin(selected_accounts)]
closed_f = closed[closed["account"].isin(selected_accounts)] if not closed.empty else closed
transfers_f = transfers[transfers["account"].isin(selected_accounts)]
dividends_f = dividends[dividends["account"].isin(selected_accounts)]

# ── Orphaned sell warning ──────────────────────────────────────────────────
orphaned_f = orphaned[orphaned["account"].isin(selected_accounts)] if not orphaned.empty else orphaned

if not orphaned_f.empty:
    # Split: real tickers (actionable) vs CUSIPs/plan-shares (noise)
    ticker_mask = orphaned_f["symbol"].apply(is_standard_ticker)
    orphaned_tickers = orphaned_f[ticker_mask]
    orphaned_plan = orphaned_f[~ticker_mask]

    if not orphaned_tickers.empty:
        missing = orphaned_tickers["unmatched_proceeds"].sum()
        syms = sorted(orphaned_tickers["symbol"].unique().tolist())
        st.warning(
            f"**Incomplete history — P&L is understated by an unknown amount.**  \n"
            f"**{len(orphaned_tickers)} sell(s)** across **{len(syms)} ticker(s)** "
            f"({', '.join(syms)}) have no matching buy in your uploaded files, "
            f"covering **${missing:,.2f} in proceeds**.  \n"
            f"These stocks were likely bought before your earliest uploaded file. "
            f"Export and upload your full history (including 2023 if applicable) to fix this.",
            icon="⚠️",
        )
        with st.expander("Show unmatched ticker sells"):
            st.dataframe(
                orphaned_tickers[["date", "symbol", "account", "sell_qty",
                                   "matched_qty", "unmatched_qty", "unmatched_proceeds"]].round(3),
                use_container_width=True, hide_index=True,
            )

    if not orphaned_plan.empty:
        plan_proceeds = orphaned_plan["unmatched_proceeds"].sum()
        with st.expander(
            f"ℹ️ {len(orphaned_plan)} employer/plan-account entries excluded from analysis "
            f"(${plan_proceeds:,.2f} in proceeds — CUSIP identifiers, not standard tickers)"
        ):
            st.caption(
                "These rows use CUSIP codes instead of ticker symbols. They come from automated "
                "employer 401k / payroll plan contributions (e.g. TANDYM account) and are excluded "
                "from all P&L and trade analysis since they don't represent manual trading decisions."
            )
            st.dataframe(
                orphaned_plan[["date", "symbol", "account", "unmatched_proceeds"]].round(2),
                use_container_width=True, hide_index=True,
            )

# ── Fidelity positions reference ───────────────────────────────────────────
if uploaded_positions:
    @st.cache_data
    def load_positions(content: bytes) -> pd.DataFrame:
        import tempfile, os
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        tmp.write(content)
        tmp.close()
        df = load_positions_csv(tmp.name)
        os.unlink(tmp.name)
        return df

    pos_df = load_positions(uploaded_positions.read())
    uploaded_positions.seek(0)

    fidelity_total = pos_df["total_gl"].sum()
    our_total = closed["realized_pnl"].sum() if not closed.empty else 0
    delta = our_total - fidelity_total

    st.info(
        f"**Fidelity official realized gain: ${fidelity_total:,.2f}**  \n"
        f"Our FIFO calculation: ${our_total:,.2f}  \n"
        f"Difference: ${delta:,.2f}"
        + (f" — upload the missing quarterly file(s) to close the gap." if abs(delta) > 10 else " — numbers match!"),
        icon="📋",
    )
    with st.expander("Fidelity realized gains by symbol"):
        display_pos = pos_df[["account", "symbol", "cost_basis", "proceeds",
                               "short_term_gl", "long_term_gl", "total_gl"]].copy()
        display_pos.columns = ["Account", "Symbol", "Cost Basis", "Proceeds",
                                "ST Gain/Loss", "LT Gain/Loss", "Total G/L"]
        for col in ["Cost Basis", "Proceeds", "ST Gain/Loss", "LT Gain/Loss", "Total G/L"]:
            display_pos[col] = display_pos[col].map("${:,.2f}".format)
        st.dataframe(display_pos, use_container_width=True, hide_index=True)
        st.caption(f"**Total: ${fidelity_total:,.2f}** across {len(pos_df)} closed positions")

# ── Key metric cards ───────────────────────────────────────────────────────
st.subheader("Key Metrics")
col1, col2, col3, col4, col5 = st.columns(5)

total_pnl = closed_f["realized_pnl"].sum() if not closed_f.empty else 0
total_dep = total_deposited(transfers_f)
div_total = dividends_f["amount"].sum() if not dividends_f.empty else 0
wr = win_rate(closed_f)
rs = risk_score(closed_f)

col1.metric("Realized P&L", f"${total_pnl:,.2f}", delta=f"{total_pnl:+.2f}")
col2.metric("Cash Deposited", f"${total_dep:,.2f}")
col3.metric("Dividends Earned", f"${div_total:,.2f}")
col4.metric("Win Rate", f"{wr:.0%}", delta=f"{wr - 0.5:.0%} vs 50%")
col5.metric("Risk Score", f"{rs} / 10", help="0 = conservative, 10 = very aggressive")

st.divider()

# ── Cumulative P&L chart ───────────────────────────────────────────────────
if not closed_f.empty:
    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.subheader("Cumulative Realized P&L")
        cum_pnl = cumulative_pnl_series(closed_f)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cum_pnl.index, y=cum_pnl.values,
            mode="lines+markers",
            line=dict(color="#00c9a7", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,201,167,0.1)",
            name="Cumulative P&L",
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(
            xaxis_title="Date", yaxis_title="Cumulative P&L ($)",
            height=350, margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Additional Metrics")
        pf = profit_factor(closed_f)
        wl = avg_win_loss_ratio(closed_f)
        freq = trade_frequency(closed_f)
        sr = sharpe_ratio(closed_f.groupby("sell_date")["realized_pnl"].sum().reindex(
            pd.date_range(closed_f["sell_date"].min(), closed_f["sell_date"].max()), fill_value=0
        ))
        mdd = max_drawdown(cumulative_pnl_series(closed_f))

        st.metric("Profit Factor", f"{pf:.2f}", help="Gross wins / Gross losses. >1 is profitable.")
        st.metric("Avg Win/Loss Ratio", f"{wl:.2f}", help="Avg winning trade / Avg losing trade")
        st.metric("Sharpe Ratio", f"{sr:.2f}", help="Risk-adjusted return (annualized)")
        st.metric("Max Drawdown", f"${mdd['drawdown_abs']:,.2f}")
        st.metric("Trades / Week", str(freq["per_week"]))

# ── Per-symbol summary ─────────────────────────────────────────────────────
st.divider()
st.subheader("Performance by Symbol")

if not closed_f.empty:
    sym_sum = symbol_summary(closed_f, open_pos)

    col_chart, col_table = st.columns([1, 1])

    with col_chart:
        fig2 = px.bar(
            sym_sum, x="symbol", y="total_realized_pnl",
            color="total_realized_pnl",
            color_continuous_scale=["#ff4b4b", "#ffa500", "#00c9a7"],
            labels={"total_realized_pnl": "Realized P&L ($)", "symbol": "Symbol"},
            title="Realized P&L per Symbol",
        )
        fig2.update_layout(height=320, margin=dict(t=40, b=20), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with col_table:
        display = sym_sum[[
            "symbol", "trade_count", "total_realized_pnl",
            "win_rate", "avg_holding_days", "overall_return_pct"
        ]].copy()
        display.columns = ["Symbol", "Trades", "Realized P&L", "Win Rate", "Avg Hold (days)", "Return %"]
        display["Realized P&L"] = display["Realized P&L"].map("${:,.2f}".format)
        display["Win Rate"] = display["Win Rate"].map("{:.0%}".format)
        display["Avg Hold (days)"] = display["Avg Hold (days)"].map("{:.1f}".format)
        display["Return %"] = display["Return %"].map("{:+.1f}%".format)
        st.dataframe(display, use_container_width=True, hide_index=True)

# ── Holding period distribution ────────────────────────────────────────────
st.divider()
col_hold, col_open = st.columns([1, 1])

with col_hold:
    st.subheader("Holding Period Breakdown")
    if not closed_f.empty:
        hold_dist = holding_period_distribution(closed_f)
        fig3 = px.pie(
            values=list(hold_dist.values()),
            names=list(hold_dist.keys()),
            color_discrete_sequence=px.colors.sequential.Teal,
        )
        fig3.update_layout(height=300, margin=dict(t=20, b=20))
        st.plotly_chart(fig3, use_container_width=True)

with col_open:
    st.subheader("Open Positions")
    if not open_pos.empty:
        enriched = enrich_open_positions(open_pos)
        display_cols = ["symbol", "account", "shares_held", "avg_cost_basis",
                        "current_price", "market_value", "unrealized_pnl", "unrealized_pnl_pct"]
        avail = [c for c in display_cols if c in enriched.columns]
        st.dataframe(enriched[avail].round(2), use_container_width=True, hide_index=True)
    else:
        st.info("No open positions detected.")
