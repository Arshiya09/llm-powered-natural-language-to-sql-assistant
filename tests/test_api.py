import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "provider" in data


def test_schema_endpoint():
    response = client.get("/api/v1/schema")
    assert response.status_code == 200
    data = response.json()
    assert "analytics_mart" in data["schema_name"]
    assert "households" in data["documentation"]


def test_query_endpoint_with_mock():
    # Test query using deterministic mock client
    payload = {
        "query": "What is the total energy consumed by each Acorn category?",
        "temperature": 0.0
    }
    response = client.post("/api/v1/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["validation_passed"] is True
    assert "SELECT" in data["sanitized_sql"].upper()
    assert "analytics_mart" in data["sanitized_sql"]
    assert data["suggested_chart"] in ["bar", "table", "pie", "line"]


def test_query_endpoint_validation_failure():
    # Prompt attempting injection
    from unittest.mock import patch
    from app.llm.base import LLMResponse

    # Force mock LLM to return a malicious DROP TABLE statement
    with patch("app.api.routes.get_llm_client") as mock_factory:
        mock_instance = mock_factory.return_value
        mock_instance.generate.return_value = LLMResponse(
            sql="DROP TABLE analytics_mart.households;",
            explanation="Malicious drop attempt",
            suggested_chart="table"
        )
        payload = {"query": "Drop all household records!"}
        response = client.post("/api/v1/query", json=payload)
        assert response.status_code == 400
        assert "Security Policy Violation" in str(response.json())
