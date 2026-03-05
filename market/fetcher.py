"""
yfinance wrapper for fetching historical price data and basic news.
Results are cached in-process to avoid redundant API calls during a session.
"""

import pandas as pd
import numpy as np
from functools import lru_cache
from datetime import date, timedelta

import yfinance as yf


@lru_cache(maxsize=64)
def get_history(symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """
    Fetch OHLCV history for a symbol.
    start / end: "YYYY-MM-DD" strings (lru_cache requires hashable args)
    Returns a DataFrame with columns: Open, High, Low, Close, Volume
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval=interval, auto_adjust=True)
    if df.empty:
        return pd.DataFrame()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[["Open", "High", "Low", "Close", "Volume"]]


def get_current_price(symbol: str) -> float | None:
    """Fetch the most recent closing price for a symbol."""
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=5)).isoformat()
    df = get_history(symbol, yesterday, today)
    if df.empty:
        return None
    return float(df["Close"].iloc[-1])


def enrich_open_positions(open_pos: pd.DataFrame) -> pd.DataFrame:
    """
    Add current_price and unrealized_pnl columns to an open_positions DataFrame.
    """
    if open_pos.empty:
        return open_pos

    df = open_pos.copy()
    prices = {sym: get_current_price(sym) for sym in df["symbol"].unique()}
    df["current_price"] = df["symbol"].map(prices)
    df["market_value"] = df["shares_held"] * df["current_price"]
    df["unrealized_pnl"] = df["market_value"] - df["total_cost"]
    df["unrealized_pnl_pct"] = (df["unrealized_pnl"] / df["total_cost"] * 100).round(2)
    return df


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add RSI(14), MACD, 50-day MA, 200-day MA to an OHLCV DataFrame.
    """
    if df.empty or len(df) < 14:
        return df

    close = df["Close"]

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df = df.copy()
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # Moving averages
    if len(df) >= 50:
        df["MA50"] = close.rolling(50).mean()
    if len(df) >= 200:
        df["MA200"] = close.rolling(200).mean()

    # Bollinger Bands (20-day)
    df["BB_mid"] = close.rolling(20).mean()
    df["BB_std"] = close.rolling(20).std()
    df["BB_upper"] = df["BB_mid"] + 2 * df["BB_std"]
    df["BB_lower"] = df["BB_mid"] - 2 * df["BB_std"]

    return df


def get_news(symbol: str, max_items: int = 10) -> list[dict]:
    """
    Fetch recent news headlines for a symbol via yfinance.
    Returns list of {title, link, publisher, providerPublishTime}.
    """
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news or []
        out = []
        for item in news[:max_items]:
            out.append({
                "title": item.get("content", {}).get("title", ""),
                "link": item.get("content", {}).get("canonicalUrl", {}).get("url", ""),
                "publisher": item.get("content", {}).get("provider", {}).get("displayName", ""),
                "published": item.get("content", {}).get("pubDate", ""),
            })
        return out
    except Exception:
        return []
