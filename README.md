# 📈 Finance Advisor

A personal portfolio analytics dashboard for Fidelity brokerage accounts. Upload your account history CSVs and get instant, deep insight into your trading performance — FIFO P&L, risk metrics, candlestick charts with your own buy/sell markers, and more.

> **Live Demo →** [Try it on Streamlit Cloud](https://your-app.streamlit.app) *(update link after deployment)*

---

## Screenshots

> Add screenshots after first run: `docs/screenshots/overview.png`, `trades.png`, `market.png`

| Overview | Trades | Market |
|----------|--------|--------|
| ![Overview](docs/screenshots/overview.png) | ![Trades](docs/screenshots/trades.png) | ![Market](docs/screenshots/market.png) |

---

## Features

### 📊 Overview Dashboard
- **Realized P&L** computed with FIFO cost basis matching across all uploaded files
- **Win rate**, **Profit Factor**, **Avg Win/Loss Ratio**, **Sharpe Ratio**, **Max Drawdown**
- **Risk Score** (0–10) based on leveraged ETF exposure, holding periods, and loss rate
- **Cumulative P&L chart** (Plotly, interactive)
- **Per-symbol breakdown** — bar chart + table with trade count, win rate, avg holding days
- **Holding period distribution** pie chart (Intraday → 3+ months)
- **Live open positions** enriched with current prices and unrealized P&L via yfinance
- **CUSIP / employer-plan account detection** — automatically excludes 401k/payroll rows from P&L
- **Fidelity realized gains validation** — upload the official gains CSV to cross-check FIFO calculations
- **Orphaned sell detection** — warns when sells have no matching buy in uploaded history

### 🔍 Trade History & P&L
- Every closed trade matched via FIFO, showing buy date, sell date, price, quantity, and P&L
- Color-coded P&L (green/red), holding days, and win/loss flag
- **Scatter plot**: P&L per trade over time, colored by symbol
- **Histogram**: P&L distribution across all trades
- **Scatter**: Holding period vs P&L (bubble size = position size)
- Sidebar filters: symbol, account, outcome (Win/Loss), date range
- **CSV export** of filtered trades

### 📈 Market Context & Charts
- **Live candlestick charts** (OHLC via yfinance) with your actual buy/sell markers overlaid
- Technical indicators: **MA50**, **MA200**, **Bollinger Bands**, **RSI (14)**, **MACD**
- **Technical state table** — RSI, MACD, and MA context at the time of each of your trades
- **Recent news feed** per ticker (via yfinance)
- Configurable lookback: 3 months → All time

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI framework | [Streamlit](https://streamlit.io) |
| Data / numerics | Pandas, NumPy |
| Charts | [Plotly](https://plotly.com/python/) |
| Market data | [yfinance](https://github.com/ranaroussi/yfinance) |
| ML / stats | scikit-learn, SciPy |
| Language | Python 3.10+ |

---

## Project Structure

```
financeadvisor/
├── app.py                  # Landing page (entry point)
├── pages/
│   ├── 1_Overview.py       # Dashboard + key metrics
│   ├── 2_Trades.py         # Closed trade log
│   └── 3_Market.py         # Candlestick charts
├── core/
│   ├── parser.py           # Fidelity CSV parser (handles preamble, footers, CUSIPs)
│   ├── portfolio.py        # FIFO matching, open positions, symbol summaries
│   └── metrics.py          # Sharpe, drawdown, win rate, risk score, etc.
├── market/
│   └── fetcher.py          # yfinance wrapper (price history, indicators, news)
├── data/
│   └── demo_generator.py   # Synthetic demo data (no real data needed)
├── styles.py               # Shared CSS injection
├── .streamlit/
│   └── config.toml         # Theme (dark, teal accent)
└── requirements.txt
```

---

## Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/MagnumOpusSirius/financeadvisor.git
cd financeadvisor

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Usage

### With your own Fidelity data
1. Log in to Fidelity → **Accounts & Trade → Account History → Download**
2. Export one or more quarterly CSV files
3. Upload them in the **Overview** page sidebar
4. All pages share the uploaded data automatically

> Your data is processed entirely in-session — nothing is stored or transmitted.

### Demo mode (no upload needed)
Click **"Try Demo"** on the landing page to load synthetic trade data and explore all features immediately.

---

## Deployment (Streamlit Cloud)

1. Push this repo to GitHub (public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo, branch `main`, and entry point `app.py`
4. Click **Deploy** — Streamlit Cloud installs `requirements.txt` automatically

---

## How FIFO Matching Works

Each `(symbol, account)` pair maintains an ordered queue of buy lots. When a sell arrives, it is matched against the oldest lots first:

```
Buy  NVDA ×10 @ $155  →  lot queue: [10 shares @ $155]
Buy  NVDA ×5  @ $280  →  lot queue: [10 @ $155, 5 @ $280]
Sell NVDA ×8  @ $395  →  matches 8 from first lot
                          P&L = 8×$395 − 8×$155 = +$1,920
                          remaining: [2 @ $155, 5 @ $280]
```

Proceeds are prorated when a sell partially consumes a lot, ensuring correct cost-basis allocation across partial fills.

---

## Known Limitations

- **Incomplete history**: If a stock was bought before your earliest uploaded file, the matching buy won't exist and P&L will be understated. The app warns you about these orphaned sells.
- **Options / futures**: Not supported — only equity buy/sell rows are analyzed.
- **Multi-currency**: All amounts assumed to be USD.
- **Fidelity-specific**: The CSV parser is built for Fidelity's export format.
