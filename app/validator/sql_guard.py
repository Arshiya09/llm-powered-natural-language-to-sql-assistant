"""
SQLGuard: AST-based Security Validation Layer for Natural Language to SQL.
Enforces SELECT-only execution, table whitelisting, statement isolation, and limit bounds.
"""

from typing import Set, Tuple
import sqlglot
from sqlglot import exp

from app.core.config import settings


class SQLSecurityViolation(Exception):
    """Raised when generated SQL violates security boundaries."""
    pass


class SQLGuard:
    """Rigorous SQL AST Security Validator powered by SQLGlot."""

    ALLOWED_TABLES: Set[str] = {
        "smart_meter_readings",
        "households",
        "tariffs",
        "daily_household_summary"
    }

    FORBIDDEN_FUNCTIONS: Set[str] = {
        "pg_sleep",
        "pg_terminate_backend",
        "pg_cancel_backend",
        "lo_export",
        "lo_import",
        "dblink",
        "system",
        "exec"
    }

    def __init__(self, max_limit: int = settings.MAX_ROW_LIMIT):
        self.max_limit = max_limit

    def validate_and_sanitize(self, raw_sql: str) -> Tuple[str, bool]:
        """
        Parses and validates a raw SQL query string against security constraints.
        Returns: (sanitized_sql_string, is_valid)
        Raises: SQLSecurityViolation if validation fails.
        """
        clean_sql = raw_sql.strip()
        # Remove trailing semicolon if present
        if clean_sql.endswith(";"):
            clean_sql = clean_sql[:-1].strip()

        # 1. Parse AST with PostgreSQL dialect
        try:
            expressions = sqlglot.parse(clean_sql, read="postgres")
        except Exception as e:
            raise SQLSecurityViolation(f"SQL Syntax Error: Unable to parse query: {e}")

        # 2. Strictly single-statement check
        if len(expressions) == 0:
            raise SQLSecurityViolation("Query cannot be empty.")
        if len(expressions) > 1:
            raise SQLSecurityViolation("Multiple SQL statements / stacked queries are forbidden.")

        statement = expressions[0]

        # 3. SELECT-Only Validation
        # Must be either a Select expression or a Union of Select expressions
        if not self._is_valid_select(statement):
            raise SQLSecurityViolation(
                f"Unauthorized statement type '{statement.key.upper()}'. Only read-only SELECT queries are permitted."
            )

        # 4. Check for forbidden commands/functions
        for func in statement.find_all(exp.Anonymous, exp.Func):
            func_name = func.name.lower()
            if func_name in self.FORBIDDEN_FUNCTIONS:
                raise SQLSecurityViolation(f"Unauthorized function invocation: '{func_name}()' is forbidden.")

        # 5. Table Whitelist Enforcement
        tables = [t.name.lower() for t in statement.find_all(exp.Table)]
        for tbl in tables:
            # Strip schema if provided (e.g., 'analytics_mart.households' -> 'households')
            short_tbl = tbl.split(".")[-1]
            if short_tbl not in self.ALLOWED_TABLES:
                raise SQLSecurityViolation(
                    f"Access Denied: Table '{tbl}' is not in the authorized analytics whitelist {sorted(list(self.ALLOWED_TABLES))}."
                )

        # 6. Safety Limit Injection
        # If query has no LIMIT, or limit > max_limit, cap it
        limit_node = statement.find(exp.Limit)
        if limit_node is None:
            statement = statement.limit(self.max_limit)
        else:
            try:
                curr_limit = int(limit_node.expression.this)
                if curr_limit > self.max_limit:
                    limit_node.set("expression", exp.Literal.number(self.max_limit))
            except Exception:
                limit_node.set("expression", exp.Literal.number(self.max_limit))

        # Output sanitized SQL with postgres dialect
        sanitized_sql = statement.sql(dialect="postgres")
        return sanitized_sql, True

    def _is_valid_select(self, node: exp.Expression) -> bool:
        """Verifies if the expression or its CTEs/Unions only contain SELECT statements."""
        if isinstance(node, (exp.Select, exp.Union)):
            # Check CTEs / with clause
            with_clause = node.find(exp.With)
            if with_clause:
                for cte in with_clause.expressions:
                    if not isinstance(cte.this, (exp.Select, exp.Union)):
                        return False
            return True
        return False


sql_guard = SQLGuard()
