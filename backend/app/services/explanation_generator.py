"""
LLM-powered narrative generator.
Produces a plain-English paragraph explaining what the data shows,
tuned for non-technical readers (think: a NatWest executive).
"""

from typing import Any

from app.models.schemas import Assumption
from app.services.llm_client import chat

_SYSTEM = """You are InsightX, an AI data analyst built for NatWest Group.
Your job: write a clear, confident narrative explaining query results to a non-technical business stakeholder.

Rules:
- Write 2-4 sentences maximum. No bullet points.
- Start with the answer directly — never say "The query shows..." or "Based on the data..."
- Include the key number(s) from the results.
- If any assumptions were made (e.g. time range), mention them naturally in one phrase.
- Use professional, concise financial language.
- If no data was found, say so clearly and suggest the user check their filters.
"""


def _format_sample(columns: list[str], rows: list[list[Any]], max_rows: int = 10) -> str:
    if not rows:
        return "No rows returned."
    lines = [" | ".join(str(c) for c in columns)]
    for row in rows[:max_rows]:
        lines.append(" | ".join(str(c) for c in row))
    if len(rows) > max_rows:
        lines.append(f"... {len(rows) - max_rows} more rows")
    return "\n".join(lines)


def build_narrative(
    question: str,
    columns: list[str],
    rows: list[list[Any]],
    assumptions: list[Assumption],
    root_cause: str = "",
) -> str:
    assumption_text = ""
    if assumptions:
        parts = [f"{a.field}: {a.value}" for a in assumptions]
        assumption_text = f"\nAssumptions made: {'; '.join(parts)}"

    root_cause_text = f"\nRoot cause context: {root_cause}" if root_cause else ""
    sample = _format_sample(columns, rows)

    user_msg = f"""QUESTION: {question}{assumption_text}{root_cause_text}

RESULTS:
{sample}

Write the narrative now:"""

    return chat(_SYSTEM, user_msg, max_tokens=300)
