"""
FastAPI Route Endpoints.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import db_manager
from app.llm.factory import get_llm_client
from app.prompt.introspector import schema_introspector
from app.prompt.templates import build_system_prompt
from app.validator.sql_guard import SQLGuard, SQLSecurityViolation

router = APIRouter(prefix="/api/v1", tags=["nl2sql"])
sql_guard = SQLGuard()


class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language question", min_length=3)
    temperature: Optional[float] = 0.0


class QueryResponse(BaseModel):
    natural_query: str
    generated_sql: str
    sanitized_sql: str
    explanation: str
    suggested_chart: str
    validation_passed: bool
    execution_time_ms: float
    row_count: int
    columns: List[str]
    data: List[Dict[str, Any]]
    db_connected: bool


class SchemaResponse(BaseModel):
    schema_name: str
    documentation: str


@router.post("/query", response_model=QueryResponse)
async def process_natural_query(req: QueryRequest):
    """
    Translates a natural language question into SQL, performs AST SELECT-only validation,
    and executes it against the read-only smart meter database.
    """
    # 1. Fetch schema-aware prompt
    schema_doc = schema_introspector.get_schema_context()
    system_prompt = build_system_prompt(schema_doc)

    # 2. Call LLM
    try:
        client = get_llm_client()
        llm_res = client.generate(system_prompt, req.query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM translation error: {str(e)}"
        )

    # 3. Security Validation & Sanitization
    try:
        sanitized_sql, is_valid = sql_guard.validate_and_sanitize(llm_res.sql)
    except SQLSecurityViolation as sec_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "SQL Security Policy Violation",
                "message": str(sec_err),
                "rejected_sql": llm_res.sql
            }
        )
    except Exception as gen_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SQL Parsing Error: {str(gen_err)}"
        )

    # 4. Read-Only Query Execution
    records = []
    columns = []
    exec_ms = 0.0
    db_ok = True

    try:
        records, columns, exec_ms = db_manager.execute_read_query(sanitized_sql)
    except Exception as db_err:
        db_ok = False
        # If DB is not reachable in local/mock mode, provide informative diagnostic
        return QueryResponse(
            natural_query=req.query,
            generated_sql=llm_res.sql,
            sanitized_sql=sanitized_sql,
            explanation=llm_res.explanation + f" (Note: Database query failed or offline: {db_err})",
            suggested_chart=llm_res.suggested_chart or "table",
            validation_passed=True,
            execution_time_ms=0.0,
            row_count=0,
            columns=[],
            data=[],
            db_connected=False
        )

    return QueryResponse(
        natural_query=req.query,
        generated_sql=llm_res.sql,
        sanitized_sql=sanitized_sql,
        explanation=llm_res.explanation,
        suggested_chart=llm_res.suggested_chart or "table",
        validation_passed=True,
        execution_time_ms=exec_ms,
        row_count=len(records),
        columns=columns,
        data=records,
        db_connected=db_ok
    )


@router.get("/schema", response_model=SchemaResponse)
async def get_schema_metadata():
    """Returns database schema definition and documentation."""
    doc = schema_introspector.get_schema_context()
    return SchemaResponse(schema_name=settings.POSTGRES_SCHEMA, documentation=doc)


@router.get("/health")
async def health_check():
    """Health status and provider information."""
    db_healthy = False
    from app.core.database import SQLITE_DB_PATH
    try:
        with db_manager.engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1;"))
            db_healthy = True
    except Exception:
        db_healthy = SQLITE_DB_PATH.exists()

    return {
        "status": "healthy",
        "provider": settings.LLM_PROVIDER,
        "database_connected": db_healthy,
        "max_row_limit": settings.MAX_ROW_LIMIT,
        "statement_timeout_ms": settings.STATEMENT_TIMEOUT_MS
    }
