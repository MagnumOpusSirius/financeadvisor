"""
Market page — candlestick price charts with your buy/sell markers overlaid,
plus technical indicators and recent news.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from styles import inject_css
from core.parser import load_csvs, get_trades
from market.fetcher import get_history, add_technical_indicators, get_news

st.set_page_config(page_title="Market", page_icon="📈", layout="wide")
inject_css()
st.title("📈 Market Context & Charts")

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

# ── Symbol / chart controls ────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.subheader("Chart Controls")

    traded_symbols = sorted(trades["symbol"].dropna().unique().tolist())
    symbol = st.selectbox("Symbol", traded_symbols, index=0 if traded_symbols else 0)

    indicators = st.multiselect(
        "Indicators",
        ["MA50", "MA200", "Bollinger Bands", "RSI", "MACD"],
        default=["MA50", "RSI"],
    )

    today = date.today()
    lookback_options = {
        "3 months": 90, "6 months": 180,
        "1 year": 365, "2 years": 730, "All time": 1000,
    }
    lookback_label = st.selectbox("Lookback", list(lookback_options.keys()), index=2)
    lookback_days = lookback_options[lookback_label]

    show_news = st.checkbox("Show recent news", value=True)

# ── Fetch price history ────────────────────────────────────────────────────
trade_start = trades[trades["symbol"] == symbol]["date"].min()
chart_start = max(
    (trade_start - timedelta(days=30)).date(),
    today - timedelta(days=lookback_days),
)

with st.spinner(f"Fetching {symbol} price history..."):
    hist = get_history(symbol, str(chart_start), str(today))
    if not hist.empty:
        hist = add_technical_indicators(hist)

if hist.empty:
    st.error(f"Could not fetch price data for {symbol}. Check the ticker symbol.")
    st.stop()

# ── Filter trades for this symbol ─────────────────────────────────────────
sym_trades = trades[
    (trades["symbol"] == symbol) &
    (trades["date"].dt.date >= chart_start)
].copy()

buys = sym_trades[sym_trades["action"] == "BUY"]
sells = sym_trades[sym_trades["action"] == "SELL"]

# ── Build chart ────────────────────────────────────────────────────────────
show_rsi = "RSI" in indicators
show_macd = "MACD" in indicators
n_subplots = 1 + int(show_rsi) + int(show_macd)
row_heights = [0.6] + [0.2] * (n_subplots - 1)

fig = make_subplots(
    rows=n_subplots, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
    row_heights=row_heights,
    subplot_titles=[symbol] + (["RSI (14)"] if show_rsi else []) + (["MACD"] if show_macd else []),
)

# Candlestick
fig.add_trace(go.Candlestick(
    x=hist.index, open=hist["Open"], high=hist["High"],
    low=hist["Low"], close=hist["Close"],
    name="Price",
    increasing_line_color="#00c9a7",
    decreasing_line_color="#ff4b4b",
), row=1, col=1)

# Moving averages
if "MA50" in indicators and "MA50" in hist.columns:
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["MA50"], name="MA50",
        line=dict(color="#ffa500", width=1.5, dash="dot"),
    ), row=1, col=1)

if "MA200" in indicators and "MA200" in hist.columns:
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["MA200"], name="MA200",
        line=dict(color="#a78bfa", width=1.5, dash="dash"),
    ), row=1, col=1)

# Bollinger Bands
if "Bollinger Bands" in indicators and "BB_upper" in hist.columns:
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["BB_upper"], name="BB Upper",
        line=dict(color="rgba(91,156,246,0.4)", width=1),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["BB_lower"], name="BB Lower",
        line=dict(color="rgba(91,156,246,0.4)", width=1),
        fill="tonexty", fillcolor="rgba(91,156,246,0.05)",
    ), row=1, col=1)

# Buy markers
if not buys.empty:
    buy_prices = []
    for _, row in buys.iterrows():
        d = row["date"].date()
        if d in hist.index.date:
            idx = hist.index[hist.index.date == d]
            buy_prices.append((row["date"], float(hist.loc[idx[0], "Low"]) * 0.99))
        elif not pd.isna(row["price"]):
            buy_prices.append((row["date"], float(row["price"])))

    if buy_prices:
        bx, by = zip(*buy_prices)
        fig.add_trace(go.Scatter(
            x=list(bx), y=list(by), mode="markers", name="Your Buys",
            marker=dict(symbol="triangle-up", size=12, color="#00c9a7",
                        line=dict(width=1, color="white")),
            hovertext=[f"BUY {symbol}<br>Price: ${p:.2f}" for _, p in buy_prices],
            hovertemplate="%{hovertext}<extra></extra>",
        ), row=1, col=1)

# Sell markers
if not sells.empty:
    sell_prices = []
    for _, row in sells.iterrows():
        d = row["date"].date()
        if d in hist.index.date:
            idx = hist.index[hist.index.date == d]
            sell_prices.append((row["date"], float(hist.loc[idx[0], "High"]) * 1.01))
        elif not pd.isna(row["price"]):
            sell_prices.append((row["date"], float(row["price"])))

    if sell_prices:
        sx, sy = zip(*sell_prices)
        fig.add_trace(go.Scatter(
            x=list(sx), y=list(sy), mode="markers", name="Your Sells",
            marker=dict(symbol="triangle-down", size=12, color="#ff4b4b",
                        line=dict(width=1, color="white")),
            hovertext=[f"SELL {symbol}<br>Price: ${p:.2f}" for _, p in sell_prices],
            hovertemplate="%{hovertext}<extra></extra>",
        ), row=1, col=1)

# RSI subplot
cur_row = 2
if show_rsi and "RSI" in hist.columns:
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["RSI"], name="RSI",
        line=dict(color="#5b9cf6", width=1.5),
    ), row=cur_row, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=cur_row, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=cur_row, col=1)
    fig.update_yaxes(range=[0, 100], row=cur_row)
    cur_row += 1

# MACD subplot
if show_macd and "MACD" in hist.columns:
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["MACD"], name="MACD",
        line=dict(color="#ffa500", width=1.5),
    ), row=cur_row, col=1)
    fig.add_trace(go.Scatter(
        x=hist.index, y=hist["MACD_signal"], name="Signal",
        line=dict(color="#a78bfa", width=1.5),
    ), row=cur_row, col=1)
    fig.add_trace(go.Bar(
        x=hist.index, y=hist["MACD_hist"], name="MACD Hist",
        marker_color=hist["MACD_hist"].apply(lambda v: "#00c9a7" if v > 0 else "#ff4b4b"),
    ), row=cur_row, col=1)

fig.update_layout(
    height=600 + 150 * (n_subplots - 1),
    xaxis_rangeslider_visible=False,
    margin=dict(t=40, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
)
st.plotly_chart(fig, use_container_width=True)

# ── RSI context at time of each trade ─────────────────────────────────────
st.subheader(f"Technical State at Time of Your {symbol} Trades")
if "RSI" in hist.columns and not sym_trades.empty:
    rows = []
    for _, row in sym_trades.iterrows():
        d = row["date"].date()
        hist_dates = hist.index.date
        if d in hist_dates:
            idx = hist.index[hist.index.date == d][0]
            rsi_val = hist.loc[idx, "RSI"] if "RSI" in hist.columns else None
            macd_val = hist.loc[idx, "MACD"] if "MACD" in hist.columns else None
            ma50_val = hist.loc[idx, "MA50"] if "MA50" in hist.columns else None
            rows.append({
                "Date": d,
                "Action": row["action"],
                "Price": row["price"],
                "RSI": round(rsi_val, 1) if rsi_val and not pd.isna(rsi_val) else None,
                "MACD": round(macd_val, 3) if macd_val and not pd.isna(macd_val) else None,
                "Above MA50": (row["price"] > ma50_val) if (ma50_val and not pd.isna(ma50_val)) else None,
            })

    if rows:
        context_df = pd.DataFrame(rows)

        def rsi_color(val):
            if pd.isna(val):
                return ""
            if val > 70:
                return "color: #ff4b4b"
            if val < 30:
                return "color: #00c9a7"
            return ""

        styled = context_df.style.applymap(rsi_color, subset=["RSI"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.caption("RSI > 70 = overbought (red), RSI < 30 = oversold (green). "
                   "Did you buy when RSI was high?")

# ── News feed ──────────────────────────────────────────────────────────────
if show_news:
    st.divider()
    st.subheader(f"Recent News: {symbol}")
    with st.spinner("Fetching news..."):
        news = get_news(symbol)

    if news:
        for item in news:
            title = item.get("title", "")
            link = item.get("link", "")
            publisher = item.get("publisher", "")
            published = item.get("published", "")
            if title:
                st.markdown(f"**[{title}]({link})**  \n_{publisher}_ · {published}")
                st.divider()
    else:
        st.info("No news found for this symbol.")
