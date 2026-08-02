import logging
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self):
        self.database_url = settings.DATABASE_URL
        self._verify_connection()

    def _verify_connection(self):
        """Verify that the database is reachable on startup."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            logger.info("Database connection verified successfully.")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    @contextmanager
    def _get_connection(self):
        """Get a database connection with automatic cleanup."""
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, sql: str) -> dict:
        """Execute a SQL query and return results."""
        try:
            # Only allow SELECT queries for safety
            sql_stripped = sql.strip().upper()
            if not sql_stripped.startswith("SELECT"):
                return {
                    "error": "Only SELECT queries are allowed.",
                    "results": [],
                }

            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(sql)
                    rows = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]

                    return {
                        "columns": columns,
                        "results": [dict(row) for row in rows],
                        "row_count": len(rows),
                    }
        except Exception as e:
            logger.error(f"Query execution failed: {e} | SQL: {sql}")
            return {"error": str(e), "results": []}

    def get_schema(self) -> str:
        """Return the database schema for the LLM."""
        return """Table: orders
Columns:
- order_id (INTEGER): Unique order identifier
- customer (TEXT): Customer full name
- product (TEXT): Product name (SmartHub Lite, SmartHub Pro, SmartHub Enterprise)
- amount (NUMERIC): Order amount in USD
- status (TEXT): Order status (delivered, shipped, pending, cancelled)
- order_date (DATE): Order date in YYYY-MM-DD format

Note: The current date is 2026-06-15. Use this for any relative date calculations (e.g., "last month" = May 2026)."""

    def is_healthy(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False


# Singleton instance
_database_service = None


def get_database() -> DatabaseService:
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service
