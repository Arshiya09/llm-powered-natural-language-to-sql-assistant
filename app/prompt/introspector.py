"""
Database Schema Introspector.
Provides schema-aware context, tables, columns, foreign keys, and sample values
for LLM prompt generation.
"""

from typing import Dict, List, Optional
from sqlalchemy import text
from app.core.config import settings
from app.core.database import db_manager


class SchemaIntrospector:
    """Introspects PostgreSQL schema for analytics_mart or provides fallback metadata."""

    # Static ground truth schema definition for analytics_mart
    STATIC_SCHEMA_DOC = """
### Schema: analytics_mart

#### 1. Table: analytics_mart.households
Description: Demographics and Acorn socioeconomic classifications for residential energy consumers.
Columns:
- household_id (VARCHAR(50), PRIMARY KEY): Unique identifier for household (e.g., 'MAC000001').
- acorn_group (VARCHAR(50)): Detailed Acorn demographic group ('Acorn-A', 'Acorn-B', ..., 'Acorn-Q').
- acorn_category (VARCHAR(50)): High-level socioeconomic category ('Affluent', 'Comfortable', 'Adversity').
- profile_type (VARCHAR(50)): Consumer lifestyle profile ('Standard', 'Time-of-Use', 'EV-Owner').
- registered_date (DATE): Date the smart meter was commissioned.

#### 2. Table: analytics_mart.tariffs
Description: Electricity pricing structures and tariffs.
Columns:
- tariff_code (VARCHAR(50), PRIMARY KEY): Code identifying tariff ('STD_FLAT', 'TOU_ECON7', 'EV_SMART_SAVE').
- tariff_name (VARCHAR(100)): Human-readable tariff plan name.
- rate_type (VARCHAR(50)): Tariff structure ('FLAT', 'DYNAMIC').
- flat_rate_per_kwh (NUMERIC): Rate in GBP/kWh for flat rate plans (e.g., 0.2450).
- peak_rate_per_kwh (NUMERIC): Rate in GBP/kWh during peak hours (16:00-19:00).
- off_peak_rate_per_kwh (NUMERIC): Rate in GBP/kWh during off-peak hours.
- currency (VARCHAR(10)): 'GBP'.
- effective_date (DATE): Start date of tariff rate.

#### 3. Table: analytics_mart.smart_meter_readings
Description: Half-hourly electricity consumption time series data.
Columns:
- household_id (VARCHAR(50), FK -> households.household_id): Household identifier.
- reading_datetime (TIMESTAMP WITHOUT TIME ZONE): Timestamp of meter interval.
- energy_kwh (NUMERIC(10, 4)): Electricity consumed during half-hour interval in kWh.
- tariff_code (VARCHAR(50), FK -> tariffs.tariff_code): Applied tariff plan.
- reading_date (DATE): Extracted date component (e.g., '2023-11-01').
- reading_hour (SMALLINT): Hour of the day (0 to 23).
- is_peak_hour (BOOLEAN): TRUE if reading occurred between 16:00 and 19:00 (4 PM - 7 PM).
- is_weekend (BOOLEAN): TRUE for Saturday or Sunday readings.
PRIMARY KEY: (household_id, reading_datetime)

#### 4. Table: analytics_mart.daily_household_summary
Description: Pre-aggregated daily electricity consumption metrics per household.
Columns:
- household_id (VARCHAR(50)): Household identifier.
- summary_date (DATE): Summary date.
- total_kwh (NUMERIC): Total consumption for the day in kWh.
- peak_kwh (NUMERIC): Consumption during peak hours (16:00-19:00).
- off_peak_kwh (NUMERIC): Consumption during off-peak hours.
- avg_hourly_kwh (NUMERIC): Average hourly consumption.
- max_hourly_kwh (NUMERIC): Maximum half-hourly spike.
- reading_count (INT): Number of recorded intervals (48 for complete days).
PRIMARY KEY: (household_id, summary_date)
"""

    def get_schema_context(self) -> str:
        """Returns schema context documentation for prompt injection."""
        try:
            # Attempt live introspection
            live_ddl = self._introspect_live_schema()
            if live_ddl:
                return live_ddl
        except Exception:
            pass
        return self.STATIC_SCHEMA_DOC.strip()

    def _introspect_live_schema(self) -> Optional[str]:
        query = text("""
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = :schema
            ORDER BY table_name, ordinal_position;
        """)
        with db_manager.engine.connect() as conn:
            rows = conn.execute(query, {"schema": settings.POSTGRES_SCHEMA}).fetchall()
            if not rows:
                return None

            lines = [f"### Live Schema: {settings.POSTGRES_SCHEMA}\n"]
            curr_table = ""
            for r in rows:
                tbl, col, dtype, nullable = r
                if tbl != curr_table:
                    curr_table = tbl
                    lines.append(f"\n#### Table: {settings.POSTGRES_SCHEMA}.{tbl}")
                lines.append(f"- {col} ({dtype}, nullable: {nullable})")

            return "\n".join(lines)


schema_introspector = SchemaIntrospector()
