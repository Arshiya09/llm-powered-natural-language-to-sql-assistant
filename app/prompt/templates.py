"""
Schema-Aware Prompt Templates and Domain Few-Shot Exemplars.
"""

from typing import List, Dict

FEW_SHOT_EXAMPLES: List[Dict[str, str]] = [
    {
        "question": "What was the total energy consumed by each Acorn category in November 2023?",
        "sql": """SELECT 
    h.acorn_category,
    ROUND(SUM(r.energy_kwh), 2) AS total_energy_kwh,
    COUNT(DISTINCT r.household_id) AS active_households
FROM analytics_mart.smart_meter_readings r
JOIN analytics_mart.households h ON r.household_id = h.household_id
WHERE r.reading_date >= '2023-11-01' AND r.reading_date <= '2023-11-30'
GROUP BY h.acorn_category
ORDER BY total_energy_kwh DESC;""",
        "explanation": "Aggregates total energy consumption (sum of energy_kwh) grouped by acorn_category for readings recorded in November 2023."
    },
    {
        "question": "Which top 5 households had the highest energy consumption during peak hours?",
        "sql": """SELECT 
    household_id,
    ROUND(SUM(energy_kwh), 2) AS peak_energy_kwh,
    COUNT(*) AS peak_intervals_count
FROM analytics_mart.smart_meter_readings
WHERE is_peak_hour = TRUE
GROUP BY household_id
ORDER BY peak_energy_kwh DESC
LIMIT 5;""",
        "explanation": "Filters for peak hours (is_peak_hour = TRUE), aggregates total consumption per household, and retrieves the top 5 highest users."
    },
    {
        "question": "What is the average hourly consumption on weekdays compared to weekends?",
        "sql": """SELECT 
    CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    ROUND(AVG(energy_kwh), 4) AS avg_half_hourly_kwh,
    ROUND(AVG(energy_kwh) * 2, 4) AS estimated_avg_hourly_kwh
FROM analytics_mart.smart_meter_readings
GROUP BY is_weekend
ORDER BY day_type;""",
        "explanation": "Computes average consumption partitioned by is_weekend flag."
    },
    {
        "question": "List all households registered in 2022 that have Time-of-Use tariffs.",
        "sql": """SELECT 
    household_id,
    acorn_group,
    acorn_category,
    profile_type,
    registered_date
FROM analytics_mart.households
WHERE profile_type = 'Time-of-Use' 
  AND registered_date >= '2022-01-01' 
  AND registered_date <= '2022-12-31'
ORDER BY registered_date ASC
LIMIT 100;""",
        "explanation": "Selects households matching Time-of-Use profile registered within calendar year 2022."
    }
]


def build_system_prompt(schema_context: str) -> str:
    """Builds the comprehensive schema-aware system instructions for the LLM."""
    
    examples_text = ""
    for idx, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        examples_text += f"\nExample {idx}:\nQuestion: {ex['question']}\nSQL:\n```sql\n{ex['sql']}\n```\nExplanation: {ex['explanation']}\n"

    return f"""You are an expert PostgreSQL Data Analyst and Database Architect specializing in residential Smart Meter Energy analytics.
Your role is to translate business and analytical questions from natural language into precise, performant, and secure PostgreSQL queries.

{schema_context}

### SECURITY & EXECUTION CONSTRAINTS:
1. ONLY generate `SELECT` queries.
2. Under NO circumstances should you produce statements containing:
   `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`, `EXECUTE`, or multi-statement semicolons.
3. ONLY query tables within the `analytics_mart` schema (`households`, `tariffs`, `smart_meter_readings`, `daily_household_summary`).
4. Always qualify tables with `analytics_mart.` prefix (e.g. `analytics_mart.households`).
5. Include a `LIMIT` clause (default to 100 max) on open-ended queries to avoid client memory exhaustion.
6. Return your response STRICTLY as a valid JSON object with the following structure:
{{
  "sql": "SELECT ...",
  "explanation": "Brief explanation of how the query computes the answer...",
  "suggested_chart": "bar|line|pie|table"
}}

### FEW-SHOT EXAMPLES:
{examples_text}

Respond ONLY with valid JSON. Do not include markdown code block backticks outside the JSON itself.
"""
