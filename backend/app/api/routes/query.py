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
    HallucinationCheck,
    InsightsOut,
    QueryRequest,
    QueryResponse,
    QueryResult,
    TrustLayerOut,
)
from app.services.anomaly_detector import anomaly_summary, detect_anomalies
from app.services.disambiguation import is_ambiguous, resolve_time_phrases
from app.services.explanation_generator import build_narrative
from app.services.hallucination_guard import check as hallucination_check
from app.services.insight_engine import generate_insights
from app.services.privacy_guard import evaluate_sql, filter_result, filter_schema
from app.services.sql_generator import SQLGenerationError, generate_sql
from app.services.trust_layer import build_trust_layer
from app.services.visualization import choose_visualization

router = APIRouter(prefix="/query", tags=["query"])

_META_PRIVACY_PHRASES = [
    "why can't i", "why cant i", "why can i not", "why cannot i",
    "why is", "why are", "why won't", "why wont",
    "why doesn't", "why doesnt", "why isn't", "why isnt",
    "can i access", "can i see", "can i view", "can i get",
    "how do i access", "why blocked", "why restricted",
]


def _privacy_preflight(
    question: str,
    redacted_columns: list[str],
    user_role: str,
    workspace_id: str,
    user_id: str,
) -> QueryResponse | None:
    """
    Returns a ready QueryResponse if the query is explicitly about blocked data,
    so we skip SQL generation entirely and give a clear privacy explanation.
    Returns None if the query should proceed normally.
    """
    q = question.lower()
    matched_cols = [col for col in redacted_columns if col.lower() in q]
    is_meta = any(phrase in q for phrase in _META_PRIVACY_PHRASES)

    if not matched_cols and not is_meta:
        return None

    if matched_cols:
        col_list = ", ".join(matched_cols)
        narrative = (
            f"The column(s) **{col_list}** are restricted under the privacy policy for your role ('{user_role}'). "
            f"This data cannot be listed, exported, or queried directly. "
            f"If you need access, contact your admin to request elevated permissions."
        )
        key_finding = f"Access denied: {col_list} — privacy-restricted for role '{user_role}'."
        follow_ups = ["Show me the non-sensitive columns", "Give me a summary of the data"]
    else:
        # Meta question about why something is blocked
        narrative = (
            f"Some columns in this dataset are restricted by the privacy policy for your role ('{user_role}'). "
            f"Restricted columns include personally identifiable or financially sensitive data such as "
            f"credit card numbers, SSNs, passwords, and national IDs. "
            f"These columns are hidden to comply with data protection standards. "
            f"Contact your admin if you need elevated access."
        )
        key_finding = "Privacy policy explanation — no data was queried."
        follow_ups = ["What columns can I access?", "Give me a summary of the data"]

    response_id = str(uuid.uuid4())
    _save_turn(workspace_id, user_id, "user", question)
    _save_turn(workspace_id, user_id, "assistant", narrative)
    db.execute(
        "INSERT INTO query_history (id, workspace_id, user_id, query, sql_generated, narrative, chart_type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [response_id, workspace_id, user_id, question, "", narrative, "table"],
    )
    return QueryResponse(
        narrative=narrative,
        sql="",
        result=QueryResult(columns=[], rows=[], row_count=0),
        insights=InsightsOut(
            key_finding=key_finding,
            anomalies=[],
            follow_up_questions=follow_ups,
        ),
        trust_layer=TrustLayerOut(
            sql="",
            confidence="low",
            confidence_reason="Query targets privacy-restricted columns.",
            data_sources=[],
            metrics_used=[],
            assumptions=[],
            hallucination_check=HallucinationCheck(passed=True, discrepancies=[]),
        ),
        visualization="table",
        anomaly_flags=[],
        query_history_id=response_id,
    )


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

    # 4. Get table schema — filter out columns blocked for this role before LLM sees them
    user_role = user.get("role", "analyst")
    full_schema = db.table_schema(table_name)
    schema, redacted_columns = filter_schema(full_schema, user_role)

    # 4.5a Privacy pre-flight — catch queries explicitly targeting blocked columns or meta questions
    preflight = _privacy_preflight(
        question=payload.query,
        redacted_columns=redacted_columns,
        user_role=user_role,
        workspace_id=payload.workspace_id,
        user_id=user["id"],
    )
    if preflight:
        return preflight

    # 4.5b Reject ambiguous queries — ask for clarification instead of guessing
    if is_ambiguous(payload.query):
        numeric_cols = [
            c["name"] for c in schema
            if any(t in c["type"].lower() for t in ("int", "float", "double", "decimal", "bigint", "hugeint"))
        ]
        follow_ups = [f"Show me total {col}" for col in numeric_cols[:3]]
        if not follow_ups:
            follow_ups = ["Show me a summary of all data", "What are the top 5 rows?", "Show row counts by category"]

        col_examples = ", ".join(f'"{c["name"]}"' for c in schema[:4])
        clarification_msg = (
            f'Your question is a bit broad — I want to make sure I give you the right answer. '
            f'This dataset has columns like {col_examples}. '
            f'Could you clarify what metric or dimension you\'re interested in? '
            f'For example: "{follow_ups[0]}".'
        )

        clarification_id = str(uuid.uuid4())
        _save_turn(payload.workspace_id, user["id"], "user", payload.query)
        _save_turn(payload.workspace_id, user["id"], "assistant", clarification_msg)
        db.execute(
            "INSERT INTO query_history (id, workspace_id, user_id, query, sql_generated, narrative, chart_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [clarification_id, payload.workspace_id, user["id"], payload.query, "", clarification_msg, "table"],
        )
        return QueryResponse(
            narrative=clarification_msg,
            sql="",
            result=QueryResult(columns=[], rows=[], row_count=0),
            insights=InsightsOut(
                key_finding="Clarification needed before I can answer accurately.",
                anomalies=[],
                follow_up_questions=follow_ups,
            ),
            trust_layer=TrustLayerOut(
                sql="",
                confidence="low",
                confidence_reason="Query is too vague to answer without making unsupported assumptions.",
                data_sources=[],
                metrics_used=[],
                assumptions=[],
                hallucination_check=HallucinationCheck(passed=True, discrepancies=[]),
            ),
            visualization="table",
            anomaly_flags=[],
            query_history_id=clarification_id,
        )

    # 5. Generate SQL via LLM
    try:
        sql = generate_sql(
            question=payload.query,
            schema=schema,
            table_name=table_name,
            assumptions=assumptions,
            conversation_history=history,
            excluded_columns=redacted_columns if redacted_columns else None,
        )
    except SQLGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 6. Privacy guard — if LLM still hallucinated a blocked column, fall back to
    #    an explicit safe SELECT rather than hard-blocking the entire response.
    privacy = evaluate_sql(sql, user.get("role", "analyst"))
    if not privacy.allowed:
        safe_cols = ", ".join(f'"{c["name"]}"' for c in schema)
        sql = f'SELECT {safe_cols} FROM "{table_name}" LIMIT 500'

    # 7. Execute SQL
    try:
        columns, rows = db.execute_query(sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"SQL execution failed: {exc}") from exc

    # 7.5 Strip sensitive columns from results — catches SELECT * and any LLM hallucinations
    columns, rows, result_redacted = filter_result(columns, rows, user_role)
    if result_redacted:
        redacted_columns = list(set(redacted_columns + result_redacted))

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
    if redacted_columns:
        from app.models.schemas import Assumption as Asmp
        assumptions = assumptions + [Asmp(
            field="privacy_filter",
            value=", ".join(redacted_columns),
            reason=f"Columns not shown due to privacy policy: {', '.join(redacted_columns)}",
        )]
        privacy_note = (
            f"⚠ {len(redacted_columns)} column(s) were hidden because they contain sensitive data "
            f"({', '.join(redacted_columns)}). Only non-sensitive columns are shown below."
        )
        insights_raw["key_finding"] = privacy_note
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
