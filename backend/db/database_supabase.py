"""
Supabase REST API database implementation
Uses REST API instead of direct PostgreSQL (fixes Vercel timeout issues)
"""
import os
import requests
import json
from typing import List, Dict, Any

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_PASSWORD", "").strip()

MISSING_VARS = []
if not SUPABASE_URL:
    MISSING_VARS.append("SUPABASE_URL")
if not SUPABASE_SERVICE_ROLE_KEY:
    MISSING_VARS.append("SUPABASE_SERVICE_ROLE_KEY")

if MISSING_VARS:
    print(f"⚠️ Supabase not configured: {', '.join(MISSING_VARS)}")
    SUPABASE_ENABLED = False
else:
    print(f"✅ Supabase REST API configured")
    SUPABASE_ENABLED = True

REST_URL = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ""
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Prefer": "return=representation"
}

# ❌ REMOVED: SQLite fallback
# Define stub functions that will be overridden if Supabase is enabled
def init_db():
    raise RuntimeError("""
❌ FATAL: Supabase is not configured. The application cannot run.
   Please ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.""")

def get_all_positions():
    raise RuntimeError("Supabase is not configured - cannot fetch positions")

def insert_position(*args, **kwargs):
    raise RuntimeError("Supabase is not configured - cannot insert position")

def delete_position(*args, **kwargs):
    raise RuntimeError("Supabase is not configured - cannot delete position")

def get_cash():
    raise RuntimeError("Supabase is not configured - cannot fetch cash")

def update_cash(*args, **kwargs):
    raise RuntimeError("Supabase is not configured - cannot update cash")

def get_sector_allocations():
    raise RuntimeError("Supabase is not configured - cannot fetch sector allocations")

def upsert_sector_allocation(*args, **kwargs):
    raise RuntimeError("Supabase is not configured - cannot upsert sector allocation")

def delete_sector_allocation(*args, **kwargs):
    raise RuntimeError("Supabase is not configured - cannot delete sector allocation")


# If Supabase IS configured, define real functions using REST API
if SUPABASE_ENABLED:
    def init_db():
        """
        Initialize database tables if they don't exist.
        Called once at startup - tables should already exist in Supabase.
        Uses REST API to verify tables exist.
        """
        try:
            # Test connection by fetching from positions table (will fail gracefully if not exists)
            response = requests.get(
                f"{REST_URL}/positions?select=count()",
                headers=HEADERS,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ Supabase database ready (REST API connection verified)")
            else:
                print(f"⚠️ Supabase REST API returned {response.status_code}: {response.text}")
                raise Exception(f"Failed to verify Supabase tables: {response.text}")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise


    def get_all_positions() -> List[Dict[str, Any]]:
        """
        Fetch all positions from Supabase using REST API.
        Returns: List of dicts with keys: ticker, shares, price_bought, date_bought
        """
        try:
            response = requests.get(
                f"{REST_URL}/positions",
                headers=HEADERS,
                params={"order": "ticker.asc"},
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error fetching positions: {response.status_code}")
                raise Exception(f"Failed to fetch positions: {response.text}")
        except requests.exceptions.Timeout:
            print(f"❌ Timeout fetching positions from REST API")
            raise Exception("Timeout fetching positions")
        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            raise Exception(f"Failed to fetch positions: {e}")


    def insert_position(ticker: str, shares: float, price_bought: float, date_bought: str = None):
        """
        Insert or update a position in Supabase using REST API (upsert).
        Args:
            ticker: Stock symbol (will be uppercased)
            shares: Number of shares
            price_bought: Entry price
            date_bought: ISO date string (optional)
        """
        ticker = (ticker or "").strip().upper()
        if not ticker:
            raise ValueError("Ticker cannot be empty")
        
        try:
            # Try to update first
            response = requests.patch(
                f"{REST_URL}/positions",
                headers=HEADERS,
                params={"ticker": f"eq.{ticker}"},
                json={
                    "shares": shares,
                    "price_bought": price_bought,
                    "date_bought": date_bought
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    print(f"✅ Position updated: {ticker} ({shares} shares @ ${price_bought})")
                    return
            
            # If no rows updated, insert new
            response = requests.post(
                f"{REST_URL}/positions",
                headers=HEADERS,
                json={
                    "ticker": ticker,
                    "shares": shares,
                    "price_bought": price_bought,
                    "date_bought": date_bought
                },
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Position saved: {ticker} ({shares} shares @ ${price_bought})")
            else:
                print(f"❌ Error inserting position {ticker}: {response.status_code}")
                raise Exception(f"Failed to save position: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout saving position to REST API")
            raise Exception("Timeout saving position")
        except Exception as e:
            print(f"❌ Error inserting position {ticker}: {e}")
            raise Exception(f"Failed to save position: {e}")


    def delete_position(ticker: str):
        """
        Delete a position from Supabase using REST API.
        Args:
            ticker: Stock symbol to delete
        
        SAFETY: ALWAYS requires ticker parameter. Never deletes without WHERE clause.
        """
        ticker = (ticker or "").strip().upper()
        if not ticker:
            raise ValueError("❌ CRITICAL: Ticker cannot be empty - refusing DELETE")
        
        try:
            print(f"🗑️ [DELETE] Supabase position: {ticker}")
            response = requests.delete(
                f"{REST_URL}/positions",
                headers=HEADERS,
                params={"ticker": f"eq.{ticker}"},
                timeout=5
            )
            
            if response.status_code in [200, 204]:
                print(f"✅ Position deleted: {ticker}")
            else:
                print(f"⚠️ Position not found or error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout deleting position from REST API")
            raise Exception("Timeout deleting position")
        except Exception as e:
            print(f"❌ Error deleting position {ticker}: {e}")
            raise Exception(f"Failed to delete position: {e}")


    def get_cash() -> float:
        """
        Get current cash value from Supabase using REST API.
        Returns: Float amount
        """
        try:
            response = requests.get(
                f"{REST_URL}/cash",
                headers=HEADERS,
                params={"id": "eq.1"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0].get("amount", 0))
                return 0.0
            else:
                print(f"❌ Error fetching cash: {response.status_code}")
                raise Exception(f"Failed to fetch cash: {response.text}")
        except requests.exceptions.Timeout:
            print(f"❌ Timeout fetching cash from REST API")
            raise Exception("Timeout fetching cash")
        except Exception as e:
            print(f"❌ Error fetching cash: {e}")
            raise Exception(f"Failed to fetch cash: {e}")


    def update_cash(amount: float):
        """
        Update cash value in Supabase using REST API. SAFE: Uses upsert pattern.
        Args:
            amount: New cash balance
        
        SAFETY: Never uses DELETE. Always preserves existing record.
        """
        try:
            print(f"💰 [UPDATE] Supabase cash: ${amount}")
            
            # Try to update first
            response = requests.patch(
                f"{REST_URL}/cash",
                headers=HEADERS,
                params={"id": "eq.1"},
                json={"amount": amount},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    print(f"✅ Cash updated: ${amount}")
                    return
            
            # If no rows updated, insert new
            response = requests.post(
                f"{REST_URL}/cash",
                headers=HEADERS,
                json={"id": 1, "amount": amount},
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Cash updated: ${amount}")
            else:
                print(f"❌ Error updating cash: {response.status_code}")
                raise Exception(f"Failed to update cash: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout updating cash on REST API")
            raise Exception("Timeout updating cash")
        except Exception as e:
            print(f"❌ Error updating cash: {e}")
            raise Exception(f"Failed to update cash: {e}")


    def get_sector_allocations() -> dict:
        """
        Get all sector allocations from Supabase using REST API.
        Returns: Dict with keys=sector names, values=allocation floats
        """
        try:
            response = requests.get(
                f"{REST_URL}/sector_allocations",
                headers=HEADERS,
                timeout=5
            )
            
            if response.status_code == 200:
                rows = response.json()
                return {row["sector"]: float(row["allocation"]) for row in rows}
            else:
                print(f"❌ Error fetching sector allocations: {response.status_code}")
                raise Exception(f"Failed to fetch sector allocations: {response.text}")
        except requests.exceptions.Timeout:
            print(f"❌ Timeout fetching sector allocations from REST API")
            raise Exception("Timeout fetching sector allocations")
        except Exception as e:
            print(f"❌ Error fetching sector allocations: {e}")
            raise Exception(f"Failed to fetch sector allocations: {e}")


    def upsert_sector_allocation(sector: str, allocation: float):
        """
        Insert or update a sector allocation in Supabase using REST API.
        Args:
            sector: Sector name
            allocation: Allocation percentage/amount
        """
        sector = (sector or "").strip()
        if not sector:
            raise ValueError("Sector cannot be empty")
        
        try:
            # Try to update first
            response = requests.patch(
                f"{REST_URL}/sector_allocations",
                headers=HEADERS,
                params={"sector": f"eq.{sector}"},
                json={"allocation": allocation},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    print(f"✅ Sector allocation saved: {sector} = {allocation}")
                    return
            
            # If no rows updated, insert new
            response = requests.post(
                f"{REST_URL}/sector_allocations",
                headers=HEADERS,
                json={"sector": sector, "allocation": allocation},
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Sector allocation saved: {sector} = {allocation}")
            else:
                print(f"❌ Error upserting sector {sector}: {response.status_code}")
                raise Exception(f"Failed to save sector allocation: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout upserting sector allocation on REST API")
            raise Exception("Timeout upserting sector allocation")
        except Exception as e:
            print(f"❌ Error upserting sector {sector}: {e}")
            raise Exception(f"Failed to save sector allocation: {e}")


    def delete_sector_allocation(sector: str):
        """
        ❌ DISABLED: This function is no longer used.
        Sector allocations are now managed via upsert() with values that can be set to 0.
        
        Reason: Deleting tables causes data loss. All data mutations must use UPSERT or UPDATE.
        
        Args:
            sector: Sector name to delete
        
        SAFETY: Returns silently without deleting. Use upsert_sector_allocation() instead.
        """
        sector = (sector or "").strip()
        if not sector:
            print("⚠️ WARNING: delete_sector_allocation() called but disabled. Use upsert_sector_allocation() instead.")
            return
        
        print(f"⚠️ WARNING: delete_sector_allocation() is disabled. Sector '{sector}' will NOT be deleted.")
        print(f"   Use upsert_sector_allocation('{sector}', 0) to set allocation to 0 instead.")
        # DO NOT DELETE - just return silently
