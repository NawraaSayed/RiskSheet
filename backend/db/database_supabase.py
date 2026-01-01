"""
Supabase PostgreSQL database module
Creates tables automatically on first connection
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql

# Get Supabase credentials from environment
SUPABASE_HOST = os.getenv("SUPABASE_HOST", "")
SUPABASE_USER = os.getenv("SUPABASE_USER", "postgres")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
SUPABASE_DB = os.getenv("SUPABASE_DB", "postgres")

def get_connection():
    """Get a connection to Supabase PostgreSQL"""
    return psycopg2.connect(
        host=SUPABASE_HOST,
        user=SUPABASE_USER,
        password=SUPABASE_PASSWORD,
        database=SUPABASE_DB,
        port=5432,
        sslmode="require"
    )

def init_db():
    """Create tables if they don't exist"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Create positions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            ticker TEXT PRIMARY KEY,
            shares REAL NOT NULL,
            price_bought REAL NOT NULL,
            date_bought TEXT
        );
    """)
    
    # Create cash table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cash (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            amount REAL NOT NULL
        );
    """)
    
    # Create sector_allocations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sector_allocations (
            sector TEXT PRIMARY KEY,
            allocation REAL NOT NULL
        );
    """)
    
    # Initialize cash with default value
    cur.execute("""
        INSERT INTO cash (id, amount) VALUES (1, 0.0)
        ON CONFLICT (id) DO NOTHING;
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Supabase tables initialized")

def get_all_positions():
    """Get all positions"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT ticker, shares, price_bought, date_bought FROM positions ORDER BY ticker ASC")
    result = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return result

def insert_position(ticker: str, shares: float, price_bought: float, date_bought: str = None):
    """Insert or update a position"""
    ticker = (ticker or "").strip().upper()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO positions (ticker, shares, price_bought, date_bought)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE SET
            shares = EXCLUDED.shares,
            price_bought = EXCLUDED.price_bought,
            date_bought = EXCLUDED.date_bought;
    """, (ticker, shares, price_bought, date_bought))
    conn.commit()
    cur.close()
    conn.close()

def delete_position(ticker: str):
    """Delete a position"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM positions WHERE ticker = %s", (ticker,))
    conn.commit()
    cur.close()
    conn.close()

def get_cash() -> float:
    """Get cash value"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT amount FROM cash WHERE id = 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return float(row["amount"]) if row else 0.0

def update_cash(amount: float):
    """Update cash value"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE cash SET amount = %s WHERE id = 1", (amount,))
    conn.commit()
    cur.close()
    conn.close()

def get_sector_allocations():
    """Get all sector allocations"""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT sector, allocation FROM sector_allocations")
    result = {row["sector"]: float(row["allocation"]) for row in cur.fetchall()}
    cur.close()
    conn.close()
    return result

def upsert_sector_allocation(sector: str, allocation: float):
    """Insert or update sector allocation"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sector_allocations (sector, allocation) VALUES (%s, %s)
        ON CONFLICT (sector) DO UPDATE SET allocation = EXCLUDED.allocation;
    """, (sector, allocation))
    conn.commit()
    cur.close()
    conn.close()

def delete_sector_allocation(sector: str):
    """Delete sector allocation"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sector_allocations WHERE sector = %s", (sector,))
    conn.commit()
    cur.close()
    conn.close()
