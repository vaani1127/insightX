"""
LLM-backed text-to-SQL generator.
Claude receives: the exact table schema, metric dictionary, conversation history,
resolved time assumptions, and the user's question — then returns valid DuckDB SQL.
"""

import re

from app.models.schemas import Assumption
from app.services.llm_client import chat_with_history
from app.services.metric_dictionary import build_metric_context

_SYSTEM = """You are an expert DuckDB SQL generator for a data analytics platform called InsightX.

Your job: given a user question, the table schema, and metric definitions, write a single valid DuckDB SQL SELECT statement.

Rules:
1. Output ONLY the raw SQL — no markdown, no backticks, no explanation.
2. Use DuckDB syntax (e.g. DATE_TRUNC, STRFTIME, EPOCH, etc.).
3. Always use the exact table name and column names from the schema — never guess column names.
4. Use the metric dictionary expressions when they match the user's intent (e.g. always SUM(net_revenue_usd) for revenue, never COUNT(*)).
5. If a time assumption is provided, inject the exact date range into a WHERE clause.
6. If the question asks for a breakdown/comparison, use GROUP BY appropriately.
7. If the question asks for a trend over time, GROUP BY a date bucket (e.g. DATE_TRUNC('month', date_col)).
8. If the question asks for a top-N, use ORDER BY + LIMIT.
9. If the question is genuinely unanswerable from this schema, output exactly: CANNOT_ANSWER
10. Never use DROP, DELETE, INSERT, UPDATE, CREATE, or any DDL/DML — SELECT only.
11. If the question asks for a "summary", "overview", "describe", "profile", or "tell me about the data" — generate a dataset profile query: SELECT COUNT(*) as total_records, and COUNT(DISTINCT col) AS unique_{col} for every non-numeric column in the schema.
12. If the question asks to "show", "display", "preview", or "sample" the data, return SELECT * FROM table LIMIT 10.
13. Interpret short or terse questions generously using the schema context. "give summary", "summarise", "overview", "what's in here" all mean rule 11. Never return CANNOT_ANSWER for summary/overview/display intents.
"""


class SQLGenerationError(Exception):
    pass


_SUMMARY_PHRASES = {
    "give summary", "summary", "summarise", "summarize", "give me a summary",
    "overview", "give overview", "give me an overview", "describe the data",
    "describe data", "what's in the data", "whats in the data",
    "tell me about the data", "data overview", "data summary", "profile the data",
    "profile data", "show summary", "show me a summary",
}

_SAMPLE_PHRASES = {
    "show data", "display data", "show me the data", "show me data",
    "preview", "preview data", "show sample", "sample data", "first rows",
    "show rows", "show records",
}


def _normalise_question(question: str, schema: list[dict], table_name: str) -> str | None:
    """
    Returns a direct SQL string for well-known terse intents, bypassing the LLM.
    Returns None if the question should go through normal LLM generation.
    """
    q = question.strip().lower().rstrip(".")

    if q in _SUMMARY_PHRASES or any(q.startswith(p) for p in _SUMMARY_PHRASES):
        distinct_parts = ", ".join(
            f'COUNT(DISTINCT "{c["name"]}") AS "unique_{c["name"]}"'
            for c in schema
            if not any(t in c["type"].lower() for t in ("int", "float", "double", "decimal", "bigint", "hugeint"))
        )
        if distinct_parts:
            return f'SELECT COUNT(*) AS total_records, {distinct_parts} FROM "{table_name}"'
        return f'SELECT COUNT(*) AS total_records FROM "{table_name}"'

    if q in _SAMPLE_PHRASES or any(q.startswith(p) for p in _SAMPLE_PHRASES):
        safe_cols = ", ".join(f'"{c["name"]}"' for c in schema)
        return f'SELECT {safe_cols} FROM "{table_name}" LIMIT 10'

    return None


def _build_schema_block(schema: list[dict], table_name: str, excluded_columns: list[str] | None = None) -> str:
    cols = "\n".join(f"  {c['name']} ({c['type']})" for c in schema)
    block = f"TABLE: {table_name}\nCOLUMNS:\n{cols}"
    if excluded_columns:
        block += f"\n\nPRIVACY POLICY — NEVER reference these columns under any circumstances: {', '.join(excluded_columns)}"
    return block


def _build_assumption_block(assumptions: list[Assumption]) -> str:
    if not assumptions:
        return ""
    lines = ["TIME ASSUMPTIONS (inject these as WHERE clauses):"]
    for a in assumptions:
        lines.append(f"  - {a.field}: {a.value}  ({a.reason})")
    return "\n".join(lines)


def generate_sql(
    question: str,
    schema: list[dict],
    table_name: str,
    assumptions: list[Assumption],
    conversation_history: list[dict],
    excluded_columns: list[str] | None = None,
) -> str:
    """
    Returns a valid DuckDB SQL SELECT string.
    Raises SQLGenerationError if the question cannot be answered.
    """
    # Fast path: handle terse well-known intents without an LLM call
    direct_sql = _normalise_question(question, schema, table_name)
    if direct_sql:
        return direct_sql

    schema_block = _build_schema_block(schema, table_name, excluded_columns)
    assumption_block = _build_assumption_block(assumptions)
    metric_block = build_metric_context()

    context_parts = [schema_block, metric_block]
    if assumption_block:
        context_parts.append(assumption_block)

    context = "\n\n".join(context_parts)

    # Build messages: inject context into the first user turn, then replay history
    history_messages: list[dict] = []
    for turn in conversation_history[-6:]:  # last 3 pairs max
        history_messages.append({"role": turn["role"], "content": turn["content"]})

    # Final user message with full context
    user_msg = f"""{context}

USER QUESTION: {question}

Write the DuckDB SQL SELECT statement now:"""

    messages = history_messages + [{"role": "user", "content": user_msg}]

    sql = chat_with_history(_SYSTEM, messages, max_tokens=512)

    # Strip any accidental markdown fences
    sql = re.sub(r"```[a-z]*\n?", "", sql).strip()

    if "CANNOT_ANSWER" in sql.upper():
        raise SQLGenerationError(
            "I couldn't find relevant data in your dataset to answer that question. "
            "Try rephrasing or check the column names in the Schema panel."
        )

    # Safety: block any non-SELECT statements
    first_word = sql.split()[0].upper() if sql.split() else ""
    if first_word not in ("SELECT", "WITH"):
        raise SQLGenerationError(f"Generated statement is not a SELECT: {sql[:80]}")

    return sql
