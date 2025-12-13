import math
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict

# Configure yfinance cache for Vercel
if os.environ.get("VERCEL"):
    cache_dir = Path("/tmp/py-yfinance")
    try:
        if not cache_dir.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ["YFINANCE_CACHE_DIR"] = str(cache_dir)
    except Exception as e:
        print(f"Failed to create yfinance cache dir: {e}")

from backend.db.database import (
    init_db,
    get_all_positions,
    insert_position,
    delete_position,
    get_cash,
    update_cash,
    get_sector_allocations,
    upsert_sector_allocation
)


import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


RISK_FREE_RATE = 0.0488  # fixed risk-free rate
MARKET_PROXY = "SPY"
ATR_WINDOW = 14
VAR_SIMULATIONS = 5000
VAR_CONFIDENCE = 0.95
IV_TENOR_DAYS = 30


class PositionIn(BaseModel):
    ticker: str = Field(..., description="Stock symbol")
    shares: float = Field(..., ge=0, description="Number of shares")
    price_bought: float = Field(..., ge=0, description="Entry price paid by the user")
    date_bought: Optional[str] = Field(None, description="YYYY-MM-DD")


class PositionOut(PositionIn):
    entry_atr: Optional[float] = None
    current_price: float = 0.0
    position_value: float = 0.0
    atr: Optional[float] = None
    beta: Optional[float] = None
    weight: Optional[float] = None
    var: Optional[float] = None
    iv: Optional[float] = None
    atr_change: Optional[float] = None
    pct_change: Optional[float] = None
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    
    # New fields
    value_paid: Optional[float] = None
    no_atrs: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    current_tp: Optional[float] = None
    current_sl: Optional[float] = None
    beta_weighted: Optional[float] = None
    expected_return: Optional[float] = None
    weighted_expected_return: Optional[float] = None
    holding_period: Optional[int] = None
    cap_formatted: Optional[str] = None
    
    error: Optional[str] = None


class RecalculateRequest(BaseModel):
    rows: List[PositionIn]


class RecalculateResponse(BaseModel):
    rows: List[PositionOut]
    market_sector_weights: Optional[Dict[str, float]] = None


# PositionDB no longer needs ID as ticker is PK
class PositionDB(PositionIn):
    pass


class CashUpdate(BaseModel):
    amount: float


class SectorAllocationUpdate(BaseModel):
    sector: str
    allocation: float


app = FastAPI(title="RiskSheet Backend", version="1.0.0")

@app.on_event("startup")
def startup():
    try:
        init_db()
    except Exception as e:
        print(f"Startup failed: {e}")
        # On Vercel, we might want to continue even if DB init fails, 
        # though functionality will be broken.
        pass


@app.get("/positions", response_model=List[PositionDB])
def read_positions():
    return get_all_positions()


@app.post("/positions", response_model=PositionDB)
def create_position(pos: PositionIn):
    try:
        ticker = pos.ticker.strip().upper()
        if not ticker:
            raise HTTPException(status_code=400, detail="Ticker is required")
        shares = float(pos.shares)
        price_bought = float(pos.price_bought)
        # Convert empty string date to None
        date_bought = pos.date_bought if pos.date_bought else None
        insert_position(ticker, shares, price_bought, date_bought)
        # Return the object with the cleaned date
        return PositionDB(
            ticker=ticker,
            shares=shares,
            price_bought=price_bought,
            date_bought=date_bought
        )
    except Exception as e:
        print(f"Error creating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/positions/{ticker}")
def delete_position_endpoint(ticker: str):
    delete_position(ticker.strip().upper())
    return {"ok": True}


@app.get("/cash", response_model=CashUpdate)
def read_cash():
    return {"amount": get_cash()}


@app.put("/cash", response_model=CashUpdate)
def update_cash_endpoint(cash: CashUpdate):
    update_cash(cash.amount)
    return cash


@app.get("/sector-allocations", response_model=Dict[str, float])
def read_sector_allocations():
    return get_sector_allocations()


@app.put("/sector-allocations")
def update_sector_allocation_endpoint(alloc: SectorAllocationUpdate):
    upsert_sector_allocation(alloc.sector, alloc.allocation)
    return {"ok": True}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def black_scholes_call_price(s: float, k: float, r: float, sigma: float, t: float) -> float:
    if s <= 0 or k <= 0 or sigma <= 0 or t <= 0:
        return 0.0
    d1 = (math.log(s / k) + (r + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    return s * norm_cdf(d1) - k * math.exp(-r * t) * norm_cdf(d2)


def estimate_implied_vol(spot: float, r: float, tenor_days: int, returns: np.ndarray) -> Optional[float]:
    if spot <= 0 or returns.size < 5:
        return None
    # Use realized volatility as the starting point and target an ATM call priced off that estimate.
    sigma_guess = float(np.std(returns) * math.sqrt(252))
    if sigma_guess <= 0:
        return None
    t = tenor_days / 365.0
    target_price = black_scholes_call_price(spot, spot, r, sigma_guess, t)
    if target_price <= 0:
        return None

    sigma = sigma_guess
    for _ in range(8):
        price = black_scholes_call_price(spot, spot, r, sigma, t)
        if price <= 0:
            break
        # Vega for ATM call
        d1 = (math.log(1) + (r + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))
        vega = spot * math.sqrt(t) * (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1**2)
        if vega <= 1e-8:
            break
        sigma -= (price - target_price) / vega
        if sigma <= 0:
            sigma = sigma_guess
            break
    return max(round(sigma, 4), 0.0)


def compute_beta(stock_returns: np.ndarray, market_returns: np.ndarray) -> Optional[float]:
    if stock_returns.size == 0 or market_returns.size == 0:
        return None
    # Align lengths
    min_len = min(len(stock_returns), len(market_returns))
    s_ret = stock_returns[-min_len:]
    m_ret = market_returns[-min_len:]
    
    covariance = np.cov(s_ret, m_ret)[0, 1]
    variance = np.var(m_ret)
    if variance == 0:
        return None
    return round(float(covariance / variance), 4)


def compute_var(position_value: float, returns: np.ndarray) -> Optional[float]:
    if returns.size < 2:
        return None
    # Monte Carlo VaR
    mu = np.mean(returns)
    sigma = np.std(returns)
    simulated_returns = np.random.normal(mu, sigma, VAR_SIMULATIONS)
    simulated_returns.sort()
    cutoff_index = int((1 - VAR_CONFIDENCE) * VAR_SIMULATIONS)
    var_percent = simulated_returns[cutoff_index]
    return round(abs(position_value * var_percent), 2)


def compute_atr_series(history):
    if history is None or history.empty:
        return None
    highs = history["High"]
    lows = history["Low"]
    closes = history["Close"]
    prev_closes = closes.shift(1)
    
    tr1 = highs - lows
    tr2 = (highs - prev_closes).abs()
    tr3 = (lows - prev_closes).abs()
    
    tr = np.maximum.reduce([tr1, tr2, tr3])
    # Convert to Series to use rolling
    tr_series = pd.Series(tr, index=history.index)
    atr_series = tr_series.rolling(window=ATR_WINDOW).mean()
    return atr_series


def fetch_ticker_data(ticker: str):
    ticker_obj = yf.Ticker(ticker)
    # Fetch max history to ensure we cover old purchase dates
    history = ticker_obj.history(period="max", auto_adjust=True)
    # Ensure timezone naive index for easier comparison
    if not history.empty:
        history.index = history.index.tz_localize(None)
    info = ticker_obj.info
    return history, info


def format_market_cap(val: float) -> str:
    if not val:
        return ""
    if val >= 1e12:
        return f"{val/1e12:.2f}T"
    if val >= 1e9:
        return f"{val/1e9:.2f}B"
    if val >= 1e6:
        return f"{val/1e6:.2f}M"
    return f"{val:.2f}"


def process_row(ticker: str, shares: float, price_bought: float, date_bought: Optional[str], market_returns: np.ndarray):
    ticker = ticker.upper()
    history, info = fetch_ticker_data(ticker)
    if history is None or history.empty:
        raise HTTPException(status_code=400, detail=f"No market data for {ticker}")
    closes = history["Close"]
    current_price = float(round(closes.iloc[-1], 4))
    returns = np.log(closes / closes.shift(1)).dropna().to_numpy()
    position_value = float(round(current_price * shares, 2))
    value_paid = float(round(price_bought * shares, 2))

    atr_series = compute_atr_series(history)
    current_atr = float(round(atr_series.iloc[-1], 4)) if atr_series is not None and not np.isnan(atr_series.iloc[-1]) else None
    
    entry_atr = None
    inferred_date = date_bought

    # Try to infer date from price if price_bought is provided
    if price_bought > 0:
        # Find rows where Low <= price_bought <= High
        mask = (history["Low"] <= price_bought) & (history["High"] >= price_bought)
        matches = history[mask]
        if not matches.empty:
            # Use the most recent match
            match_date = matches.index[-1]
            inferred_date = match_date.strftime("%Y-%m-%d")
        else:
            # Price not found in history
            raise ValueError(f"Price {price_bought} not found in history")
    
    holding_period = 0
    if inferred_date and atr_series is not None:
        try:
            dt = datetime.strptime(inferred_date, "%Y-%m-%d")
            holding_period = (datetime.now() - dt).days
            # Find the closest date in history (on or before)
            idx = history.index.get_indexer([dt], method='pad')[0]
            if idx != -1:
                val = atr_series.iloc[idx]
                if not np.isnan(val):
                    entry_atr = float(round(val, 4))
        except Exception:
            pass

    beta = compute_beta(returns, market_returns) if market_returns.size else None
    var = compute_var(position_value, returns)
    iv = estimate_implied_vol(current_price, RISK_FREE_RATE, IV_TENOR_DAYS, returns)

    atr_change = round(current_atr - entry_atr, 4) if current_atr is not None and entry_atr is not None else None
    pct_change = round((current_price - price_bought) / price_bought, 4) if price_bought > 0 else 0.0
    sector = info.get("sector", "Unknown")
    market_cap = info.get("marketCap")
    cap_formatted = format_market_cap(market_cap) if market_cap else None

    # New Calculations
    no_atrs = None
    if entry_atr and entry_atr > 0:
        no_atrs = round((current_price - price_bought) / entry_atr, 4)
    
    take_profit = None
    stop_loss = None
    current_tp = None
    current_sl = None
    if entry_atr:
        take_profit = round(price_bought + 2 * entry_atr, 2)
        stop_loss = round(price_bought - 2 * entry_atr, 2)
    
    if current_atr:
        current_tp = round(current_price + 2 * current_atr, 2)
        current_sl = round(current_price - 2 * current_atr, 2)

    # CAPM Expected Return
    # Rf + Beta * (Rm - Rf)
    # Estimate Rm from market_returns (annualized)
    expected_return = None
    if beta is not None and market_returns.size > 0:
        annual_market_return = np.mean(market_returns) * 252
        expected_return = round(RISK_FREE_RATE + beta * (annual_market_return - RISK_FREE_RATE), 6)

    return PositionOut(
        ticker=ticker,
        shares=shares,
        price_bought=price_bought,
        date_bought=inferred_date,
        entry_atr=entry_atr,
        current_price=current_price,
        position_value=position_value,
        atr=current_atr,
        beta=beta,
        weight=None,  # filled later after total value is known
        var=var,
        iv=iv,
        atr_change=atr_change,
        pct_change=pct_change,
        sector=sector,
        market_cap=market_cap,
        value_paid=value_paid,
        no_atrs=no_atrs,
        take_profit=take_profit,
        stop_loss=stop_loss,
        current_tp=current_tp,
        current_sl=current_sl,
        expected_return=expected_return,
        holding_period=holding_period,
        cap_formatted=cap_formatted
    )


def get_market_returns() -> np.ndarray:
    history, _ = fetch_ticker_data(MARKET_PROXY)
    if history is None or history.empty:
        return np.array([])
    closes = history["Close"]
    return np.log(closes / closes.shift(1)).dropna().to_numpy()


def get_market_sector_weights() -> Dict[str, float]:
    try:
        spy = yf.Ticker(MARKET_PROXY)
        # Try funds_data (newer yfinance)
        if hasattr(spy, 'funds_data') and spy.funds_data and spy.funds_data.sector_weightings:
            return spy.funds_data.sector_weightings
        
        # Fallback to info
        info = spy.info
        if 'sectorWeightings' in info:
            # Usually a list of dicts: [{'sector': '...', 'weight': ...}]
            sw = info['sectorWeightings']
            if isinstance(sw, list):
                return {item['sector']: item['weight'] for item in sw}
            elif isinstance(sw, dict):
                return sw
        
        return {}
    except Exception:
        return {}


@app.post("/recalculate", response_model=RecalculateResponse)
def recalculate(payload: RecalculateRequest):
    if not payload.rows:
        return RecalculateResponse(rows=[])

    market_returns = get_market_returns()
    market_sector_weights = get_market_sector_weights()

    processed = []
    for row in payload.rows:
        try:
            processed.append(process_row(row.ticker, row.shares, row.price_bought, row.date_bought, market_returns))
        except Exception as e:
            # Return row with error
            processed.append(PositionOut(
                ticker=row.ticker,
                shares=row.shares,
                price_bought=row.price_bought,
                date_bought=row.date_bought,
                error=str(e)
            ))

    total_value = sum(row.position_value for row in processed if row.position_value)
    for row in processed:
        row.weight = round(row.position_value / total_value, 4) if total_value else None
        if row.beta is not None and row.weight is not None:
            row.beta_weighted = round(row.beta * row.weight, 6)
        if row.expected_return is not None and row.weight is not None:
            row.weighted_expected_return = round(row.expected_return * row.weight, 6)

    return RecalculateResponse(rows=processed, market_sector_weights=market_sector_weights)


@app.get("/")
def root():
    return {"message": "RiskSheet Backend is running"}


base_dir = Path(__file__).resolve().parent
static_dir = (base_dir.parent / "frontend").resolve()
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
