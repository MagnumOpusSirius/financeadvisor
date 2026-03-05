"""
Finance Advisor — landing page.
Run with:  streamlit run app.py
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from styles import inject_css

st.set_page_config(
    page_title="Finance Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📈 Finance Advisor")
    st.caption("Personal portfolio analytics for Fidelity accounts")
    st.divider()
    st.page_link("pages/1_Overview.py",  label="📊 Overview",  help="Key metrics & P&L")
    st.page_link("pages/2_Trades.py",   label="🔍 Trades",    help="Closed trade log")
    st.page_link("pages/3_Market.py",   label="📈 Market",    help="Charts & indicators")
    st.divider()
    st.caption("v0.1 — Phase 1")

# ── Hero ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fa-hero">
    <div class="fa-eyebrow">Portfolio Analytics</div>
    <h1 class="fa-hero-title">
        Your Trading History,<br>
        <span class="fa-hero-accent">Deeply Analyzed</span>
    </h1>
    <p class="fa-hero-sub">
        Upload your Fidelity account CSVs and instantly see FIFO P&amp;L,
        win rate, Sharpe ratio, max drawdown, candlestick charts with your
        own buy/sell markers, and much more — all in one place.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Demo CTA ───────────────────────────────────────────────────────────────
col_demo, col_real, col_pad = st.columns([1.8, 1.6, 3])

with col_demo:
    if st.button("🚀 Try Demo — No Upload Needed", use_container_width=True, type="primary"):
        from data.demo_generator import get_demo_df
        st.session_state["demo_df"] = get_demo_df()
        st.switch_page("pages/1_Overview.py")

with col_real:
    if st.button("📂 Upload My Fidelity CSVs", use_container_width=True):
        st.switch_page("pages/1_Overview.py")

st.markdown("<br>", unsafe_allow_html=True)

# ── Feature cards ──────────────────────────────────────────────────────────
st.markdown("#### What's inside")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class="fa-card">
        <span class="fa-card-icon">📊</span>
        <p class="fa-card-title">Overview Dashboard</p>
        <p class="fa-card-desc">
            Total realized P&amp;L, Sharpe ratio, max drawdown, win rate,
            profit factor, and a cumulative P&amp;L chart — all in one view.
        </p>
        <div class="fa-card-pills">
            <span class="fa-pill">FIFO P&amp;L</span>
            <span class="fa-pill">Sharpe</span>
            <span class="fa-pill">Drawdown</span>
            <span class="fa-pill">Open Positions</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="fa-card">
        <span class="fa-card-icon">🔍</span>
        <p class="fa-card-title">Trade History &amp; P&amp;L</p>
        <p class="fa-card-desc">
            Every closed trade matched with FIFO cost basis. Filter by symbol,
            account, outcome, and date range. Download as CSV.
        </p>
        <div class="fa-card-pills">
            <span class="fa-pill">FIFO Matching</span>
            <span class="fa-pill">Win/Loss</span>
            <span class="fa-pill">Holding Days</span>
            <span class="fa-pill">Export</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="fa-card">
        <span class="fa-card-icon">📈</span>
        <p class="fa-card-title">Market Context &amp; Charts</p>
        <p class="fa-card-desc">
            Live candlestick charts with your actual buy/sell markers overlaid.
            MA, RSI, MACD, Bollinger Bands, and recent news per symbol.
        </p>
        <div class="fa-card-pills">
            <span class="fa-pill">Candlestick</span>
            <span class="fa-pill">RSI / MACD</span>
            <span class="fa-pill">Buy/Sell Markers</span>
            <span class="fa-pill">News Feed</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Getting started + Tech stack ───────────────────────────────────────────
col_steps, col_stack = st.columns([1.1, 1])

with col_steps:
    st.markdown("#### Getting started")
    st.markdown("""
    <div class="fa-step">
        <div class="fa-step-num">1</div>
        <div class="fa-step-text">
            <strong>Export from Fidelity</strong><br>
            Accounts &amp; Trade → Account History → Download (CSV)
        </div>
    </div>
    <div class="fa-step">
        <div class="fa-step-num">2</div>
        <div class="fa-step-text">
            <strong>Upload in the sidebar</strong><br>
            Go to Overview and upload one or more quarterly CSV files
        </div>
    </div>
    <div class="fa-step">
        <div class="fa-step-num">3</div>
        <div class="fa-step-text">
            <strong>Explore your analytics</strong><br>
            All pages share the same uploaded data automatically
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_stack:
    st.markdown("#### Built with")
    st.markdown("""
    <div style="padding: 16px 0 8px 0;">
        <span class="fa-badge">🐍 Python</span>
        <span class="fa-badge">⚡ Streamlit</span>
        <span class="fa-badge">🐼 Pandas</span>
        <span class="fa-badge">📊 Plotly</span>
        <span class="fa-badge">📈 yfinance</span>
        <span class="fa-badge">🔢 NumPy</span>
        <span class="fa-badge">🤖 scikit-learn</span>
    </div>
    <div style="margin-top: 12px; padding: 16px 20px;
                background: rgba(0,201,167,0.05);
                border: 1px solid rgba(0,201,167,0.15);
                border-radius: 12px;">
        <p style="margin:0; font-size:0.82rem; color:#7a89a8; line-height:1.6;">
            <strong style="color:#00c9a7;">Privacy first</strong> — your CSV data
            is processed entirely in-session. Nothing is stored or transmitted.
        </p>
    </div>
    """, unsafe_allow_html=True)
