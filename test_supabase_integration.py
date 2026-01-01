"""
Integration tests for Supabase PostgreSQL database
Tests that all CRUD operations actually persist to Supabase
"""
import os
import sys
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.db.database_supabase import (
    init_db,
    get_all_positions,
    insert_position,
    delete_position,
    get_cash,
    update_cash,
    get_sector_allocations,
    upsert_sector_allocation,
    delete_sector_allocation
)


def test_database_connection():
    """Test that Supabase connection works"""
    print("\n🧪 Testing Supabase connection...")
    try:
        init_db()
        print("✅ Supabase connection successful")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return False


def test_positions_crud():
    """Test positions CRUD operations"""
    print("\n🧪 Testing Positions CRUD...")
    test_ticker = f"TEST{uuid.uuid4().hex[:4].upper()}"
    
    try:
        # CREATE
        print(f"  Creating position {test_ticker}...")
        insert_position(test_ticker, 100.0, 50.0, "2024-01-01")
        
        # READ
        print(f"  Reading all positions...")
        positions = get_all_positions()
        test_pos = [p for p in positions if p["ticker"] == test_ticker]
        assert len(test_pos) > 0, f"Position {test_ticker} not found in database"
        assert test_pos[0]["shares"] == 100.0
        assert test_pos[0]["price_bought"] == 50.0
        print(f"  ✅ Position created and readable from Supabase")
        
        # UPDATE
        print(f"  Updating position {test_ticker}...")
        insert_position(test_ticker, 150.0, 55.0)
        positions = get_all_positions()
        test_pos = [p for p in positions if p["ticker"] == test_ticker]
        assert test_pos[0]["shares"] == 150.0, "Update failed"
        print(f"  ✅ Position updated in Supabase")
        
        # DELETE
        print(f"  Deleting position {test_ticker}...")
        delete_position(test_ticker)
        positions = get_all_positions()
        test_pos = [p for p in positions if p["ticker"] == test_ticker]
        assert len(test_pos) == 0, "Delete failed - position still in database"
        print(f"  ✅ Position deleted from Supabase")
        
        return True
    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Positions CRUD test failed: {e}")
        return False


def test_cash_operations():
    """Test cash balance operations"""
    print("\n🧪 Testing Cash Operations...")
    
    try:
        # UPDATE
        print("  Updating cash to $5000...")
        update_cash(5000.0)
        
        # READ
        cash = get_cash()
        assert cash == 5000.0, f"Cash value mismatch. Expected 5000.0, got {cash}"
        print(f"  ✅ Cash updated and readable from Supabase: ${cash}")
        
        # UPDATE AGAIN
        print("  Updating cash to $2500...")
        update_cash(2500.0)
        cash = get_cash()
        assert cash == 2500.0, f"Cash value mismatch. Expected 2500.0, got {cash}"
        print(f"  ✅ Cash updated again in Supabase: ${cash}")
        
        return True
    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Cash operations test failed: {e}")
        return False


def test_sector_allocations():
    """Test sector allocation CRUD operations"""
    print("\n🧪 Testing Sector Allocations...")
    test_sector = f"TEST_SECTOR_{uuid.uuid4().hex[:4].upper()}"
    
    try:
        # CREATE
        print(f"  Creating allocation for {test_sector}...")
        upsert_sector_allocation(test_sector, 0.25)
        
        # READ
        allocations = get_sector_allocations()
        assert test_sector in allocations, f"Sector {test_sector} not found"
        assert allocations[test_sector] == 0.25
        print(f"  ✅ Sector allocation created and readable from Supabase")
        
        # UPDATE
        print(f"  Updating {test_sector} allocation to 0.35...")
        upsert_sector_allocation(test_sector, 0.35)
        allocations = get_sector_allocations()
        assert allocations[test_sector] == 0.35, "Update failed"
        print(f"  ✅ Sector allocation updated in Supabase")
        
        # DELETE
        print(f"  Deleting {test_sector}...")
        delete_sector_allocation(test_sector)
        allocations = get_sector_allocations()
        assert test_sector not in allocations, "Delete failed"
        print(f"  ✅ Sector allocation deleted from Supabase")
        
        return True
    except AssertionError as e:
        print(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Sector allocations test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("SUPABASE INTEGRATION TEST SUITE")
    print("=" * 60)
    
    results = []
    
    results.append(("Connection", test_database_connection()))
    results.append(("Positions CRUD", test_positions_crud()))
    results.append(("Cash Operations", test_cash_operations()))
    results.append(("Sector Allocations", test_sector_allocations()))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Supabase integration is working!")
    else:
        print("❌ SOME TESTS FAILED - Check Supabase configuration")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
