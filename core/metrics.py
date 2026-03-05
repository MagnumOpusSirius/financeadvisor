"""
Risk and performance metrics computed from your trade history.
"""

import numpy as np
import pandas as pd


def sharpe_ratio(pnl_series: pd.Series, risk_free_rate: float = 0.05) -> float:
    """
    Annualized Sharpe ratio from a daily P&L series.
    risk_free_rate: annual, e.g. 0.05 = 5%
    """
    if pnl_series.empty or pnl_series.std() == 0:
        return 0.0
    daily_rf = risk_free_rate / 252
    excess = pnl_series - daily_rf
    return float(excess.mean() / excess.std() * np.sqrt(252))


def max_drawdown(cumulative_pnl: pd.Series) -> dict:
    """
    Maximum drawdown from a cumulative P&L series.
    Returns: {drawdown_pct, peak_date, trough_date, recovery_date}
    """
    if cumulative_pnl.empty:
        return {"drawdown_abs": 0.0, "peak_date": None, "trough_date": None}

    running_max = cumulative_pnl.cummax()
    drawdown = cumulative_pnl - running_max
    trough_idx = drawdown.idxmin()
    peak_idx = running_max[:trough_idx].idxmax()

    return {
        "drawdown_abs": float(drawdown[trough_idx]),
        "peak_date": peak_idx,
        "trough_date": trough_idx,
    }


def win_rate(closed_trades: pd.DataFrame) -> float:
    if closed_trades.empty:
        return 0.0
    return float(closed_trades["win"].mean())


def profit_factor(closed_trades: pd.DataFrame) -> float:
    """Gross profit / gross loss. > 1 means overall profitable."""
    if closed_trades.empty:
        return 0.0
    wins = closed_trades.loc[closed_trades["win"], "realized_pnl"].sum()
    losses = closed_trades.loc[~closed_trades["win"], "realized_pnl"].abs().sum()
    return float(wins / losses) if losses > 0 else float("inf")


def avg_win_loss_ratio(closed_trades: pd.DataFrame) -> float:
    """Average winning trade size / average losing trade size."""
    if closed_trades.empty:
        return 0.0
    avg_win = closed_trades.loc[closed_trades["win"], "realized_pnl"].mean()
    avg_loss = closed_trades.loc[~closed_trades["win"], "realized_pnl"].abs().mean()
    if pd.isna(avg_win) or pd.isna(avg_loss) or avg_loss == 0:
        return 0.0
    return float(avg_win / avg_loss)


def trade_frequency(closed_trades: pd.DataFrame) -> dict:
    """How many trades per week / month on average."""
    if closed_trades.empty:
        return {"per_week": 0.0, "per_month": 0.0}

    days_span = (closed_trades["sell_date"].max() - closed_trades["sell_date"].min()).days
    if days_span == 0:
        return {"per_week": 0.0, "per_month": 0.0}

    n = len(closed_trades)
    return {
        "per_week": round(n / (days_span / 7), 2),
        "per_month": round(n / (days_span / 30), 2),
    }


def holding_period_distribution(closed_trades: pd.DataFrame) -> dict:
    """Breakdown of trades by holding period bucket."""
    if closed_trades.empty:
        return {}

    bins = [0, 1, 7, 30, 90, float("inf")]
    labels = ["Intraday", "2-7 days", "1-4 weeks", "1-3 months", "3+ months"]
    cut = pd.cut(closed_trades["holding_days"], bins=bins, labels=labels, right=True)
    return cut.value_counts().to_dict()


def risk_score(closed_trades: pd.DataFrame) -> float:
    """
    Simple 0-10 risk score based on:
      - % of leveraged ETF trades (PLTU, NVDX, etc.) → high risk
      - Average holding period (shorter = higher risk for leveraged)
      - Win rate (lower win rate = higher risk realization)
    Higher score = higher risk.
    """
    if closed_trades.empty:
        return 0.0

    leveraged_keywords = ["U", "X", "BULL", "BEAR"]  # common leveraged ETF suffixes
    leveraged_mask = closed_trades["symbol"].str.endswith(
        tuple(leveraged_keywords), na=False
    )
    leveraged_frac = leveraged_mask.mean()

    avg_hold = closed_trades["holding_days"].mean()
    hold_score = max(0, 1 - avg_hold / 30)  # 0 hold days = 1, 30+ days = 0

    wr = win_rate(closed_trades)
    loss_score = 1 - wr

    score = (leveraged_frac * 4 + hold_score * 3 + loss_score * 3)
    return round(min(10.0, score * 10), 1)
