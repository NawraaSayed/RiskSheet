"""
SQLite database for Vercel with polling sync
Data persists within a function invocation, and polling syncs across clients
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "risksheet.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS positions (ticker TEXT PRIMARY KEY, shares REAL NOT NULL, price_bought REAL NOT NULL, date_bought TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS cash (id INTEGER PRIMARY KEY CHECK (id = 1), amount REAL NOT NULL)")
    cur.execute("CREATE TABLE IF NOT EXISTS sector_allocations (sector TEXT PRIMARY KEY, allocation REAL NOT NULL)")
    cur.execute("INSERT OR IGNORE INTO cash (id, amount) VALUES (1, 0.0)")
    conn.commit()
    conn.close()

def get_all_positions():
    conn = get_connection()
    cur = conn.execute("SELECT ticker, shares, price_bought, date_bought FROM positions ORDER BY ticker ASC")
    result = [dict(row) for row in cur.fetchall()]
    conn.close()
    return result

def insert_position(ticker: str, shares: float, price_bought: float, date_bought: str = None):
    ticker = (ticker or "").strip().upper()
    conn = get_connection()
    conn.execute("""
        INSERT INTO positions (ticker, shares, price_bought, date_bought) VALUES (?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET shares = excluded.shares, price_bought = excluded.price_bought, date_bought = excluded.date_bought
    """, (ticker, shares, price_bought, date_bought))
    conn.commit()
    conn.close()

def delete_position(ticker: str):
    conn = get_connection()
    conn.execute("DELETE FROM positions WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()

def get_cash() -> float:
    conn = get_connection()
    cur = conn.execute("SELECT amount FROM cash WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return float(row["amount"]) if row else 0.0

def update_cash(amount: float):
    conn = get_connection()
    conn.execute("UPDATE cash SET amount = ? WHERE id = 1", (amount,))
    conn.commit()
    conn.close()

def get_sector_allocations():
    conn = get_connection()
    cur = conn.execute("SELECT sector, allocation FROM sector_allocations")
    result = {row["sector"]: float(row["allocation"]) for row in cur.fetchall()}
    conn.close()
    return result

def upsert_sector_allocation(sector: str, allocation: float):
    conn = get_connection()
    conn.execute("""
        INSERT INTO sector_allocations (sector, allocation) VALUES (?, ?)
        ON CONFLICT(sector) DO UPDATE SET allocation = excluded.allocation
    """, (sector, allocation))
    conn.commit()
    conn.close()

def delete_sector_allocation(sector: str):
    conn = get_connection()
    conn.execute("DELETE FROM sector_allocations WHERE sector = ?", (sector,))
    conn.commit()
    conn.close()


