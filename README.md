# RiskSheet (Locked One-Page Tracker)

Single-page Handsontable UI backed by FastAPI. Users can only edit **Ticker**, **Shares**, and **Price Bought**; all other cells are read-only and computed server-side.

## Quick start

You can simply run the `run.bat` file (on Windows) to install dependencies and start the server.

Or manually:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/` to load the sheet.

## What it does
- Frontend: Handsontable with locked structure; add/remove rows; automatic + manual recalc; IndexedDB persistence of editable fields only.
- Backend: `/recalculate` fetches market data via `yfinance`, computes ATR, beta vs SPY, position value, portfolio weights, Monte Carlo VaR, and a Black-Scholes implied-vol estimate (ATM, 30-day). Risk-free rate fixed at **4.88%**.

## Notes
- Network access is required for `yfinance` price/history downloads.
- All financial logic is in the backend; frontend never computes derived fields.
