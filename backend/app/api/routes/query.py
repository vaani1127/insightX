"""
POST /api/query — the main InsightX pipeline.

Flow:
  1. Validate workspace + auth
  2. Load conversation history (multi-turn context)
  3. Disambiguate time phrases → assumptions
  4. LLM generates SQL (schema + metric dict + history + assumptions)
  5. Privacy guard checks the SQL
  6. DuckDB executes SQL
  7. Anomaly detection on results
  8. LLM generates insights (key finding, root cause, follow-ups)
  9. LLM generates narrative
  10. Hallucination guard: narrative vs actual data
  11. Trust layer built
  12. Visualization type selected
  13. Save to history + conversation turns
  14. Return full QueryResponse
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import db
from app.models.schemas import (
    InsightsOut,
    QueryRequest,
    QueryResponse,
    QueryResult,
)
from app.services.anomaly_detector import anomaly_summary, detect_anomalies
from app.services.disambiguation import is_ambiguous, resolve_time_phrases
from app.services.explanation_generator import build_narrative
from app.services.hallucination_guard import check as hallucination_check
from app.services.insight_engine import generate_insights
from app.services.privacy_guard import evaluate_sql
from app.services.sql_generator import SQLGenerationError, generate_sql
from app.services.trust_layer import build_trust_layer
from app.services.visualization import choose_visualization

router = APIRouter(prefix="/query", tags=["query"])


def _get_conversation_history(workspace_id: str, user_id: str) -> list[dict]:
    rows = db.fetchall(
        "SELECT role, content FROM conversation_turns "
        "WHERE workspace_id = ? AND user_id = ? "
        "ORDER BY created_at ASC",
        [workspace_id, user_id],
    )
    return [{"role": r[0], "content": r[1]} for r in rows]


def _save_turn(workspace_id: str, user_id: str, role: str, content: str) -> None:
    db.execute(
        "INSERT INTO conversation_turns (id, workspace_id, user_id, role, content) VALUES (?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), workspace_id, user_id, role, content],
    )


@router.post("", response_model=QueryResponse)
def run_query(payload: QueryRequest, user: dict = Depends(get_current_user)) -> QueryResponse:
    # 1. Validate workspace
    ws_row = db.fetchone(
        "SELECT table_name, row_count FROM workspaces WHERE id = ? AND user_id = ?",
        [payload.workspace_id, user["id"]],
    )
    if ws_row is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    if ws_row[0] is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded to this workspace yet.")

    table_name: str = ws_row[0]

    # 2. Conversation history
    history = _get_conversation_history(payload.workspace_id, user["id"])

    # 3. Disambiguate time phrases
    _, assumptions = resolve_time_phrases(payload.query)

    # 4. Get table schema
    schema = db.table_schema(table_name)

    # 5. Generate SQL via LLM
    try:
        sql = generate_sql(
            question=payload.query,
            schema=schema,
            table_name=table_name,
            assumptions=assumptions,
            conversation_history=history,
        )
    except SQLGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 6. Privacy guard
    privacy = evaluate_sql(sql, user["role"])
    if not privacy.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "privacy_blocked",
                "blocked_columns": privacy.blocked_columns,
                "reason": privacy.policy_reason,
            },
        )

    # 7. Execute SQL
    try:
        columns, rows = db.execute_query(sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"SQL execution failed: {exc}") from exc

    row_count = len(rows)

    # 8. Anomaly detection
    anomaly_flags = detect_anomalies(columns, rows)
    anomaly_strings = anomaly_summary(anomaly_flags)

    # 9. LLM Insights
    insights_raw = generate_insights(payload.query, columns, rows)

    # 10. LLM Narrative
    narrative = build_narrative(
        question=payload.query,
        columns=columns,
        rows=rows,
        assumptions=assumptions,
        root_cause=insights_raw.get("root_cause", ""),
    )

    # 11. Hallucination guard
    h_check = hallucination_check(narrative, columns, rows)

    # 12. Trust layer
    trust = build_trust_layer(
        sql=sql,
        table_name=table_name,
        assumptions=assumptions,
        hallucination_check=h_check,
        row_count=row_count,
    )

    # 13. Visualization
    chart_type = choose_visualization(columns, rows)

    # 14. Persist to history + conversation turns
    history_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO query_history (id, workspace_id, user_id, query, sql_generated, narrative, chart_type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [history_id, payload.workspace_id, user["id"], payload.query, sql, narrative, chart_type],
    )
    _save_turn(payload.workspace_id, user["id"], "user", payload.query)
    _save_turn(payload.workspace_id, user["id"], "assistant", narrative)

    return QueryResponse(
        narrative=narrative,
        sql=sql,
        result=QueryResult(columns=columns, rows=rows, row_count=row_count),
        insights=InsightsOut(
            key_finding=insights_raw.get("key_finding", ""),
            anomalies=anomaly_strings,
            follow_up_questions=insights_raw.get("follow_up_questions", []),
        ),
        trust_layer=trust,
        visualization=chart_type,
        anomaly_flags=anomaly_flags,
        query_history_id=history_id,
    )
