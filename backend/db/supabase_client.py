"""
Centralized Supabase PostgreSQL client with environment validation
Falls back gracefully if credentials are missing
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Parse Supabase credentials from environment
# Supports standard Supabase environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD", "").strip() or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

# Extract host from URL if provided (https://xyz.supabase.co -> xyz.supabase.co)
SUPABASE_HOST = ""
if SUPABASE_URL:
    # Parse URL: https://project-ref.supabase.co
    if "://" in SUPABASE_URL:
        SUPABASE_HOST = SUPABASE_URL.split("://")[1]  # Remove https://
    else:
        SUPABASE_HOST = SUPABASE_URL

SUPABASE_USER = os.getenv("SUPABASE_USER", "postgres").strip()
SUPABASE_DB = os.getenv("SUPABASE_DB", "postgres").strip()

# Check for missing credentials
MISSING_VARS = []
if not SUPABASE_HOST:
    MISSING_VARS.append("SUPABASE_URL")
if not SUPABASE_PASSWORD:
    MISSING_VARS.append("SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_PASSWORD)")

if MISSING_VARS:
    print(f"⚠️ Supabase not configured: {', '.join(MISSING_VARS)}")
    print("ℹ️ To enable Supabase, add these to Vercel environment variables:")
    print("   SUPABASE_URL=https://your-project.supabase.co")
    print("   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key")
    SUPABASE_ENABLED = False
else:
    print(f"✅ Supabase client configured for {SUPABASE_HOST}")
    SUPABASE_ENABLED = True


class SupabaseClient:
    """Thread-safe Supabase PostgreSQL client"""
    
    @staticmethod
    def get_connection():
        """
        Get a new connection to Supabase PostgreSQL.
        Raises: psycopg2.Error if connection fails
        """
        if not SUPABASE_ENABLED:
            raise Exception("Supabase not configured - environment variables missing")
        
        try:
            conn = psycopg2.connect(
                host=SUPABASE_HOST,
                user=SUPABASE_USER,
                password=SUPABASE_PASSWORD,
                database=SUPABASE_DB,
                port=5432,
                sslmode="require",
                connect_timeout=10
            )
            return conn
        except psycopg2.OperationalError as e:
            print(f"❌ Supabase connection failed: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error connecting to Supabase: {e}")
            raise

    @staticmethod
    def execute_query(query: str, params: tuple = ()) -> list:
        """
        Execute a SELECT query and return results
        Args:
            query: SQL query string
            params: Query parameters tuple
        Returns:
            List of dicts (rows)
        Raises:
            psycopg2.Error if query fails
        """
        conn = SupabaseClient.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            result = [dict(row) for row in cur.fetchall()]
            cur.close()
            return result
        finally:
            conn.close()

    @staticmethod
    def execute_update(query: str, params: tuple = ()) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query
        Args:
            query: SQL query string
            params: Query parameters tuple
        Returns:
            Number of rows affected
        Raises:
            psycopg2.Error if query fails
        """
        conn = SupabaseClient.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            affected = cur.rowcount
            conn.commit()
            cur.close()
            return affected
        except Exception as e:
            conn.rollback()
            print(f"❌ Database update failed: {e}")
            raise
        finally:
            conn.close()


class SupabaseClient:
    """Thread-safe Supabase PostgreSQL client"""
    
    @staticmethod
    def get_connection():
        """
        Get a new connection to Supabase PostgreSQL.
        Raises: psycopg2.Error if connection fails
        """
        try:
            conn = psycopg2.connect(
                host=SUPABASE_HOST,
                user=SUPABASE_USER,
                password=SUPABASE_PASSWORD,
                database=SUPABASE_DB,
                port=5432,
                sslmode="require",
                connect_timeout=10
            )
            return conn
        except psycopg2.OperationalError as e:
            print(f"❌ Supabase connection failed: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error connecting to Supabase: {e}")
            raise

    @staticmethod
    def execute_query(query: str, params: tuple = ()) -> list:
        """
        Execute a SELECT query and return results
        Args:
            query: SQL query string
            params: Query parameters tuple
        Returns:
            List of dicts (rows)
        Raises:
            psycopg2.Error if query fails
        """
        conn = SupabaseClient.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            result = [dict(row) for row in cur.fetchall()]
            cur.close()
            return result
        finally:
            conn.close()

    @staticmethod
    def execute_update(query: str, params: tuple = ()) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query
        Args:
            query: SQL query string
            params: Query parameters tuple
        Returns:
            Number of rows affected
        Raises:
            psycopg2.Error if query fails
        """
        conn = SupabaseClient.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            affected = cur.rowcount
            conn.commit()
            cur.close()
            return affected
        except Exception as e:
            conn.rollback()
            print(f"❌ Database update failed: {e}")
            raise
        finally:
            conn.close()
