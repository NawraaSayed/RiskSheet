import sqlite3
from pathlib import Path

BASE_DIR = Path("backend/db").resolve()
DB_PATH = BASE_DIR / "risksheet.db"

def check_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(positions)")
    columns = cursor.fetchall()
    print("Columns in positions table:")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_schema()
