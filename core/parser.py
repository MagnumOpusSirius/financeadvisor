"""
Fidelity CSV parser.

Fidelity exports have 2 blank rows before the header, then data rows.
Columns: Run Date, Account, Account Number, Action, Symbol, Description,
         Type, Price ($), Quantity, Commission ($), Fees ($),
         Accrued Interest ($), Amount ($), Settlement Date

Action strings encode the trade type, e.g.:
  "YOU BOUGHT PALANTIR TECHNOLOGIES INC CL A (PLTR) (Cash)"
  "YOU SOLD DIREXION SHS ETF TR DAILY PLTR BULL (PLTU) (Cash)"
  "DIVIDEND RECEIVED FIDELITY GOVERNMENT MONEY MARKET (SPAXX) (Cash)"
  "REINVESTMENT FIDELITY GOVERNMENT MONEY MARKET (SPAXX) (Cash)"
  "Electronic Funds Transfer Received (Cash)"
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from io import StringIO

_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}")


# ── Column rename map ──────────────────────────────────────────────────────
_COL_MAP = {
    "Run Date": "date",
    "Account": "account",
    "Account Number": "account_number",
    "Action": "action_raw",
    "Symbol": "symbol",
    "Description": "description",
    "Type": "type",
    "Price ($)": "price",
    "Quantity": "quantity",
    "Commission ($)": "commission",
    "Fees ($)": "fees",
    "Accrued Interest ($)": "accrued_interest",
    "Amount ($)": "amount",
    "Settlement Date": "settlement_date",
}

# ── Ticker vs CUSIP / plan-share identifier ───────────────────────────────
_TICKER_RE = re.compile(r"^[A-Z]{1,5}(\.?[A-Z])?$")  # e.g. PLTR, BRK.B, TSLA

def is_standard_ticker(symbol: str) -> bool:
    """
    Return True if the symbol looks like a standard exchange-traded ticker
    (1–5 uppercase letters, optionally one dotted suffix like BRK.B).

    CUSIP codes (e.g. '00688A205', '3622AW304') contain digits and are 9 chars.
    Fidelity plan-share IDs and mutual fund CUSIPs also fail this test.
    Bankruptcy tickers ending in Q (e.g. OTRKQ) are kept — they're real trades.
    """
    if not symbol or not isinstance(symbol, str):
        return False
    s = symbol.strip().upper()
    # Allow Q/W suffixes for bankruptcy/warrant OTC symbols (OTRKQ, STAFQ)
    if s.endswith("Q") or s.endswith("W"):
        base = s[:-1]
        return bool(_TICKER_RE.match(base)) and len(base) >= 1
    return bool(_TICKER_RE.match(s))


# ── Action-type classification ─────────────────────────────────────────────
def _classify_action(action: str) -> str:
    a = str(action).upper()
    if a.startswith("YOU BOUGHT"):
        return "BUY"
    if a.startswith("YOU SOLD"):
        return "SELL"
    if "DIVIDEND RECEIVED" in a:
        return "DIVIDEND"
    if a.startswith("REINVESTMENT"):
        return "REINVESTMENT"
    if "ELECTRONIC FUNDS TRANSFER" in a or "FUNDS TRANSFER" in a:
        return "TRANSFER"
    return "OTHER"


def _read_single_csv(path: str | Path) -> pd.DataFrame:
    """
    Read one Fidelity CSV, skipping blank preamble rows AND any footer
    disclaimer text that Fidelity appends after the data.
    """
    path = Path(path)

    with open(path, encoding="utf-8-sig") as f:
        lines = f.readlines()

    # Find the header row ("Run Date,Account,...")
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Run Date"):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(f"Could not find header row in {path.name}. "
                         "Expected a row starting with 'Run Date'.")

    # Find the last actual data row — any line whose first field is a date.
    # This ignores the Fidelity legal disclaimer/footer that some exports append.
    last_data_idx = header_idx
    for i, line in enumerate(lines[header_idx + 1:], start=header_idx + 1):
        if _DATE_RE.match(line.strip()):
            last_data_idx = i

    # Slice to just header + data rows, then parse from a string buffer.
    # on_bad_lines='skip' handles rows with unexpected column counts (e.g.
    # TANDYM employer-account contribution rows that have a trailing extra comma).
    data_text = "".join(lines[header_idx : last_data_idx + 1])
    df = pd.read_csv(StringIO(data_text), dtype=str, on_bad_lines="skip")
    return df


def load_csvs(paths: list[str | Path]) -> pd.DataFrame:
    """
    Load and merge one or more Fidelity account-history CSV files.
    Returns a clean, typed DataFrame with all transactions combined.
    """
    frames = []
    for p in paths:
        try:
            frames.append(_read_single_csv(p))
        except Exception as e:
            print(f"Warning: could not parse {p}: {e}")

    if not frames:
        raise ValueError("No valid CSV files were loaded.")

    raw = pd.concat(frames, ignore_index=True)

    # ── Rename columns ─────────────────────────────────────────────────────
    raw = raw.rename(columns=_COL_MAP)

    # Keep only expected columns (drop any Fidelity footer junk rows)
    expected = list(_COL_MAP.values())
    raw = raw[[c for c in expected if c in raw.columns]]

    # ── Drop empty / footer rows ───────────────────────────────────────────
    raw = raw.dropna(subset=["date", "action_raw"], how="any")
    raw = raw[raw["date"].str.match(r"\d{2}/\d{2}/\d{4}", na=False)]

    # ── Parse dates ────────────────────────────────────────────────────────
    raw["date"] = pd.to_datetime(raw["date"], format="%m/%d/%Y")
    raw["settlement_date"] = pd.to_datetime(
        raw["settlement_date"], format="%m/%d/%Y", errors="coerce"
    )

    # ── Clean symbol ───────────────────────────────────────────────────────
    raw["symbol"] = raw["symbol"].str.strip().replace("", np.nan)

    # ── Tag rows: standard exchange ticker vs CUSIP / plan-share identifier ──
    # CUSIP rows come from employer 401k/plan accounts (e.g. TANDYM) and
    # automated fund investments. They look like '00688A205', 'G1180K116'.
    raw["is_ticker"] = raw["symbol"].apply(
        lambda s: is_standard_ticker(s) if pd.notna(s) else False
    )

    # ── Parse numeric columns ──────────────────────────────────────────────
    for col in ["price", "quantity", "commission", "fees", "accrued_interest", "amount"]:
        if col in raw.columns:
            raw[col] = pd.to_numeric(raw[col], errors="coerce")

    # ── Classify action type ───────────────────────────────────────────────
    raw["action"] = raw["action_raw"].apply(_classify_action)

    # ── Derived: absolute amount spent/received ────────────────────────────
    # Amount is negative for buys, positive for sells in Fidelity format
    raw["amount_abs"] = raw["amount"].abs()

    # ── Sort chronologically ───────────────────────────────────────────────
    raw = raw.sort_values("date").reset_index(drop=True)

    return raw


def get_trades(df: pd.DataFrame, tickers_only: bool = True) -> pd.DataFrame:
    """
    Return only BUY and SELL rows.

    tickers_only=True (default): exclude CUSIP/plan-share rows so that
    automated employer-plan contributions don't pollute the trade analysis
    or inflate the orphaned-sell count.
    Set to False only if you need to see all raw transactions including
    TANDYM/401k plan buys.
    """
    mask = df["action"].isin(["BUY", "SELL"])
    if tickers_only and "is_ticker" in df.columns:
        mask &= df["is_ticker"]
    return df[mask].copy()


def get_transfers(df: pd.DataFrame) -> pd.DataFrame:
    """Return only cash deposit/withdrawal rows."""
    return df[df["action"] == "TRANSFER"].copy()


def get_dividends(df: pd.DataFrame) -> pd.DataFrame:
    """Return only dividend rows."""
    return df[df["action"] == "DIVIDEND"].copy()


def _parse_dollar(val: str) -> float:
    """Parse Fidelity dollar strings like '+$1,648.44', '--', '-$500.00' → float."""
    if pd.isna(val) or str(val).strip() in ("--", "", "nan"):
        return 0.0
    return float(str(val).replace("$", "").replace(",", "").replace("+", "").strip())


def load_positions_csv(path: str | Path) -> pd.DataFrame:
    """
    Parse a Fidelity 'Portfolio Positions / Realized Gains' CSV.

    Expected columns:
      Account Number, Account Name, Symbol, Description,
      Cost Basis, Proceeds, Short Term Gain/Loss, Long Term Gain/Loss,
      Total Term Gain/Loss

    Returns a clean DataFrame with numeric gain/loss columns.
    This file is Fidelity's official realized-gain record and is used as
    the ground-truth reference to validate our FIFO calculations.
    """
    path = Path(path)

    with open(path, encoding="utf-8-sig") as f:
        lines = f.readlines()

    # Find header row
    header_idx = None
    for i, line in enumerate(lines):
        if "Account Number" in line and "Symbol" in line:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(f"Could not find header in {path.name}. "
                         "Expected a row containing 'Account Number' and 'Symbol'.")

    # Find last actual data row (non-blank, before footer)
    last_data_idx = header_idx
    for i, line in enumerate(lines[header_idx + 1:], start=header_idx + 1):
        stripped = line.strip()
        if stripped and not stripped.startswith('"') and not stripped.startswith("Date"):
            last_data_idx = i

    data_text = "".join(lines[header_idx : last_data_idx + 1])
    # index_col=False prevents pandas from treating the first column as the
    # row index when rows have a trailing comma (which adds an extra empty field).
    df = pd.read_csv(StringIO(data_text), dtype=str, on_bad_lines="skip", index_col=False)

    df.columns = [c.strip() for c in df.columns]

    col_map = {
        "Account Number": "account_number",
        "Account Name": "account",
        "Symbol": "symbol",
        "Description": "description",
        "Cost Basis": "cost_basis",
        "Proceeds": "proceeds",
        "Short Term Gain/Loss": "short_term_gl",
        "Long Term Gain/Loss": "long_term_gl",
        "Total Term Gain/Loss": "total_gl",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    for col in ["cost_basis", "proceeds", "short_term_gl", "long_term_gl", "total_gl"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_dollar)

    df = df.dropna(subset=["symbol"])
    df = df[df["symbol"].str.strip() != ""]

    return df.reset_index(drop=True)
