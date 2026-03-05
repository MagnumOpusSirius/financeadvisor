"""
Demo data generator for Finance Advisor.

Generates a realistic synthetic DataFrame that exactly matches the schema
returned by core.parser.load_csvs(), so all downstream analytics and pages
work identically whether the user uploads real CSVs or clicks "Try Demo".

All trades are fictional. No real account data is used.
"""

import pandas as pd
import numpy as np
from datetime import datetime


def _ts(date_str: str) -> pd.Timestamp:
    return pd.Timestamp(date_str)


def _bday(date_str: str, n: int = 2) -> pd.Timestamp:
    """Approximate settlement: n business days after trade date."""
    ts = _ts(date_str)
    added = 0
    while added < n:
        ts += pd.Timedelta(days=1)
        if ts.weekday() < 5:
            added += 1
    return ts


# ── Raw row definitions ────────────────────────────────────────────────────
# Each tuple: (date_str, action, symbol, description, price, quantity, amount)
# amount is negative for buys, positive for sells/deposits/dividends.

_ACCOUNT     = "Individual - TOD"
_ACCT_NUM    = "Z00000000"          # fake account number
_TYPE        = "Cash"

_RAW_ROWS = [
    # ── Cash deposits (TRANSFER) ──────────────────────────────────────────
    ("01/03/2023", "Electronic Funds Transfer Received (Cash)",
     np.nan, "ELECTRONIC TRANSFER", np.nan, np.nan, 10_000.00),
    ("07/03/2023", "Electronic Funds Transfer Received (Cash)",
     np.nan, "ELECTRONIC TRANSFER", np.nan, np.nan, 5_000.00),
    ("01/02/2024", "Electronic Funds Transfer Received (Cash)",
     np.nan, "ELECTRONIC TRANSFER", np.nan, np.nan, 5_000.00),

    # ── AAPL ─────────────────────────────────────────────────────────────
    ("01/10/2023", "YOU BOUGHT APPLE INC (AAPL) (Cash)",
     "AAPL", "APPLE INC", 130.50, 15.0, -1_957.50),
    ("02/14/2023", "YOU SOLD APPLE INC (AAPL) (Cash)",
     "AAPL", "APPLE INC", 152.55, 15.0, 2_288.25),

    # ── NVDA (trade 1) ────────────────────────────────────────────────────
    ("01/17/2023", "YOU BOUGHT NVIDIA CORP (NVDA) (Cash)",
     "NVDA", "NVIDIA CORP", 155.00, 10.0, -1_550.00),
    ("03/20/2023", "YOU SOLD NVIDIA CORP (NVDA) (Cash)",
     "NVDA", "NVIDIA CORP", 270.00, 10.0, 2_700.00),

    # ── TSLA (loss) ───────────────────────────────────────────────────────
    ("02/01/2023", "YOU BOUGHT TESLA INC (TSLA) (Cash)",
     "TSLA", "TESLA INC", 190.00, 10.0, -1_900.00),
    ("03/10/2023", "YOU SOLD TESLA INC (TSLA) (Cash)",
     "TSLA", "TESLA INC", 178.00, 10.0, 1_780.00),

    # ── META ──────────────────────────────────────────────────────────────
    ("01/25/2023", "YOU BOUGHT META PLATFORMS INC (META) (Cash)",
     "META", "META PLATFORMS INC", 152.00, 8.0, -1_216.00),
    ("04/20/2023", "YOU SOLD META PLATFORMS INC (META) (Cash)",
     "META", "META PLATFORMS INC", 230.00, 8.0, 1_840.00),

    # ── NVDA (trade 2) ────────────────────────────────────────────────────
    ("05/01/2023", "YOU BOUGHT NVIDIA CORP (NVDA) (Cash)",
     "NVDA", "NVIDIA CORP", 280.00, 8.0, -2_240.00),
    ("06/15/2023", "YOU SOLD NVIDIA CORP (NVDA) (Cash)",
     "NVDA", "NVIDIA CORP", 395.00, 8.0, 3_160.00),

    # ── PLTR (trade 1) ────────────────────────────────────────────────────
    ("03/01/2023", "YOU BOUGHT PALANTIR TECHNOLOGIES INC CL A (PLTR) (Cash)",
     "PLTR", "PALANTIR TECHNOLOGIES INC CL A", 8.50, 100.0, -850.00),
    ("06/15/2023", "YOU SOLD PALANTIR TECHNOLOGIES INC CL A (PLTR) (Cash)",
     "PLTR", "PALANTIR TECHNOLOGIES INC CL A", 14.30, 100.0, 1_430.00),

    # ── NVDX leveraged ETF (win) ──────────────────────────────────────────
    ("06/05/2023", "YOU BOUGHT DIREXION SHS ETF TR DAILY NVDA BULL 2X (NVDX) (Cash)",
     "NVDX", "DIREXION NVDA BULL 2X", 12.00, 50.0, -600.00),
    ("06/20/2023", "YOU SOLD DIREXION SHS ETF TR DAILY NVDA BULL 2X (NVDX) (Cash)",
     "NVDX", "DIREXION NVDA BULL 2X", 17.50, 50.0, 875.00),

    # ── NVDX leveraged ETF (loss) ─────────────────────────────────────────
    ("07/10/2023", "YOU BOUGHT DIREXION SHS ETF TR DAILY NVDA BULL 2X (NVDX) (Cash)",
     "NVDX", "DIREXION NVDA BULL 2X", 24.00, 30.0, -720.00),
    ("07/25/2023", "YOU SOLD DIREXION SHS ETF TR DAILY NVDA BULL 2X (NVDX) (Cash)",
     "NVDX", "DIREXION NVDA BULL 2X", 18.50, 30.0, 555.00),

    # ── SPY ───────────────────────────────────────────────────────────────
    ("04/03/2023", "YOU BOUGHT SPDR S&P 500 ETF TRUST (SPY) (Cash)",
     "SPY", "SPDR S&P 500 ETF TRUST", 410.00, 5.0, -2_050.00),
    ("08/01/2023", "YOU SOLD SPDR S&P 500 ETF TRUST (SPY) (Cash)",
     "SPY", "SPDR S&P 500 ETF TRUST", 451.00, 5.0, 2_255.00),

    # ── AMZN ──────────────────────────────────────────────────────────────
    ("04/10/2023", "YOU BOUGHT AMAZON COM INC (AMZN) (Cash)",
     "AMZN", "AMAZON COM INC", 104.00, 12.0, -1_248.00),
    ("05/25/2023", "YOU SOLD AMAZON COM INC (AMZN) (Cash)",
     "AMZN", "AMAZON COM INC", 115.00, 12.0, 1_380.00),

    # ── TSLA (loss 2) ─────────────────────────────────────────────────────
    ("08/15/2023", "YOU BOUGHT TESLA INC (TSLA) (Cash)",
     "TSLA", "TESLA INC", 248.00, 6.0, -1_488.00),
    ("10/18/2023", "YOU SOLD TESLA INC (TSLA) (Cash)",
     "TSLA", "TESLA INC", 215.00, 6.0, 1_290.00),

    # ── PLTR (trade 2) ────────────────────────────────────────────────────
    ("10/01/2023", "YOU BOUGHT PALANTIR TECHNOLOGIES INC CL A (PLTR) (Cash)",
     "PLTR", "PALANTIR TECHNOLOGIES INC CL A", 16.50, 60.0, -990.00),
    ("12/15/2023", "YOU SOLD PALANTIR TECHNOLOGIES INC CL A (PLTR) (Cash)",
     "PLTR", "PALANTIR TECHNOLOGIES INC CL A", 19.00, 60.0, 1_140.00),

    # ── SPY dividends ─────────────────────────────────────────────────────
    ("03/31/2023", "DIVIDEND RECEIVED SPDR S&P 500 ETF TRUST (SPY) (Cash)",
     "SPY", "SPDR S&P 500 ETF TRUST", np.nan, np.nan, 12.50),
    ("06/30/2023", "DIVIDEND RECEIVED SPDR S&P 500 ETF TRUST (SPY) (Cash)",
     "SPY", "SPDR S&P 500 ETF TRUST", np.nan, np.nan, 15.00),
    ("09/30/2023", "DIVIDEND RECEIVED SPDR S&P 500 ETF TRUST (SPY) (Cash)",
     "SPY", "SPDR S&P 500 ETF TRUST", np.nan, np.nan, 13.75),

    # ── 2024 ─────────────────────────────────────────────────────────────
    # NVDA (big win)
    ("01/15/2024", "YOU BOUGHT NVIDIA CORP (NVDA) (Cash)",
     "NVDA", "NVIDIA CORP", 495.00, 4.0, -1_980.00),
    ("03/05/2024", "YOU SOLD NVIDIA CORP (NVDA) (Cash)",
     "NVDA", "NVIDIA CORP", 822.00, 4.0, 3_288.00),

    # MSFT
    ("03/10/2024", "YOU BOUGHT MICROSOFT CORP (MSFT) (Cash)",
     "MSFT", "MICROSOFT CORP", 415.00, 5.0, -2_075.00),
    ("06/15/2024", "YOU SOLD MICROSOFT CORP (MSFT) (Cash)",
     "MSFT", "MICROSOFT CORP", 445.00, 5.0, 2_225.00),

    # AAPL open position (no sell)
    ("02/05/2024", "YOU BOUGHT APPLE INC (AAPL) (Cash)",
     "AAPL", "APPLE INC", 187.00, 10.0, -1_870.00),

    # TSLA open position (no sell)
    ("04/15/2024", "YOU BOUGHT TESLA INC (TSLA) (Cash)",
     "TSLA", "TESLA INC", 172.00, 8.0, -1_376.00),
]


def _classify_action(raw: str) -> str:
    a = str(raw).upper()
    if a.startswith("YOU BOUGHT"):
        return "BUY"
    if a.startswith("YOU SOLD"):
        return "SELL"
    if "DIVIDEND RECEIVED" in a:
        return "DIVIDEND"
    if "ELECTRONIC FUNDS TRANSFER" in a or "FUNDS TRANSFER" in a:
        return "TRANSFER"
    return "OTHER"


_TICKER_SYMS = {"AAPL", "NVDA", "TSLA", "META", "PLTR", "NVDX", "SPY", "AMZN", "MSFT"}


def get_demo_df() -> pd.DataFrame:
    """
    Return a fully-typed DataFrame matching the schema of core.parser.load_csvs().
    Drop this into any page that expects the output of load_csvs().
    """
    records = []
    for row in _RAW_ROWS:
        date_str, action_raw, symbol, description, price, quantity, amount = row
        action = _classify_action(action_raw)
        is_ticker = symbol in _TICKER_SYMS if isinstance(symbol, str) else False

        records.append({
            "date":              pd.Timestamp(datetime.strptime(date_str, "%m/%d/%Y")),
            "account":           _ACCOUNT,
            "account_number":    _ACCT_NUM,
            "action_raw":        action_raw,
            "symbol":            symbol if isinstance(symbol, str) else np.nan,
            "description":       description,
            "type":              _TYPE,
            "price":             float(price) if pd.notna(price) else np.nan,
            "quantity":          float(quantity) if pd.notna(quantity) else np.nan,
            "commission":        np.nan,
            "fees":              np.nan,
            "accrued_interest":  np.nan,
            "amount":            float(amount),
            "settlement_date":   _bday(date_str),
            "is_ticker":         is_ticker,
            "action":            action,
            "amount_abs":        abs(float(amount)),
        })

    df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
    return df
