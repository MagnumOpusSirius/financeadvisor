"""
Portfolio calculations: P&L per trade (FIFO matching), holding periods,
unrealized positions, and per-symbol summaries.
"""

import pandas as pd
import numpy as np
from collections import deque
from dataclasses import dataclass, field


@dataclass
class _Lot:
    """A single purchase lot used for FIFO matching."""
    date: pd.Timestamp
    quantity: float
    price: float
    amount: float          # actual cash out (including fees)
    account: str


def match_trades_fifo(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Match BUY lots to SELL lots using FIFO per (symbol, account).
    Returns a DataFrame of closed trades with P&L columns.

    Input: output of core.parser.get_trades()
    Output columns added:
        buy_date, buy_price, buy_amount, sell_date, sell_price, sell_amount,
        quantity_matched, holding_days, realized_pnl, pnl_pct, win
    """
    closed = []

    for (symbol, account), group in trades.groupby(["symbol", "account"]):
        # Sort by date, then BUY before SELL on the same date.
        # Fidelity CSVs are reverse-chronological, so after merging files
        # same-day rows can appear SELL-first; the secondary key fixes that.
        group = group.copy()
        group["_order"] = (group["action"] == "SELL").astype(int)
        group = group.sort_values(["date", "_order"], kind="stable")
        lot_queue: deque[_Lot] = deque()

        for _, row in group.iterrows():
            if row["action"] == "BUY":
                qty = abs(row["quantity"]) if not pd.isna(row["quantity"]) else 0
                lot_queue.append(_Lot(
                    date=row["date"],
                    quantity=qty,
                    price=row["price"] if not pd.isna(row["price"]) else 0,
                    amount=abs(row["amount"]) if not pd.isna(row["amount"]) else 0,
                    account=account,
                ))

            elif row["action"] == "SELL":
                sell_qty = abs(row["quantity"]) if not pd.isna(row["quantity"]) else 0
                sell_price = row["price"] if not pd.isna(row["price"]) else 0
                sell_amount = abs(row["amount"]) if not pd.isna(row["amount"]) else 0
                sell_date = row["date"]
                remaining_sell = sell_qty

                while remaining_sell > 1e-9 and lot_queue:
                    lot = lot_queue[0]
                    matched = min(lot.quantity, remaining_sell)
                    frac = matched / lot.quantity if lot.quantity > 0 else 0

                    buy_cost = lot.amount * frac
                    sell_proceeds = sell_amount * (matched / sell_qty) if sell_qty > 0 else 0
                    pnl = sell_proceeds - buy_cost

                    closed.append({
                        "symbol": symbol,
                        "account": account,
                        "buy_date": lot.date,
                        "buy_price": lot.price,
                        "buy_amount": buy_cost,
                        "sell_date": sell_date,
                        "sell_price": sell_price,
                        "sell_amount": sell_proceeds,
                        "quantity": matched,
                        "holding_days": (sell_date - lot.date).days,
                        "realized_pnl": pnl,
                        "pnl_pct": (pnl / buy_cost * 100) if buy_cost > 0 else 0,
                        "win": pnl > 0,
                    })

                    lot.quantity -= matched
                    lot.amount -= buy_cost
                    remaining_sell -= matched

                    if lot.quantity < 1e-9:
                        lot_queue.popleft()

    if not closed:
        return pd.DataFrame()

    return pd.DataFrame(closed).sort_values("sell_date").reset_index(drop=True)


def open_positions(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Compute currently open positions (shares bought but not yet sold).
    Returns per (symbol, account) with total shares held and average cost basis.
    """
    rows = []
    for (symbol, account), group in trades.groupby(["symbol", "account"]):
        group = group.sort_values("date")
        total_qty = 0.0
        total_cost = 0.0

        for _, row in group.iterrows():
            qty = abs(row["quantity"]) if not pd.isna(row["quantity"]) else 0
            amt = abs(row["amount"]) if not pd.isna(row["amount"]) else 0

            if row["action"] == "BUY":
                total_qty += qty
                total_cost += amt
            elif row["action"] == "SELL":
                if total_qty > 0:
                    cost_per_share = total_cost / total_qty
                    total_cost -= qty * cost_per_share
                    total_qty = max(0.0, total_qty - qty)

        if total_qty > 1e-6:
            rows.append({
                "symbol": symbol,
                "account": account,
                "shares_held": total_qty,
                "avg_cost_basis": total_cost / total_qty if total_qty > 0 else 0,
                "total_cost": total_cost,
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def symbol_summary(closed_trades: pd.DataFrame, open_pos: pd.DataFrame) -> pd.DataFrame:
    """
    Per-symbol summary: total realized P&L, win rate, trade count, avg holding.
    """
    if closed_trades.empty:
        return pd.DataFrame()

    grp = closed_trades.groupby("symbol").agg(
        trade_count=("realized_pnl", "count"),
        total_realized_pnl=("realized_pnl", "sum"),
        win_count=("win", "sum"),
        avg_pnl_pct=("pnl_pct", "mean"),
        avg_holding_days=("holding_days", "mean"),
        total_invested=("buy_amount", "sum"),
        total_proceeds=("sell_amount", "sum"),
    ).reset_index()

    grp["win_rate"] = grp["win_count"] / grp["trade_count"]
    grp["overall_return_pct"] = (
        (grp["total_proceeds"] - grp["total_invested"]) / grp["total_invested"] * 100
    )

    return grp.sort_values("total_realized_pnl", ascending=False)


def unmatched_sells(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Find SELL transactions that had no matching BUY in the uploaded files.

    This happens when the user exports quarterly CSVs and the buy occurred in
    a previous quarter's file that wasn't uploaded.  These trades are silently
    skipped by match_trades_fifo, which causes the realized P&L to be
    understated.

    Returns a DataFrame with one row per orphaned sell event, including the
    dollar value of proceeds that could not be attributed to a cost basis.
    """
    rows = []

    for (symbol, account), group in trades.groupby(["symbol", "account"]):
        group = group.copy()
        group["_order"] = (group["action"] == "SELL").astype(int)
        group = group.sort_values(["date", "_order"], kind="stable")
        inventory = 0.0

        for _, row in group.iterrows():
            qty = abs(row["quantity"]) if not pd.isna(row["quantity"]) else 0
            amount = abs(row["amount"]) if not pd.isna(row["amount"]) else 0

            if row["action"] == "BUY":
                inventory += qty
            elif row["action"] == "SELL":
                if qty > inventory + 1e-6:
                    shortfall = qty - max(0.0, inventory)
                    rows.append({
                        "date": row["date"],
                        "symbol": symbol,
                        "account": account,
                        "sell_qty": qty,
                        "matched_qty": max(0.0, inventory),
                        "unmatched_qty": shortfall,
                        "unmatched_proceeds": amount * (shortfall / qty) if qty > 0 else 0,
                    })
                    inventory = 0.0
                else:
                    inventory = max(0.0, inventory - qty)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def cumulative_pnl_series(closed_trades: pd.DataFrame) -> pd.Series:
    """Return a daily cumulative realized P&L series (indexed by sell_date)."""
    if closed_trades.empty:
        return pd.Series(dtype=float)
    daily = closed_trades.groupby("sell_date")["realized_pnl"].sum()
    return daily.cumsum()


def total_deposited(transfers: pd.DataFrame) -> float:
    """Sum of all Electronic Funds Transfer Received rows (cash in)."""
    if transfers.empty:
        return 0.0
    return transfers["amount"].sum()
