"""
Supabase PostgreSQL database module for Vercel deployment
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Supabase connection details
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_connection():
    """Connect to Supabase PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=SUPABASE_URL,
            database="postgres",
            user="postgres",
            password=SUPABASE_KEY,
            port=5432,
            sslmode="require"
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def init_db():
    """Initialize database schema"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Tables are created manually in Supabase dashboard
        print("Database connection verified")
        conn.commit()
    except Exception as e:
        print(f"Database init error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def get_all_positions():
    """Fetch all positions"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT ticker, shares, price_bought, date_bought FROM positions ORDER BY ticker ASC")
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        cur.close()
        conn.close()

def insert_position(ticker: str, shares: float, price_bought: float, date_bought: str = None):
    """Insert or update a position"""
    ticker = (ticker or "").strip().upper()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO positions (ticker, shares, price_bought, date_bought)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (ticker) DO UPDATE SET
                shares = EXCLUDED.shares,
                price_bought = EXCLUDED.price_bought,
                date_bought = EXCLUDED.date_bought
        """, (ticker, shares, price_bought, date_bought))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def delete_position(ticker: str):
    """Delete a position"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM positions WHERE ticker = %s", (ticker,))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def get_cash() -> float:
    """Get current cash amount"""
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
    """Update cash amount"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE cash SET amount = %s WHERE id = 1", (amount,))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def get_sector_allocations():
    """Get all sector allocations"""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT sector, allocation FROM sector_allocations")
        rows = cur.fetchall()
        return {row["sector"]: float(row["allocation"]) for row in rows}
    finally:
        cur.close()
        conn.close()

def upsert_sector_allocation(sector: str, allocation: float):
    """Insert or update sector allocation"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sector_allocations (sector, allocation)
            VALUES (%s, %s)
            ON CONFLICT (sector) DO UPDATE SET allocation = EXCLUDED.allocation
        """, (sector, allocation))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def delete_sector_allocation(sector: str):
    """Delete a sector allocation"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM sector_allocations WHERE sector = %s", (sector,))
        conn.commit()
    finally:
        cur.close()
        conn.close()
