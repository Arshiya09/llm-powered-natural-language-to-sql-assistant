"""
Seeds a local SQLite database with the full analytics_mart schema and data.
This allows running the entire application offline without requiring PostgreSQL or any password.
"""

import datetime
import random
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "smart_meter_dw.db"

def seed_sqlite():
    print(f"[*] Creating/Seeding local SQLite database at: {DB_PATH}")
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create tables
    cur.execute("""
    CREATE TABLE households (
        household_id TEXT PRIMARY KEY,
        acorn_group TEXT NOT NULL,
        acorn_category TEXT NOT NULL,
        profile_type TEXT NOT NULL,
        registered_date TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE tariffs (
        tariff_code TEXT PRIMARY KEY,
        tariff_name TEXT NOT NULL,
        rate_type TEXT NOT NULL,
        flat_rate_per_kwh REAL,
        peak_rate_per_kwh REAL,
        off_peak_rate_per_kwh REAL,
        currency TEXT NOT NULL DEFAULT 'GBP',
        effective_date TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE smart_meter_readings (
        household_id TEXT NOT NULL,
        reading_datetime TEXT NOT NULL,
        energy_kwh REAL NOT NULL,
        tariff_code TEXT NOT NULL,
        reading_date TEXT NOT NULL,
        reading_hour INTEGER NOT NULL,
        is_peak_hour INTEGER NOT NULL,
        is_weekend INTEGER NOT NULL,
        PRIMARY KEY (household_id, reading_datetime)
    );
    """)

    cur.execute("""
    CREATE TABLE daily_household_summary (
        household_id TEXT NOT NULL,
        summary_date TEXT NOT NULL,
        total_kwh REAL NOT NULL,
        peak_kwh REAL NOT NULL,
        off_peak_kwh REAL NOT NULL,
        avg_hourly_kwh REAL NOT NULL,
        max_hourly_kwh REAL NOT NULL,
        reading_count INTEGER NOT NULL,
        PRIMARY KEY (household_id, summary_date)
    );
    """)

    # Seed tariffs
    cur.executemany("""
    INSERT INTO tariffs VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, [
        ('STD_FLAT', 'Standard Flat Rate', 'FLAT', 0.2450, None, None, 'GBP', '2023-01-01'),
        ('TOU_ECON7', 'Economy 7 Time-of-Use', 'DYNAMIC', None, 0.3850, 0.1250, 'GBP', '2023-01-01'),
        ('EV_SMART_SAVE', 'EV Smart Save Plan', 'DYNAMIC', None, 0.4200, 0.0850, 'GBP', '2023-01-01')
    ])

    # Seed households
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

    cur.executemany("""
    INSERT INTO households VALUES (?, ?, ?, ?, ?);
    """, households_data)

    # Seed readings
    random.seed(42)
    start_date = datetime.date(2023, 11, 1)
    days_count = 10
    household_tariffs = {'Standard': 'STD_FLAT', 'Time-of-Use': 'TOU_ECON7', 'EV-Owner': 'EV_SMART_SAVE'}
    household_profile_map = {h[0]: h[3] for h in households_data}

    readings = []
    for day_offset in range(days_count):
        curr_date = start_date + datetime.timedelta(days=day_offset)
        is_wknd = 1 if curr_date.weekday() >= 5 else 0

        for hour in range(24):
            is_pk = 1 if 16 <= hour < 19 else 0
            for minute in (0, 30):
                dt_str = f"{curr_date.isoformat()} {hour:02d}:{minute:02d}:00"
                for hid, profile in household_profile_map.items():
                    tariff = household_tariffs[profile]
                    base_kwh = random.uniform(0.15, 0.45)
                    if is_pk:
                        base_kwh *= random.uniform(1.8, 3.2)
                    if profile == 'EV-Owner' and hour in (1, 2, 3, 4):
                        base_kwh += random.uniform(2.5, 4.5)
                    if profile == 'EV-Owner' and is_pk:
                        base_kwh += random.uniform(0.5, 1.5)
                    if hid == 'MAC000001' and is_pk:
                        base_kwh += 0.8
                    if curr_date == datetime.date(2023, 11, 5) and hour == 18 and minute == 0 and hid == 'MAC000002':
                        base_kwh = 6.45

                    readings.append((
                        hid,
                        dt_str,
                        round(base_kwh, 4),
                        tariff,
                        curr_date.isoformat(),
                        hour,
                        is_pk,
                        is_wknd
                    ))

    cur.executemany("""
    INSERT INTO smart_meter_readings VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, readings)

    # Seed summaries
    cur.execute("""
    INSERT INTO daily_household_summary
    SELECT 
        household_id,
        reading_date AS summary_date,
        ROUND(SUM(energy_kwh), 4) AS total_kwh,
        ROUND(SUM(CASE WHEN is_peak_hour = 1 THEN energy_kwh ELSE 0 END), 4) AS peak_kwh,
        ROUND(SUM(CASE WHEN is_peak_hour = 0 THEN energy_kwh ELSE 0 END), 4) AS off_peak_kwh,
        ROUND(AVG(energy_kwh), 4) AS avg_hourly_kwh,
        ROUND(MAX(energy_kwh), 4) AS max_hourly_kwh,
        COUNT(*) AS reading_count
    FROM smart_meter_readings
    GROUP BY household_id, reading_date;
    """)

    conn.commit()
    conn.close()
    print(f"[SUCCESS] Seeded SQLite database ({len(households_data)} households, {len(readings)} readings)!")

if __name__ == "__main__":
    seed_sqlite()
