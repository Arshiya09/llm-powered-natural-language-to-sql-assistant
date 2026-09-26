-- =========================================================================
-- Smart Meter DW Database & Schema Initialization Script
-- =========================================================================

-- 1. Create User and Database (Execute connected to default 'postgres' database)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nl2sql_readonly') THEN
        CREATE USER nl2sql_readonly WITH PASSWORD 'readonly_secure_pass_2026';
    ELSE
        ALTER USER nl2sql_readonly WITH PASSWORD 'readonly_secure_pass_2026';
    END IF;
END
$$;

-- Connect to database 'smart_meter_dw'
\c smart_meter_dw

-- 2. Schema Creation
CREATE SCHEMA IF NOT EXISTS analytics_mart;

-- 3. Table Definitions
CREATE TABLE IF NOT EXISTS analytics_mart.households (
    household_id VARCHAR(50) PRIMARY KEY,
    acorn_group VARCHAR(50) NOT NULL,
    acorn_category VARCHAR(50) NOT NULL,
    profile_type VARCHAR(50) NOT NULL,
    registered_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics_mart.tariffs (
    tariff_code VARCHAR(50) PRIMARY KEY,
    tariff_name VARCHAR(100) NOT NULL,
    rate_type VARCHAR(50) NOT NULL,
    flat_rate_per_kwh NUMERIC(10, 4),
    peak_rate_per_kwh NUMERIC(10, 4),
    off_peak_rate_per_kwh NUMERIC(10, 4),
    currency VARCHAR(10) NOT NULL DEFAULT 'GBP',
    effective_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics_mart.smart_meter_readings (
    household_id VARCHAR(50) NOT NULL REFERENCES analytics_mart.households(household_id),
    reading_datetime TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    energy_kwh NUMERIC(10, 4) NOT NULL,
    tariff_code VARCHAR(50) NOT NULL REFERENCES analytics_mart.tariffs(tariff_code),
    reading_date DATE NOT NULL,
    reading_hour SMALLINT NOT NULL,
    is_peak_hour BOOLEAN NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    PRIMARY KEY (household_id, reading_datetime)
);

CREATE TABLE IF NOT EXISTS analytics_mart.daily_household_summary (
    household_id VARCHAR(50) NOT NULL,
    summary_date DATE NOT NULL,
    total_kwh NUMERIC(10, 4) NOT NULL,
    peak_kwh NUMERIC(10, 4) NOT NULL,
    off_peak_kwh NUMERIC(10, 4) NOT NULL,
    avg_hourly_kwh NUMERIC(10, 4) NOT NULL,
    max_hourly_kwh NUMERIC(10, 4) NOT NULL,
    reading_count INT NOT NULL,
    PRIMARY KEY (household_id, summary_date)
);

-- 4. Permissions for nl2sql_readonly
GRANT CONNECT ON DATABASE smart_meter_dw TO nl2sql_readonly;
GRANT USAGE ON SCHEMA analytics_mart TO nl2sql_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics_mart TO nl2sql_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics_mart GRANT SELECT ON TABLES TO nl2sql_readonly;
