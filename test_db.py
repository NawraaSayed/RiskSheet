from backend.db.database_supabase import insert_position, get_all_positions, init_db

try:
    print("Initializing DB...")
    init_db()
    print("Inserting position...")
    insert_position("TEST", 10, 100, "2023-01-01")
    print("Position inserted.")
    positions = get_all_positions()
    print("Positions:", positions)
except Exception as e:
    print("Error:", e)
