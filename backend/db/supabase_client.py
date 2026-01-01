"""
Centralized Supabase PostgreSQL client with environment validation
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Validate environment variables at module load time
SUPABASE_HOST = os.getenv("SUPABASE_HOST", "").strip()
SUPABASE_USER = os.getenv("SUPABASE_USER", "postgres").strip()
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD", "").strip()
SUPABASE_DB = os.getenv("SUPABASE_DB", "postgres").strip()

# Check for missing credentials
MISSING_VARS = []
if not SUPABASE_HOST:
    MISSING_VARS.append("SUPABASE_HOST")
if not SUPABASE_PASSWORD:
    MISSING_VARS.append("SUPABASE_PASSWORD")

if MISSING_VARS:
    print(f"❌ FATAL: Missing Supabase environment variables: {', '.join(MISSING_VARS)}")
    print("Please set these in your Vercel environment: SUPABASE_HOST, SUPABASE_PASSWORD")
    raise EnvironmentError(f"Missing Supabase config: {', '.join(MISSING_VARS)}")

print(f"✅ Supabase client configured for {SUPABASE_HOST}")


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
