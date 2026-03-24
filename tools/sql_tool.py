
import sqlite3
import logging
import re
from typing import Any
from pydantic import BaseModel, Field
from tools.base import BaseTool
from agent.schemas import UserRole
from config.settings import settings

logger = logging.getLogger(__name__)

# Dangerous SQL keywords that could modify data
BLOCKED_KEYWORDS = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]


class SQLTool(BaseTool):
    """
    Executes read-only SQL queries against the supply chain database.

    The planner writes the SQL, this tool runs it safely.
    """

    name = "sql_query"
    description = (
        "Execute a read-only SQL query against the supply chain database. "
        "Available tables: orders, inventory, shipments, quality_holds. "
        "Use this to look up order details, inventory levels, shipment tracking, "
        "and quality hold information. "
        "Arguments: query (str) - A valid SQLite SELECT query."
    )
    required_role = UserRole.ANALYST  # Viewers can't query the database

    class Args(BaseModel):
        query: str = Field(min_length=1, description="Read-only SQLite SELECT query")

    args_model = Args

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.database_path

    def execute(self, query: str = "", **kwargs) -> Any:
        """
        Execute a SQL query and return results.

        Args:
            query: SQL SELECT query to execute

        Returns:
            List of dicts, where each dict is a row with column names as keys

        Raises:
            ValueError: If the query contains write operations
            sqlite3.Error: If the query is invalid SQL
        """
        if not query:
            return "Error: No query provided."

        # --- Security check: block write operations ---
        # Match SQL keywords as full words only so columns like `created_at`
        # do not falsely trigger `CREATE` blocking.
        query_upper = query.upper().strip()
        for keyword in BLOCKED_KEYWORDS:
            if re.search(rf"\b{keyword}\b", query_upper):
                msg = f"Blocked: write operation '{keyword}' not allowed. This tool is read-only."
                logger.warning(msg)
                raise ValueError(msg)

        logger.info(f"Executing SQL: {query}")

        try:
            # Connect in read-only mode
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row  # Returns dict-like rows
            cursor = conn.cursor()

            cursor.execute(query)
            rows = cursor.fetchmany(100)  # Cap at 100 rows to avoid huge outputs

            # Convert sqlite3.Row objects to plain dicts
            results = [dict(row) for row in rows]

            conn.close()

            if not results:
                return "No results found."

            logger.info(f"Query returned {len(results)} rows")
            return results

        except sqlite3.Error as e:
            error_msg = f"SQL Error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

