import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# On Vercel (or read-only environments), use /tmp for SQLite
if os.environ.get("VERCEL"):
    DB_PATH = Path("/tmp") / "risksheet.db"
else:
    DB_PATH = BASE_DIR / "risksheet.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Keep the DB responsive to concurrent reads while writes occur
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Table 1: positions (user input only)
    ensure_positions_schema(conn)

    # Table 3: cash (single row)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cash (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            amount REAL NOT NULL
        );
    """)
    cur.execute("""
        INSERT OR IGNORE INTO cash (id, amount)
        VALUES (1, 0.0);
    """)

    # Tables 4 & 5: sector allocations
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sector_allocations (
            sector TEXT PRIMARY KEY,
            allocation REAL NOT NULL
        );
    """)

    conn.commit()
    conn.close()


def ensure_positions_schema(conn: sqlite3.Connection):
    """Create or migrate the positions table so ticker is the PK and date_bought exists."""
    cur = conn.execute("PRAGMA table_info(positions)")
    cols = cur.fetchall()

    # Table missing entirely
    if not cols:
        conn.execute("""
            CREATE TABLE positions (
                ticker TEXT PRIMARY KEY,
                shares REAL NOT NULL,
                price_bought REAL NOT NULL,
                date_bought TEXT
            );
        """)
        conn.commit()
        return

    col_names = {c["name"] for c in cols}
    has_ticker_pk = any(c["name"] == "ticker" and c["pk"] == 1 for c in cols)
    missing_cols = {"ticker", "shares", "price_bought", "date_bought"} - col_names

    # If schema is off, migrate while preserving data
    if missing_cols or not has_ticker_pk:
        conn.execute("ALTER TABLE positions RENAME TO positions_backup")
        conn.execute("""
            CREATE TABLE positions (
                ticker TEXT PRIMARY KEY,
                shares REAL NOT NULL,
                price_bought REAL NOT NULL,
                date_bought TEXT
            );
        """)
        # Copy what we can; fall back to defaults when missing
        conn.execute("""
            INSERT OR IGNORE INTO positions (ticker, shares, price_bought, date_bought)
            SELECT 
                UPPER(COALESCE(ticker, '')) AS ticker,
                COALESCE(shares, 0),
                COALESCE(price_bought, 0),
                date_bought
            FROM positions_backup
        """)
        conn.execute("DROP TABLE positions_backup")
        conn.commit()


# --- POSITIONS HELPERS ---

def get_all_positions():
    """Fetch all positions from the database."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT ticker, shares, price_bought, date_bought FROM positions ORDER BY ticker ASC")
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def insert_position(ticker: str, shares: float, price_bought: float, date_bought: str = None):
    """Insert or update a position (upsert on ticker)."""
    ticker = (ticker or "").strip().upper()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO positions (ticker, shares, price_bought, date_bought)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                shares = excluded.shares,
                price_bought = excluded.price_bought,
                date_bought = excluded.date_bought
            """,
            (ticker, shares, price_bought, date_bought)
        )
        conn.commit()
    finally:
        conn.close()


def delete_position(ticker: str):
    """Delete a position by ticker."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM positions WHERE ticker = ?", (ticker,))
        conn.commit()
    finally:
        conn.close()


def clear_positions():
    """Delete all positions."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM positions")
        conn.commit()
    finally:
        conn.close()


# --- CASH HELPERS ---

def get_cash():
    """Get the current cash amount."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT amount FROM cash WHERE id = 1")
        row = cur.fetchone()
        return row["amount"] if row else 0.0
    finally:
        conn.close()


def update_cash(amount: float):
    """Update the cash amount."""
    conn = get_connection()
    try:
        # Ensure single row by deleting all and inserting new
        conn.execute("DELETE FROM cash")
        conn.execute("INSERT INTO cash (id, amount) VALUES (1, ?)", (amount,))
        conn.commit()
    finally:
        conn.close()


# --- SECTOR ALLOCATION HELPERS ---

def get_sector_allocations():
    """Get all sector allocations."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT sector, allocation FROM sector_allocations")
        rows = cur.fetchall()
        return {row["sector"]: row["allocation"] for row in rows}
    finally:
        conn.close()


def upsert_sector_allocation(sector: str, allocation: float):
    """Insert or update a sector allocation."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO sector_allocations (sector, allocation) VALUES (?, ?) "
            "ON CONFLICT(sector) DO UPDATE SET allocation = excluded.allocation",
            (sector, allocation)
        )
        conn.commit()
    finally:
        conn.close()


def clear_sector_allocations():
    """Clear all sector allocations."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sector_allocations")
        conn.commit()
    finally:
        conn.close()
