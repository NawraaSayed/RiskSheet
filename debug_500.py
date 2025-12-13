from backend.db.database import insert_position, init_db, get_all_positions
import time

try:
    print("Initializing DB...")
    init_db()
    print("DB Initialized.")

    print("Inserting position...")
    # Simulate the call from main.py
    insert_position("AAPL", 10.0, 150.0, None)
    print("Inserted AAPL.")

    print("Inserting position with date...")
    insert_position("MSFT", 5.0, 300.0, "2023-01-01")
    print("Inserted MSFT.")

    print("Updating AAPL (Delete + Insert)...")
    insert_position("AAPL", 20.0, 155.0, None)
    print("Updated AAPL.")

    positions = get_all_positions()
    print("Positions:", positions)

except Exception as e:
    print("CAUGHT EXCEPTION:", e)
    import traceback
    traceback.print_exc()
