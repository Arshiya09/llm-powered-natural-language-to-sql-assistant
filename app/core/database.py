"""
Database connection pool and execution manager with read-only restrictions.
Supports PostgreSQL with seamless local SQLite offline fallback.
"""

import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from app.core.config import settings

SQLITE_DB_PATH = Path(__file__).resolve().parent.parent.parent / "smart_meter_dw.db"


class DatabaseManager:
    def __init__(self, db_url: str = settings.database_url):
        self.engine: Engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={
                "options": f"-c statement_timeout={settings.STATEMENT_TIMEOUT_MS} -c default_transaction_read_only=on"
            }
        )

    def execute_read_query(self, sql_query: str) -> Tuple[List[Dict[str, Any]], List[str], float]:
        """
        Executes a validated SELECT query on the read-only PostgreSQL database.
        If PostgreSQL is offline or credentials fail, automatically executes against
        the local SQLite database replica.
        Returns: (records, column_names, execution_time_ms)
        """
        start_time = time.perf_counter()

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                columns = list(result.keys()) if result.returns_rows else []
                rows = result.fetchall() if result.returns_rows else []

                records = self._format_rows(columns, rows)
                duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                return records, columns, duration_ms
        except Exception as pg_err:
            # Fallback to local SQLite database if available
            if SQLITE_DB_PATH.exists():
                return self._execute_sqlite_fallback(sql_query, start_time)
            raise pg_err

    def _execute_sqlite_fallback(self, sql_query: str, start_time: float) -> Tuple[List[Dict[str, Any]], List[str], float]:
        """Executes query against the local SQLite database attached as analytics_mart."""
        clean_sql = re.sub(r'\bTRUE\b', '1', sql_query, flags=re.IGNORECASE)
        clean_sql = re.sub(r'\bFALSE\b', '0', clean_sql, flags=re.IGNORECASE)
        clean_sql = re.sub(r'::[a-zA-Z0-9_]+', '', clean_sql)

        conn = sqlite3.connect(":memory:")
        conn.execute(f"ATTACH DATABASE '{SQLITE_DB_PATH.as_posix()}' AS analytics_mart;")
        cur = conn.cursor()
        cur.execute(clean_sql)

        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
        cur.close()
        conn.close()

        records = self._format_rows(columns, rows)
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return records, columns, duration_ms

    def _format_rows(self, columns: List[str], rows: List[Any]) -> List[Dict[str, Any]]:
        records = []
        for r in rows:
            row_dict = {}
            for col, val in zip(columns, r):
                if hasattr(val, "isoformat"):
                    row_dict[col] = val.isoformat()
                elif isinstance(val, (int, float, str, bool)) or val is None:
                    row_dict[col] = val
                else:
                    row_dict[col] = str(val)
            records.append(row_dict)
        return records


db_manager = DatabaseManager()
