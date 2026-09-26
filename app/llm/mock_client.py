"""
Deterministic Mock LLM Client.
Enables offline benchmarking, automated CI testing, and zero-cost local evaluation.
"""

import re
from typing import Dict, List, Tuple
from app.llm.base import BaseLLMClient, LLMResponse


class MockLLMClient(BaseLLMClient):
    """Rule-based and pattern-matching mock client for offline energy queries."""

    PATTERNS: List[Tuple[re.Pattern, str, str, str]] = [
        (
            re.compile(r"acorn.*category|category.*acorn", re.IGNORECASE),
            """SELECT 
    h.acorn_category,
    ROUND(SUM(r.energy_kwh), 2) AS total_energy_kwh,
    COUNT(DISTINCT r.household_id) AS household_count
FROM analytics_mart.smart_meter_readings r
JOIN analytics_mart.households h ON r.household_id = h.household_id
GROUP BY h.acorn_category
ORDER BY total_energy_kwh DESC;""",
            "Calculates total energy consumption aggregated by Acorn demographic category.",
            "bar"
        ),
        (
            re.compile(r"peak.*(?:hour|consumption|usage)|top.*peak", re.IGNORECASE),
            """SELECT 
    household_id,
    ROUND(SUM(energy_kwh), 2) AS peak_energy_kwh,
    COUNT(*) AS peak_readings
FROM analytics_mart.smart_meter_readings
WHERE is_peak_hour = TRUE
GROUP BY household_id
ORDER BY peak_energy_kwh DESC
LIMIT 5;""",
            "Finds top households with the highest consumption during peak hours (16:00-19:00).",
            "bar"
        ),
        (
            re.compile(r"weekend.*vs.*weekday|weekday.*vs.*weekend", re.IGNORECASE),
            """SELECT 
    CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    ROUND(AVG(energy_kwh), 4) AS avg_half_hourly_kwh,
    ROUND(SUM(energy_kwh), 2) AS total_kwh
FROM analytics_mart.smart_meter_readings
GROUP BY is_weekend
ORDER BY day_type;""",
            "Compares electricity consumption metrics between weekends and weekdays.",
            "pie"
        ),
        (
            re.compile(r"tariff|pricing|rate", re.IGNORECASE),
            """SELECT 
    t.tariff_code,
    t.tariff_name,
    t.rate_type,
    COUNT(DISTINCT r.household_id) AS enrolled_households,
    ROUND(SUM(r.energy_kwh), 2) AS total_consumption_kwh
FROM analytics_mart.tariffs t
LEFT JOIN analytics_mart.smart_meter_readings r ON t.tariff_code = r.tariff_code
GROUP BY t.tariff_code, t.tariff_name, t.rate_type
ORDER BY total_consumption_kwh DESC;""",
            "Analyzes household enrollment and total energy consumed per tariff plan.",
            "bar"
        ),
        (
            re.compile(r"hourly.*profile|hourly.*pattern|hour.*day", re.IGNORECASE),
            """SELECT 
    reading_hour,
    ROUND(AVG(energy_kwh), 4) AS avg_kwh,
    ROUND(SUM(energy_kwh), 2) AS total_kwh
FROM analytics_mart.smart_meter_readings
GROUP BY reading_hour
ORDER BY reading_hour ASC;""",
            "Profiles diurnal electricity demand curve across all 24 hours of the day.",
            "line"
        ),
        (
            re.compile(r"daily.*trend|daily.*consumption|per.*day", re.IGNORECASE),
            """SELECT 
    reading_date,
    ROUND(SUM(energy_kwh), 2) AS daily_total_kwh,
    ROUND(AVG(energy_kwh), 4) AS daily_avg_kwh
FROM analytics_mart.smart_meter_readings
GROUP BY reading_date
ORDER BY reading_date ASC;""",
            "Time series of daily aggregate energy consumption.",
            "line"
        ),
        (
            re.compile(r"ev|electric vehicle", re.IGNORECASE),
            """SELECT 
    h.household_id,
    h.acorn_group,
    ROUND(SUM(r.energy_kwh), 2) AS total_kwh
FROM analytics_mart.households h
JOIN analytics_mart.smart_meter_readings r ON h.household_id = r.household_id
WHERE h.profile_type = 'EV-Owner'
GROUP BY h.household_id, h.acorn_group
ORDER BY total_kwh DESC
LIMIT 10;""",
            "Queries consumption specifically for EV-Owner households.",
            "bar"
        )
    ]

    DEFAULT_SQL = """SELECT 
    household_id,
    reading_date,
    ROUND(SUM(energy_kwh), 2) AS total_kwh
FROM analytics_mart.smart_meter_readings
GROUP BY household_id, reading_date
ORDER BY total_kwh DESC
LIMIT 20;"""

    def generate(self, system_prompt: str, user_question: str) -> LLMResponse:
        q = user_question.strip()
        for pattern, sql, expl, chart in self.PATTERNS:
            if pattern.search(q):
                return LLMResponse(sql=sql, explanation=expl, suggested_chart=chart)

        return LLMResponse(
            sql=self.DEFAULT_SQL,
            explanation="Retrieves household daily consumption summaries from analytics_mart.",
            suggested_chart="table"
        )
