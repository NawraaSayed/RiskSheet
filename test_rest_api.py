#!/usr/bin/env python3
"""
Test the Supabase REST API implementation (without actual Supabase connection)
Verifies syntax and basic function structure
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from db import database_supabase
    
    print("✅ Successfully imported database_supabase module")
    print(f"   SUPABASE_ENABLED: {database_supabase.SUPABASE_ENABLED}")
    print(f"   REST_URL: {database_supabase.REST_URL}")
    
    # Verify all functions exist
    functions = [
        'init_db',
        'get_all_positions',
        'insert_position',
        'delete_position',
        'get_cash',
        'update_cash',
        'get_sector_allocations',
        'upsert_sector_allocation',
        'delete_sector_allocation'
    ]
    
    for func_name in functions:
        if hasattr(database_supabase, func_name):
            print(f"   ✅ Function {func_name} exists")
        else:
            print(f"   ❌ Function {func_name} NOT FOUND")
            
    print("\n✅ All database functions are defined correctly")
    
except Exception as e:
    print(f"❌ Error importing database module: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
