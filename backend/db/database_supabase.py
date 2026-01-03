"""
Supabase PostgreSQL database implementation
CRITICAL: NO SQLite fallback. Supabase is mandatory.
"""
from backend.db.supabase_client import SupabaseClient, SUPABASE_ENABLED
import psycopg2

# ❌ REMOVED: SQLite fallback
# If Supabase is not enabled, the application MUST FAIL FAST
# Do not silently downgrade to SQLite as this causes data loss
if not SUPABASE_ENABLED:
    print("❌ FATAL: Supabase is not configured. The application cannot run.")
    print("   Please ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.")
    raise RuntimeError("Supabase is required - SQLite fallback has been removed to prevent data loss")
else:
    def init_db():
        """
        Initialize database tables if they don't exist.
        Called once at startup - tables should already exist in Supabase.
        """
        try:
            conn = SupabaseClient.get_connection()
            cur = conn.cursor()
            
            # Verify tables exist by querying information_schema
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('positions', 'cash', 'sector_allocations')
            """)
            existing_tables = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
            
            required_tables = {'positions', 'cash', 'sector_allocations'}
            missing_tables = required_tables - set(existing_tables)
            
            if missing_tables:
                print(f"⚠️ Missing tables in Supabase: {missing_tables}")
                print("Please create these tables manually in Supabase SQL Editor")
                raise Exception(f"Missing tables: {missing_tables}")
            
            print(f"✅ Supabase database ready. Tables verified: {existing_tables}")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise


    def get_all_positions():
        """
        Fetch all positions from Supabase.
        Returns: List of dicts with keys: ticker, shares, price_bought, date_bought
        """
        try:
            rows = SupabaseClient.execute_query(
                "SELECT ticker, shares, price_bought, date_bought FROM positions ORDER BY ticker ASC"
            )
            return rows
        except psycopg2.Error as e:
            print(f"❌ Error fetching positions: {e}")
            raise Exception(f"Failed to fetch positions: {e}")


    def insert_position(ticker: str, shares: float, price_bought: float, date_bought: str = None):
        """
        Insert or update a position in Supabase.
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
            SupabaseClient.execute_update(
                """
                INSERT INTO positions (ticker, shares, price_bought, date_bought)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET
                    shares = EXCLUDED.shares,
                    price_bought = EXCLUDED.price_bought,
                    date_bought = EXCLUDED.date_bought
                """,
                (ticker, shares, price_bought, date_bought)
            )
            print(f"✅ Position saved: {ticker} ({shares} shares @ ${price_bought})")
        except psycopg2.Error as e:
            print(f"❌ Error inserting position {ticker}: {e}")
            raise Exception(f"Failed to save position: {e}")


    def delete_position(ticker: str):
        """
        Delete a position from Supabase.
        Args:
            ticker: Stock symbol to delete
        
        SAFETY: ALWAYS requires ticker parameter. Never deletes without WHERE clause.
        """
        ticker = (ticker or "").strip().upper()
        if not ticker:
            raise ValueError("❌ CRITICAL: Ticker cannot be empty - refusing DELETE")
        
        try:
            print(f"🗑️ [DELETE] Supabase position: {ticker}")
            affected = SupabaseClient.execute_update(
                "DELETE FROM positions WHERE ticker = %s",
                (ticker,)
            )
            if affected > 0:
                print(f"✅ Position deleted: {ticker}")
            else:
                print(f"⚠️ Position not found: {ticker}")
        except psycopg2.Error as e:
            print(f"❌ Error deleting position {ticker}: {e}")
            raise Exception(f"Failed to delete position: {e}")


    def get_cash() -> float:
        """
        Get current cash value from Supabase.
        Returns: Float amount
        """
        try:
            rows = SupabaseClient.execute_query("SELECT amount FROM cash WHERE id = 1")
            if rows and len(rows) > 0:
                return float(rows[0]["amount"])
            return 0.0
        except psycopg2.Error as e:
            print(f"❌ Error fetching cash: {e}")
            raise Exception(f"Failed to fetch cash: {e}")


    def update_cash(amount: float):
        """
        Update cash value in Supabase. SAFE: Uses INSERT...ON CONFLICT.
        Args:
            amount: New cash balance
        
        SAFETY: Never uses DELETE. Always preserves existing record.
        """
        try:
            print(f"💰 [UPDATE] Supabase cash: ${amount}")
            # SAFE: Use INSERT...ON CONFLICT instead of DELETE
            # This ensures we never truncate the cash table
            SupabaseClient.execute_update(
                "INSERT INTO cash (id, amount) VALUES (1, %s) ON CONFLICT (id) DO UPDATE SET amount = %s",
                (amount, amount)
            )
            print(f"✅ Cash updated: ${amount}")
        except psycopg2.Error as e:
            print(f"❌ Error updating cash: {e}")
            raise Exception(f"Failed to update cash: {e}")


    def get_sector_allocations() -> dict:
        """
        Get all sector allocations from Supabase.
        Returns: Dict with keys=sector names, values=allocation floats
        """
        try:
            rows = SupabaseClient.execute_query(
                "SELECT sector, allocation FROM sector_allocations"
            )
            return {row["sector"]: float(row["allocation"]) for row in rows}
        except psycopg2.Error as e:
            print(f"❌ Error fetching sector allocations: {e}")
            raise Exception(f"Failed to fetch sector allocations: {e}")


    def upsert_sector_allocation(sector: str, allocation: float):
        """
        Insert or update a sector allocation in Supabase.
        Args:
            sector: Sector name
            allocation: Allocation percentage/amount
        """
        sector = (sector or "").strip()
        if not sector:
            raise ValueError("Sector cannot be empty")
        
        try:
            SupabaseClient.execute_update(
                """
                INSERT INTO sector_allocations (sector, allocation) VALUES (%s, %s)
                ON CONFLICT (sector) DO UPDATE SET allocation = EXCLUDED.allocation
                """,
                (sector, allocation)
            )
            print(f"✅ Sector allocation saved: {sector} = {allocation}")
        except psycopg2.Error as e:
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
