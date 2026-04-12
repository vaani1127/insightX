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
"""


class SQLGenerationError(Exception):
    pass


def _build_schema_block(schema: list[dict], table_name: str) -> str:
    cols = "\n".join(f"  {c['name']} ({c['type']})" for c in schema)
    return f"TABLE: {table_name}\nCOLUMNS:\n{cols}"


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
) -> str:
    """
    Returns a valid DuckDB SQL SELECT string.
    Raises SQLGenerationError if the question cannot be answered.
    """
    schema_block = _build_schema_block(schema, table_name)
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
