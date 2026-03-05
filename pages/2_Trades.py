"""
Trades page — closed trade log with FIFO P&L, filters, and per-trade analysis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from styles import inject_css
from core.parser import load_csvs, get_trades, get_transfers
from core.portfolio import match_trades_fifo

st.set_page_config(page_title="Trades", page_icon="🔍", layout="wide")
inject_css()
st.title("🔍 Trade History & P&L")

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
        )
        if uploaded:
            st.success(f"{len(uploaded)} file(s) loaded")

if demo_df is not None:
    df = demo_df
elif not uploaded:
    st.info("Upload your Fidelity CSV files in the sidebar.", icon="👈")
    st.stop()
else:
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

    file_contents = [(f.name, f.read()) for f in uploaded]
    for f in uploaded:
        f.seek(0)
    df = load_data(file_contents)

trades = get_trades(df)
closed = match_trades_fifo(trades)

if closed.empty:
    st.warning("No closed trades found. Make sure you have both BUY and SELL rows in your CSV files.")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.subheader("Filters")
    symbols = ["All"] + sorted(closed["symbol"].unique().tolist())
    sel_symbol = st.selectbox("Symbol", symbols)

    accounts = ["All"] + sorted(closed["account"].unique().tolist())
    sel_account = st.selectbox("Account", accounts)

    outcomes = st.multiselect("Outcome", ["Win", "Loss"], default=["Win", "Loss"])

    date_min = closed["sell_date"].min().date()
    date_max = closed["sell_date"].max().date()
    date_range = st.date_input("Sell Date Range", value=(date_min, date_max))

filtered = closed.copy()
if sel_symbol != "All":
    filtered = filtered[filtered["symbol"] == sel_symbol]
if sel_account != "All":
    filtered = filtered[filtered["account"] == sel_account]
if "Win" in outcomes and "Loss" not in outcomes:
    filtered = filtered[filtered["win"]]
elif "Loss" in outcomes and "Win" not in outcomes:
    filtered = filtered[~filtered["win"]]
if len(date_range) == 2:
    filtered = filtered[
        (filtered["sell_date"].dt.date >= date_range[0]) &
        (filtered["sell_date"].dt.date <= date_range[1])
    ]

# ── Summary strip ──────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Trades shown", len(filtered))
c2.metric("Total P&L", f"${filtered['realized_pnl'].sum():,.2f}")
c3.metric("Win Rate", f"{filtered['win'].mean():.0%}" if not filtered.empty else "—")
c4.metric("Avg Hold", f"{filtered['holding_days'].mean():.1f} days" if not filtered.empty else "—")

st.divider()

# ── P&L scatter: each trade as a dot ──────────────────────────────────────
col_scatter, col_hist = st.columns([3, 2])

with col_scatter:
    st.subheader("P&L per Trade")
    fig = go.Figure()
    for sym, grp in filtered.groupby("symbol"):
        fig.add_trace(go.Scatter(
            x=grp["sell_date"],
            y=grp["realized_pnl"],
            mode="markers",
            name=sym,
            marker=dict(
                size=8,
                color=grp["realized_pnl"].apply(lambda x: "#00c9a7" if x > 0 else "#ff4b4b"),
                line=dict(width=1, color="white"),
            ),
            text=grp.apply(
                lambda r: f"{r['symbol']}<br>P&L: ${r['realized_pnl']:,.2f}<br>"
                          f"Hold: {r['holding_days']}d<br>"
                          f"Buy: ${r['buy_price']:.2f} → Sell: ${r['sell_price']:.2f}",
                axis=1,
            ),
            hovertemplate="%{text}<extra></extra>",
        ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        xaxis_title="Sell Date", yaxis_title="Realized P&L ($)",
        height=380, margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_hist:
    st.subheader("P&L Distribution")
    fig2 = px.histogram(
        filtered, x="realized_pnl", nbins=30,
        color_discrete_sequence=["#5b9cf6"],
        labels={"realized_pnl": "Realized P&L ($)"},
    )
    fig2.add_vline(x=0, line_dash="dash", line_color="gray")
    fig2.update_layout(height=380, margin=dict(t=20, b=20))
    st.plotly_chart(fig2, use_container_width=True)

# ── Holding period vs P&L ──────────────────────────────────────────────────
st.subheader("Holding Period vs P&L")
fig3 = px.scatter(
    filtered, x="holding_days", y="realized_pnl",
    color="symbol", size="buy_amount",
    hover_data=["buy_date", "sell_date", "buy_price", "sell_price", "quantity"],
    labels={"holding_days": "Holding Days", "realized_pnl": "Realized P&L ($)"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig3.add_hline(y=0, line_dash="dash", line_color="gray")
fig3.update_layout(height=350, margin=dict(t=20, b=20))
st.plotly_chart(fig3, use_container_width=True)

# ── Raw trade table ────────────────────────────────────────────────────────
st.subheader("Trade Log")
display = filtered[[
    "symbol", "account", "buy_date", "buy_price", "sell_date", "sell_price",
    "quantity", "buy_amount", "sell_amount", "realized_pnl", "pnl_pct",
    "holding_days", "win",
]].copy()

display.columns = [
    "Symbol", "Account", "Buy Date", "Buy Price", "Sell Date", "Sell Price",
    "Qty", "Cost", "Proceeds", "P&L", "P&L %", "Hold Days", "Win",
]

def color_pnl(val):
    color = "#00c9a7" if val > 0 else "#ff4b4b"
    return f"color: {color}"

styled = display.style.format({
    "Buy Price": "${:.2f}",
    "Sell Price": "${:.2f}",
    "Cost": "${:.2f}",
    "Proceeds": "${:.2f}",
    "P&L": "${:+.2f}",
    "P&L %": "{:+.2f}%",
    "Qty": "{:.4f}",
}).applymap(color_pnl, subset=["P&L", "P&L %"])

st.dataframe(styled, use_container_width=True, hide_index=True, height=400)

csv_out = display.to_csv(index=False)
st.download_button("Download filtered trades as CSV", csv_out, "trades.csv", "text/csv")
