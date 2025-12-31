"""
Cloud database module for Vercel deployment.
Uses PostgreSQL on Vercel, SQLite locally.
"""
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

# Check if we're on Vercel or have PostgreSQL configured
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
IS_VERCEL = os.getenv("VERCEL") is not None

if IS_VERCEL and (SUPABASE_URL and SUPABASE_KEY):
    # Use PostgreSQL via Supabase
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    def get_connection():
        conn = psycopg2.connect(
            host=SUPABASE_URL.replace("https://", "").split(".supabase.co")[0] + ".supabase.co",
            database="postgres",
            user="postgres",
            password=SUPABASE_KEY,
            port=5432
        )
        return conn
    
    DATABASE_TYPE = "postgres"
else:
    # Use SQLite locally
    BASE_DIR = Path(__file__).resolve().parent
    DB_PATH = BASE_DIR / "risksheet.db"
    
    def get_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    
    DATABASE_TYPE = "sqlite"


def init_db():
    """Initialize database schema"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        if DATABASE_TYPE == "postgres":
            # PostgreSQL init
            cur.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    ticker TEXT PRIMARY KEY,
                    shares REAL NOT NULL,
                    price_bought REAL NOT NULL,
                    date_bought TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cash (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    amount REAL NOT NULL DEFAULT 0.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sector_allocations (
                    sector TEXT PRIMARY KEY,
                    allocation REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Ensure cash row exists
            cur.execute("INSERT INTO cash (id, amount) VALUES (1, 0.0) ON CONFLICT (id) DO NOTHING;")
            
        else:
            # SQLite init
            cur.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    ticker TEXT PRIMARY KEY,
                    shares REAL NOT NULL,
                    price_bought REAL NOT NULL,
                    date_bought TEXT
                );
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cash (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    amount REAL NOT NULL
                );
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sector_allocations (
                    sector TEXT PRIMARY KEY,
                    allocation REAL NOT NULL
                );
            """)
            
            # Ensure cash row exists
            cur.execute("INSERT OR IGNORE INTO cash (id, amount) VALUES (1, 0.0);")
        
        conn.commit()
        
    except Exception as e:
        print(f"Database init error: {e}")
        conn.rollback()
    finally:
        conn.close()


# --- POSITIONS HELPERS ---

def get_all_positions() -> List[Dict]:
    """Fetch all positions from the database."""
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT ticker, shares, price_bought, date_bought FROM positions ORDER BY ticker ASC;")
            return [dict(row) for row in cur.fetchall()]
        else:
            cur = conn.execute("SELECT ticker, shares, price_bought, date_bought FROM positions ORDER BY ticker ASC")
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def insert_position(ticker: str, shares: float, price_bought: float, date_bought: str = None):
    """Insert or update a position (upsert on ticker)."""
    ticker = (ticker or "").strip().upper()
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO positions (ticker, shares, price_bought, date_bought)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET
                    shares = EXCLUDED.shares,
                    price_bought = EXCLUDED.price_bought,
                    date_bought = EXCLUDED.date_bought;
            """, (ticker, shares, price_bought, date_bought))
        else:
            conn.execute("""
                INSERT INTO positions (ticker, shares, price_bought, date_bought)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    shares = excluded.shares,
                    price_bought = excluded.price_bought,
                    date_bought = excluded.date_bought
            """, (ticker, shares, price_bought, date_bought))
        
        conn.commit()
    finally:
        conn.close()


def delete_position(ticker: str):
    """Delete a position by ticker."""
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor()
            cur.execute("DELETE FROM positions WHERE ticker = %s;", (ticker,))
        else:
            conn.execute("DELETE FROM positions WHERE ticker = ?", (ticker,))
        
        conn.commit()
    finally:
        conn.close()


def clear_positions():
    """Delete all positions."""
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor()
            cur.execute("DELETE FROM positions;")
        else:
            conn.execute("DELETE FROM positions")
        
        conn.commit()
    finally:
        conn.close()


# --- CASH HELPERS ---

def get_cash() -> float:
    """Get the current cash amount."""
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT amount FROM cash WHERE id = 1;")
            row = cur.fetchone()
            return float(row["amount"]) if row else 0.0
        else:
            cur = conn.execute("SELECT amount FROM cash WHERE id = 1")
            row = cur.fetchone()
            return float(row["amount"]) if row else 0.0
    finally:
        conn.close()


def update_cash(amount: float):
    """Update the cash amount."""
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor()
            cur.execute("UPDATE cash SET amount = %s WHERE id = 1;", (amount,))
        else:
            conn.execute("UPDATE cash SET amount = ? WHERE id = 1", (amount,))
        
        conn.commit()
    finally:
        conn.close()


# --- SECTOR ALLOCATION HELPERS ---

def get_sector_allocations() -> Dict[str, float]:
    """Get all sector allocations."""
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT sector, allocation FROM sector_allocations;")
            return {row["sector"]: float(row["allocation"]) for row in cur.fetchall()}
        else:
            cur = conn.execute("SELECT sector, allocation FROM sector_allocations")
            return {dict(row)["sector"]: float(dict(row)["allocation"]) for row in cur.fetchall()}
    finally:
        conn.close()


def upsert_sector_allocation(sector: str, allocation: float):
    """Insert or update a sector allocation."""
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sector_allocations (sector, allocation)
                VALUES (%s, %s)
                ON CONFLICT (sector) DO UPDATE SET allocation = EXCLUDED.allocation;
            """, (sector, allocation))
        else:
            conn.execute("""
                INSERT INTO sector_allocations (sector, allocation) VALUES (?, ?)
                ON CONFLICT(sector) DO UPDATE SET allocation = excluded.allocation
            """, (sector, allocation))
        
        conn.commit()
    finally:
        conn.close()


def delete_sector_allocation(sector: str):
    """Delete a sector allocation."""
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor()
            cur.execute("DELETE FROM sector_allocations WHERE sector = %s;", (sector,))
        else:
            conn.execute("DELETE FROM sector_allocations WHERE sector = ?", (sector,))
        
        conn.commit()
    finally:
        conn.close()


def clear_sector_allocations():
    """Clear all sector allocations."""
    conn = get_connection()
    try:
        if DATABASE_TYPE == "postgres":
            cur = conn.cursor()
            cur.execute("DELETE FROM sector_allocations;")
        else:
            conn.execute("DELETE FROM sector_allocations")
        
        conn.commit()
    finally:
        conn.close()
