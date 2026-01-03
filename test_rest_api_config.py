#!/usr/bin/env python3
"""
Test Supabase REST API implementation
This test would work if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set
"""
import os
import sys
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from db import database_supabase

def test_rest_api_setup():
    """Test that REST API is properly configured"""
    
    print("=" * 60)
    print("SUPABASE REST API CONFIGURATION TEST")
    print("=" * 60)
    
    # Check environment variables
    print("\n1. Environment Variables:")
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_PASSWORD", "").strip()
    
    if supabase_url:
        print(f"   ✅ SUPABASE_URL set: {supabase_url}")
    else:
        print(f"   ❌ SUPABASE_URL not set")
    
    if service_role_key:
        masked_key = service_role_key[:10] + "..." + service_role_key[-5:]
        print(f"   ✅ SUPABASE_SERVICE_ROLE_KEY set: {masked_key}")
    else:
        print(f"   ❌ SUPABASE_SERVICE_ROLE_KEY not set")
    
    # Check module configuration
    print("\n2. Module Configuration:")
    print(f"   SUPABASE_ENABLED: {database_supabase.SUPABASE_ENABLED}")
    print(f"   REST_URL: {database_supabase.REST_URL}")
    
    if database_supabase.SUPABASE_ENABLED:
        print(f"   ✅ REST API is enabled")
        print(f"   Headers configured: {bool(database_supabase.HEADERS)}")
    else:
        print(f"   ⚠️  REST API is disabled (missing environment variables)")
    
    # Check function definitions
    print("\n3. Database Functions:")
    functions = {
        'init_db': 'Initialize database',
        'get_all_positions': 'Fetch all positions',
        'insert_position': 'Insert or update position',
        'delete_position': 'Delete position',
        'get_cash': 'Get cash balance',
        'update_cash': 'Update cash balance',
        'get_sector_allocations': 'Get sector allocations',
        'upsert_sector_allocation': 'Insert or update sector allocation',
        'delete_sector_allocation': 'Delete sector (disabled)',
    }
    
    all_present = True
    for func_name, description in functions.items():
        if hasattr(database_supabase, func_name):
            func = getattr(database_supabase, func_name)
            print(f"   ✅ {func_name:30s} - {description}")
        else:
            print(f"   ❌ {func_name:30s} - MISSING")
            all_present = False
    
    print("\n" + "=" * 60)
    if all_present and database_supabase.SUPABASE_ENABLED:
        print("✅ REST API is fully configured and ready for use")
    elif all_present:
        print("⚠️  REST API is configured but environment variables are missing")
        print("   Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to enable")
    else:
        print("❌ Some functions are missing - check implementation")
    print("=" * 60)

if __name__ == "__main__":
    test_rest_api_setup()
