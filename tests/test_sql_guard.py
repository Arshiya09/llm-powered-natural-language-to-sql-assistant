import pytest
from app.validator.sql_guard import SQLGuard, SQLSecurityViolation


@pytest.fixture
def guard():
    return SQLGuard(max_limit=100)


def test_valid_select_queries(guard):
    valid_queries = [
        "SELECT * FROM analytics_mart.households;",
        "SELECT household_id, energy_kwh FROM analytics_mart.smart_meter_readings WHERE is_peak_hour = TRUE LIMIT 10",
        """SELECT h.acorn_category, SUM(r.energy_kwh) 
           FROM analytics_mart.smart_meter_readings r 
           JOIN analytics_mart.households h ON r.household_id = h.household_id 
           GROUP BY h.acorn_category;""",
        "SELECT * FROM analytics_mart.tariffs WHERE rate_type = 'FLAT'"
    ]

    for q in valid_queries:
        sanitized, ok = guard.validate_and_sanitize(q)
        assert ok is True
        assert "select" in sanitized.lower()


def test_reject_dangerous_dml(guard):
    dangerous_dml = [
        "DROP TABLE analytics_mart.households;",
        "DELETE FROM analytics_mart.smart_meter_readings WHERE 1=1;",
        "UPDATE analytics_mart.tariffs SET flat_rate_per_kwh = 0;",
        "INSERT INTO analytics_mart.households (household_id) VALUES ('HACK');",
        "TRUNCATE TABLE analytics_mart.households;",
        "ALTER TABLE analytics_mart.households ADD COLUMN hacked TEXT;"
    ]

    for q in dangerous_dml:
        with pytest.raises(SQLSecurityViolation, match="Unauthorized statement type"):
            guard.validate_and_sanitize(q)


def test_reject_stacked_queries(guard):
    stacked = "SELECT * FROM analytics_mart.households; DROP TABLE analytics_mart.tariffs;"
    with pytest.raises(SQLSecurityViolation, match="Multiple SQL statements"):
        guard.validate_and_sanitize(stacked)


def test_reject_unauthorized_tables(guard):
    prohibited_tables = [
        "SELECT * FROM etl_metadata.pipelines;",
        "SELECT * FROM pg_catalog.pg_user;",
        "SELECT * FROM information_schema.tables;",
        "SELECT * FROM sensitive_customer_data;"
    ]

    for q in prohibited_tables:
        with pytest.raises(SQLSecurityViolation, match="Access Denied: Table"):
            guard.validate_and_sanitize(q)


def test_reject_forbidden_functions(guard):
    forbidden_sql = "SELECT pg_sleep(5) FROM analytics_mart.households;"
    with pytest.raises(SQLSecurityViolation, match="Unauthorized function invocation"):
        guard.validate_and_sanitize(forbidden_sql)


def test_automatic_limit_injection(guard):
    query_without_limit = "SELECT * FROM analytics_mart.households"
    sanitized, _ = guard.validate_and_sanitize(query_without_limit)
    assert "LIMIT 100" in sanitized.upper()

    query_with_huge_limit = "SELECT * FROM analytics_mart.households LIMIT 50000"
    sanitized, _ = guard.validate_and_sanitize(query_with_huge_limit)
    assert "LIMIT 100" in sanitized.upper()
