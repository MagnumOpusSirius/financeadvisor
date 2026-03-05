"""
Shared CSS injection for Finance Advisor.
Call inject_css() at the top of every page.
"""

import streamlit as st

_CSS = """
<style>
/* ── Google Font ─────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── Metric cards ─────────────────────────────── */
[data-testid="metric-container"] {
    background: linear-gradient(145deg, #1c2233 0%, #141824 100%);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 14px;
    padding: 20px 18px 18px 18px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.04);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    position: relative;
    overflow: hidden;
}

[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00c9a7, #5b9cf6);
    border-radius: 14px 14px 0 0;
}

[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0, 201, 167, 0.12), inset 0 1px 0 rgba(255,255,255,0.06);
    border-color: rgba(0, 201, 167, 0.25);
}

[data-testid="metric-label"] > div, [data-testid="metric-label"] p {
    color: #8b96b0 !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.10em !important;
    text-transform: uppercase !important;
}

[data-testid="stMetricValue"] > div {
    color: #eef2ff !important;
    font-size: 1.65rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    line-height: 1.2 !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    margin-top: 4px !important;
}

/* ── Hero card (landing page) ─────────────────── */
.fa-hero {
    background: linear-gradient(135deg, #0d1526 0%, #162040 40%, #0a1a30 100%);
    border: 1px solid rgba(0, 201, 167, 0.12);
    border-radius: 20px;
    padding: 56px 52px;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}

.fa-hero::before {
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(0,201,167,0.06) 0%, transparent 70%);
    pointer-events: none;
}

.fa-hero::after {
    content: '';
    position: absolute;
    bottom: -100px; left: 30%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(91,156,246,0.05) 0%, transparent 70%);
    pointer-events: none;
}

.fa-eyebrow {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #00c9a7;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.fa-eyebrow::before {
    content: '';
    display: inline-block;
    width: 24px;
    height: 2px;
    background: #00c9a7;
    border-radius: 2px;
}

.fa-hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    line-height: 1.1;
    color: #eef2ff;
    margin: 0 0 16px 0;
    letter-spacing: -0.04em;
}

.fa-hero-accent {
    background: linear-gradient(135deg, #00c9a7 0%, #5b9cf6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.fa-hero-sub {
    font-size: 1.05rem;
    color: #7a89a8;
    line-height: 1.6;
    max-width: 560px;
    margin: 0;
    font-weight: 400;
}

/* ── Feature cards ────────────────────────────── */
.fa-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
    padding: 28px 24px;
    height: 100%;
    transition: all 0.25s ease;
    cursor: default;
    position: relative;
}

.fa-card:hover {
    border-color: rgba(0, 201, 167, 0.25);
    background: rgba(0, 201, 167, 0.03);
    transform: translateY(-3px);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
}

.fa-card-icon {
    font-size: 2rem;
    margin-bottom: 14px;
    display: block;
}

.fa-card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #eef2ff;
    margin: 0 0 8px 0;
    letter-spacing: -0.01em;
}

.fa-card-desc {
    font-size: 0.85rem;
    color: #7a89a8;
    line-height: 1.6;
    margin: 0;
}

.fa-card-pills {
    margin-top: 14px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.fa-pill {
    background: rgba(0,201,167,0.1);
    border: 1px solid rgba(0,201,167,0.2);
    color: #00c9a7;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}

/* ── Tech badge ───────────────────────────────── */
.fa-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 0.8rem;
    font-weight: 500;
    color: #a0b4d0;
    margin: 4px;
    transition: all 0.2s;
}

.fa-badge:hover {
    border-color: rgba(0,201,167,0.3);
    color: #c8d8f0;
}

/* ── Demo banner ──────────────────────────────── */
.fa-demo-banner {
    background: linear-gradient(90deg, rgba(0,201,167,0.08) 0%, rgba(91,156,246,0.06) 100%);
    border: 1px solid rgba(0,201,167,0.25);
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 1rem;
    font-size: 0.82rem;
    font-weight: 500;
    color: #00c9a7;
}

/* ── Step card (getting started) ──────────────── */
.fa-step {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 18px 20px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 12px;
    margin-bottom: 10px;
}

.fa-step-num {
    background: linear-gradient(135deg, #00c9a7, #5b9cf6);
    color: #000;
    font-weight: 800;
    font-size: 0.8rem;
    width: 26px;
    height: 26px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
}

.fa-step-text {
    font-size: 0.88rem;
    color: #c0ccdd;
    line-height: 1.5;
}

.fa-step-text strong {
    color: #eef2ff;
    font-weight: 600;
}

/* ── Sidebar polish ───────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #141824 0%, #0e1117 100%);
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* ── Dividers ─────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid rgba(255,255,255,0.07) !important;
    margin: 1.5rem 0 !important;
}

/* ── Dataframe ────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.06);
}

/* ── Info / warning boxes ─────────────────────── */
[data-testid="stInfo"] {
    border-radius: 10px;
    border-left-color: #5b9cf6;
}

[data-testid="stWarning"] {
    border-radius: 10px;
}

/* ── Section titles ───────────────────────────── */
h2 { letter-spacing: -0.025em !important; }
h3 { letter-spacing: -0.015em !important; }

/* ── Scrollbar ────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.25); }
</style>
"""


def inject_css() -> None:
    """Inject global Finance Advisor CSS into the current Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)
