"""
PostgreSQL Database Setup and Data Seeder for Smart Meter DW.
Initializes the database, creates the read-only user, builds tables, and inserts sample data.
"""

import argparse
import datetime
import random
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def get_admin_connection(host, port, user, password, dbname="postgres"):
    return psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname
    )

def setup_database(pg_host="localhost", pg_port=5432, pg_admin_user="postgres", pg_admin_pass=""):
    print(f"[*] Connecting to PostgreSQL as admin ({pg_admin_user}) at {pg_host}:{pg_port}...")
    
    # 1. Connect to default postgres DB to create database and user
    conn = get_admin_connection(pg_host, pg_port, pg_admin_user, pg_admin_pass, "postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # Create role nl2sql_readonly if not exists
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'nl2sql_readonly';")
    if not cur.fetchone():
        print("[*] Creating user 'nl2sql_readonly'...")
        cur.execute("CREATE USER nl2sql_readonly WITH PASSWORD 'readonly_secure_pass_2026';")
    else:
        print("[*] Updating password for 'nl2sql_readonly'...")
        cur.execute("ALTER USER nl2sql_readonly WITH PASSWORD 'readonly_secure_pass_2026';")
        
    # Create database smart_meter_dw if not exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'smart_meter_dw';")
    if not cur.fetchone():
        print("[*] Creating database 'smart_meter_dw'...")
        cur.execute("CREATE DATABASE smart_meter_dw;")
    else:
        print("[*] Database 'smart_meter_dw' already exists.")
        
    cur.close()
    conn.close()

    # 2. Connect to smart_meter_dw database
    print("[*] Connecting to 'smart_meter_dw' to create schema, tables, and seed data...")
    dw_conn = get_admin_connection(pg_host, pg_port, pg_admin_user, pg_admin_pass, "smart_meter_dw")
    dw_cur = dw_conn.cursor()

    # Create schema
    dw_cur.execute("CREATE SCHEMA IF NOT EXISTS analytics_mart;")
    
    # Create tables
    print("[*] Creating tables in analytics_mart...")
    dw_cur.execute("""
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
    """)

    # Seed Tariffs
    print("[*] Seeding tariffs...")
    dw_cur.execute("""
    INSERT INTO analytics_mart.tariffs 
        (tariff_code, tariff_name, rate_type, flat_rate_per_kwh, peak_rate_per_kwh, off_peak_rate_per_kwh, currency, effective_date)
    VALUES 
        ('STD_FLAT', 'Standard Flat Rate', 'FLAT', 0.2450, NULL, NULL, 'GBP', '2023-01-01'),
        ('TOU_ECON7', 'Economy 7 Time-of-Use', 'DYNAMIC', NULL, 0.3850, 0.1250, 'GBP', '2023-01-01'),
        ('EV_SMART_SAVE', 'EV Smart Save Plan', 'DYNAMIC', NULL, 0.4200, 0.0850, 'GBP', '2023-01-01')
    ON CONFLICT (tariff_code) DO UPDATE 
    SET tariff_name = EXCLUDED.tariff_name,
        flat_rate_per_kwh = EXCLUDED.flat_rate_per_kwh,
        peak_rate_per_kwh = EXCLUDED.peak_rate_per_kwh,
        off_peak_rate_per_kwh = EXCLUDED.off_peak_rate_per_kwh;
    """)

    # Seed Households
    print("[*] Seeding households...")
    households_data = [
        ('MAC000001', 'Acorn-A', 'Affluent', 'Standard', '2021-04-12'),
        ('MAC000002', 'Acorn-A', 'Affluent', 'EV-Owner', '2022-03-15'),
        ('MAC000003', 'Acorn-B', 'Affluent', 'Time-of-Use', '2022-06-20'),
        ('MAC000004', 'Acorn-B', 'Affluent', 'EV-Owner', '2022-09-05'),
        ('MAC000005', 'Acorn-C', 'Affluent', 'Standard', '2021-11-01'),
        ('MAC000006', 'Acorn-D', 'Affluent', 'EV-Owner', '2022-11-18'),
        ('MAC000007', 'Acorn-E', 'Comfortable', 'Standard', '2021-02-14'),
        ('MAC000008', 'Acorn-F', 'Comfortable', 'Time-of-Use', '2022-01-22'),
        ('MAC000009', 'Acorn-G', 'Comfortable', 'Standard', '2023-02-10'),
        ('MAC000010', 'Acorn-H', 'Comfortable', 'EV-Owner', '2022-05-30'),
        ('MAC000011', 'Acorn-I', 'Comfortable', 'Time-of-Use', '2023-05-19'),
        ('MAC000012', 'Acorn-J', 'Comfortable', 'Standard', '2021-09-08'),
        ('MAC000013', 'Acorn-K', 'Adversity', 'Standard', '2021-01-20'),
        ('MAC000014', 'Acorn-L', 'Adversity', 'Time-of-Use', '2022-04-14'),
        ('MAC000015', 'Acorn-M', 'Adversity', 'Standard', '2023-03-01'),
        ('MAC000016', 'Acorn-N', 'Adversity', 'Standard', '2021-10-15'),
        ('MAC000017', 'Acorn-O', 'Adversity', 'Time-of-Use', '2022-08-11'),
        ('MAC000018', 'Acorn-P', 'Adversity', 'Standard', '2023-07-25'),
        ('MAC000019', 'Acorn-Q', 'Adversity', 'Standard', '2023-09-14'),
        ('MAC000020', 'Acorn-A', 'Affluent', 'EV-Owner', '2023-10-01'),
    ]

    for h in households_data:
        dw_cur.execute("""
        INSERT INTO analytics_mart.households (household_id, acorn_group, acorn_category, profile_type, registered_date)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (household_id) DO UPDATE
        SET acorn_group = EXCLUDED.acorn_group,
            acorn_category = EXCLUDED.acorn_category,
            profile_type = EXCLUDED.profile_type,
            registered_date = EXCLUDED.registered_date;
        """, h)

    # Seed Half-hourly Smart Meter Readings for November 2023 (Nov 1 - Nov 10)
    print("[*] Seeding smart meter readings for November 2023...")
    dw_cur.execute("SELECT COUNT(*) FROM analytics_mart.smart_meter_readings;")
    existing_readings = dw_cur.fetchone()[0]

    if existing_readings < 1000:
        readings_batch = []
        random.seed(42)
        start_date = datetime.date(2023, 11, 1)
        days_count = 10  # 10 days of half-hourly readings for 20 households

        household_tariffs = {
            'Standard': 'STD_FLAT',
            'Time-of-Use': 'TOU_ECON7',
            'EV-Owner': 'EV_SMART_SAVE'
        }

        household_profile_map = {h[0]: h[3] for h in households_data}

        for day_offset in range(days_count):
            curr_date = start_date + datetime.timedelta(days=day_offset)
            is_wknd = curr_date.weekday() >= 5  # Sat or Sun

            for hour in range(24):
                is_pk = (16 <= hour < 19)
                for minute in (0, 30):
                    dt = datetime.datetime.combine(curr_date, datetime.time(hour, minute))
                    
                    for hid, profile in household_profile_map.items():
                        tariff = household_tariffs[profile]
                        
                        # Base consumption logic
                        base_kwh = random.uniform(0.15, 0.45)
                        if is_pk:
                            base_kwh *= random.uniform(1.8, 3.2)
                        if profile == 'EV-Owner' and hour in (1, 2, 3, 4):  # overnight charging
                            base_kwh += random.uniform(2.5, 4.5)
                        if profile == 'EV-Owner' and is_pk:
                            base_kwh += random.uniform(0.5, 1.5)
                        if hid == 'MAC000001' and is_pk:
                            base_kwh += 0.8
                        if curr_date == datetime.date(2023, 11, 5) and hour == 18 and minute == 0 and hid == 'MAC000002':
                            base_kwh = 6.45  # Peak spike test record

                        readings_batch.append((
                            hid,
                            dt,
                            round(base_kwh, 4),
                            tariff,
                            curr_date,
                            hour,
                            is_pk,
                            is_wknd
                        ))

        # Insert batch
        psycopg2.extras.execute_values(
            dw_cur,
            """
            INSERT INTO analytics_mart.smart_meter_readings
                (household_id, reading_datetime, energy_kwh, tariff_code, reading_date, reading_hour, is_peak_hour, is_weekend)
            VALUES %s
            ON CONFLICT (household_id, reading_datetime) DO NOTHING;
            """,
            readings_batch,
            page_size=2000
        )
        print(f"[*] Inserted {len(readings_batch)} readings.")

    # Populate daily summary
    print("[*] Populating daily_household_summary...")
    dw_cur.execute("""
    INSERT INTO analytics_mart.daily_household_summary
        (household_id, summary_date, total_kwh, peak_kwh, off_peak_kwh, avg_hourly_kwh, max_hourly_kwh, reading_count)
    SELECT 
        household_id,
        reading_date AS summary_date,
        ROUND(SUM(energy_kwh), 4) AS total_kwh,
        ROUND(SUM(CASE WHEN is_peak_hour THEN energy_kwh ELSE 0 END), 4) AS peak_kwh,
        ROUND(SUM(CASE WHEN NOT is_peak_hour THEN energy_kwh ELSE 0 END), 4) AS off_peak_kwh,
        ROUND(AVG(energy_kwh), 4) AS avg_hourly_kwh,
        ROUND(MAX(energy_kwh), 4) AS max_hourly_kwh,
        COUNT(*) AS reading_count
    FROM analytics_mart.smart_meter_readings
    GROUP BY household_id, reading_date
    ON CONFLICT (household_id, summary_date) DO UPDATE
    SET total_kwh = EXCLUDED.total_kwh,
        peak_kwh = EXCLUDED.peak_kwh,
        off_peak_kwh = EXCLUDED.off_peak_kwh,
        avg_hourly_kwh = EXCLUDED.avg_hourly_kwh,
        max_hourly_kwh = EXCLUDED.max_hourly_kwh,
        reading_count = EXCLUDED.reading_count;
    """)

    # Grant read-only permissions
    print("[*] Granting read-only permissions to user 'nl2sql_readonly'...")
    dw_cur.execute("""
    GRANT CONNECT ON DATABASE smart_meter_dw TO nl2sql_readonly;
    GRANT USAGE ON SCHEMA analytics_mart TO nl2sql_readonly;
    GRANT SELECT ON ALL TABLES IN SCHEMA analytics_mart TO nl2sql_readonly;
    ALTER DEFAULT PRIVILEGES IN SCHEMA analytics_mart GRANT SELECT ON TABLES TO nl2sql_readonly;
    """)

    dw_conn.commit()
    dw_cur.close()
    dw_conn.close()
    print("[+] Database setup complete!")

    # Verify connection as nl2sql_readonly
    print("[*] Verifying connection with 'nl2sql_readonly'...")
    try:
        ro_conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            user="nl2sql_readonly",
            password="readonly_secure_pass_2026",
            dbname="smart_meter_dw"
        )
        ro_cur = ro_conn.cursor()
        ro_cur.execute("SELECT COUNT(*) FROM analytics_mart.households;")
        h_count = ro_cur.fetchone()[0]
        ro_cur.execute("SELECT COUNT(*) FROM analytics_mart.smart_meter_readings;")
        r_count = ro_cur.fetchone()[0]
        ro_cur.close()
        ro_conn.close()
        print(f"[SUCCESS] Connected successfully as 'nl2sql_readonly'!")
        print(f"          - Households: {h_count}")
        print(f"          - Readings:   {r_count}")
        return True
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize and seed Smart Meter PostgreSQL database")
    parser.add_argument("--host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--user", default="postgres", help="PostgreSQL superuser/admin user")
    parser.add_argument("--password", default="", help="PostgreSQL admin password")
    args = parser.parse_args()

    # If no password passed, prompt for it if interactive
    import psycopg2.extras
    setup_database(
        pg_host=args.host,
        pg_port=args.port,
        pg_admin_user=args.user,
        pg_admin_pass=args.password
    )
