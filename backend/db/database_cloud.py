"""
Supabase PostgreSQL database module with SQLite fallback
"""
import os
import sqlite3
from pathlib import Path

# Try PostgreSQL first, fall back to SQLite
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
USE_POSTGRES = False

if SUPABASE_URL and SUPABASE_KEY:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Test connection
        test_conn = psycopg2.connect(
            host=SUPABASE_URL,
            database="postgres",
            user="postgres",
            password=SUPABASE_KEY,
            port=5432,
            sslmode="require",
            connect_timeout=5
        )
        test_conn.close()
        USE_POSTGRES = True
        print("✅ Using Supabase PostgreSQL")
    except Exception as e:
        print(f"⚠️ Supabase connection failed: {e}, using SQLite fallback")

if USE_POSTGRES:
    # PostgreSQL functions
    def get_connection():
        return psycopg2.connect(
            host=SUPABASE_URL,
            database="postgres",
            user="postgres",
            password=SUPABASE_KEY,
            port=5432,
            sslmode="require"
        )
    
    def init_db():
        """Tables should be created manually in Supabase"""
        print("Using Supabase - tables should exist")
    
    def get_all_positions():
        conn = get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT ticker, shares, price_bought, date_bought FROM positions ORDER BY ticker ASC")
            return [dict(row) for row in cur.fetchall()]
        finally:
            cur.close()
            conn.close()
    
    def insert_position(ticker: str, shares: float, price_bought: float, date_bought: str = None):
        ticker = (ticker or "").strip().upper()
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO positions (ticker, shares, price_bought, date_bought)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET
                    shares = EXCLUDED.shares, price_bought = EXCLUDED.price_bought, date_bought = EXCLUDED.date_bought
            """, (ticker, shares, price_bought, date_bought))
            conn.commit()
        finally:
            cur.close()
            conn.close()
    
    def delete_position(ticker: str):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM positions WHERE ticker = %s", (ticker,))
            conn.commit()
        finally:
            cur.close()
            conn.close()
    
    def get_cash() -> float:
        conn = get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT amount FROM cash WHERE id = 1")
            row = cur.fetchone()
            return float(row["amount"]) if row else 0.0
        finally:
            cur.close()
            conn.close()
    
    def update_cash(amount: float):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE cash SET amount = %s WHERE id = 1", (amount,))
            conn.commit()
        finally:
            cur.close()
            conn.close()
    
    def get_sector_allocations():
        conn = get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT sector, allocation FROM sector_allocations")
            return {row["sector"]: float(row["allocation"]) for row in cur.fetchall()}
        finally:
            cur.close()
            conn.close()
    
    def upsert_sector_allocation(sector: str, allocation: float):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sector_allocations (sector, allocation) VALUES (%s, %s)
                ON CONFLICT (sector) DO UPDATE SET allocation = EXCLUDED.allocation
            """, (sector, allocation))
            conn.commit()
        finally:
            cur.close()
            conn.close()
    
    def delete_sector_allocation(sector: str):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM sector_allocations WHERE sector = %s", (sector,))
            conn.commit()
        finally:
            cur.close()
            conn.close()

else:
    # SQLite functions (fallback)
    BASE_DIR = Path(__file__).resolve().parent
    DB_PATH = BASE_DIR / "risksheet.db"
    
    print(f"✅ Using SQLite at {DB_PATH}")
    
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

