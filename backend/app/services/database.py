import sqlite3
import pandas as pd
from pathlib import Path

from app.config import settings


class DatabaseService:
    def __init__(self):
        self.db_path = settings.DATABASE_PATH
        self._initialize()

    def _initialize(self):
        """Create SQLite database from CSV if it doesn't exist."""
        db_path = Path(self.db_path)

        if not db_path.exists():
            self._build_database()

    def _build_database(self):
        """Build SQLite database from orders CSV."""
        csv_path = Path("data/orders.csv")

        if not csv_path.exists():
            raise FileNotFoundError(f"Orders CSV not found: {csv_path}")

        df = pd.read_csv(csv_path)

        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(db_path))
        df.to_sql("orders", conn, if_exists="replace", index=False)
        conn.close()

    def execute_query(self, sql: str) -> dict:
        """Execute a SQL query and return results."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Only allow SELECT queries for safety
            sql_stripped = sql.strip().upper()
            if not sql_stripped.startswith("SELECT"):
                return {
                    "error": "Only SELECT queries are allowed.",
                    "results": [],
                }

            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            return {
                "columns": columns,
                "results": [dict(zip(columns, row)) for row in rows],
                "row_count": len(rows),
            }
        except Exception as e:
            return {"error": str(e), "results": []}
        finally:
            conn.close()

    def get_schema(self) -> str:
        """Return the database schema for the LLM."""
        return """Table: orders
Columns:
- order_id (INTEGER): Unique order identifier
- customer (TEXT): Customer full name
- product (TEXT): Product name (SmartHub Lite, SmartHub Pro, SmartHub Enterprise)
- amount (REAL): Order amount in USD
- status (TEXT): Order status (delivered, shipped, pending, cancelled)
- order_date (TEXT): Order date in YYYY-MM-DD format

Note: The current date is 2026-06-15. Use this for any relative date calculations (e.g., "last month" = May 2026)."""


# Singleton instance
_database_service = None


def get_database() -> DatabaseService:
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service
