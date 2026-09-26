import pytest
from app.prompt.introspector import schema_introspector
from app.prompt.templates import build_system_prompt


def test_schema_context_contains_key_tables():
    context = schema_introspector.get_schema_context()
    assert "analytics_mart.households" in context
    assert "analytics_mart.tariffs" in context
    assert "analytics_mart.smart_meter_readings" in context
    assert "is_peak_hour" in context
    assert "acorn_category" in context


def test_system_prompt_builder():
    context = schema_introspector.get_schema_context()
    prompt = build_system_prompt(context)
    assert "ONLY generate `SELECT` queries" in prompt
    assert "analytics_mart" in prompt
    assert "FEW-SHOT EXAMPLES" in prompt
