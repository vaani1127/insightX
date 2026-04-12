"""
LLM-powered insight engine.
Given the question + actual query results, Claude produces:
  - key_finding (one sharp sentence)
  - root cause reasoning (for "why" questions)
  - follow-up questions the user should ask next
"""

import json
from typing import Any

from app.services.llm_client import chat

_SYSTEM = """You are an expert data analyst for InsightX, an AI analytics platform.
You have just executed a SQL query and received the results. Your job is to generate sharp, concise business insights.

Return ONLY valid JSON matching this exact structure:
{
  "key_finding": "<one sentence: the single most important insight from this data>",
  "root_cause": "<if the question asks 'why', explain the likely root cause based on the data patterns; otherwise empty string>",
  "follow_up_questions": ["<question 1>", "<question 2>", "<question 3>"]
}

Rules:
- key_finding must be specific with numbers (e.g. "North region leads with $1.2M revenue, 34% above average")
- Do not say "the data shows" or "based on the results" — just state the insight directly
- follow_up_questions should be natural next analytical steps the user would want
- If data is empty, set key_finding to "No data returned for this query" and leave others empty
- Never hallucinate numbers not present in the results
"""


def _format_results(columns: list[str], rows: list[list[Any]], max_rows: int = 20) -> str:
    if not rows:
        return "No rows returned."
    header = " | ".join(columns)
    separator = "-" * len(header)
    data_rows = [" | ".join(str(cell) for cell in row) for row in rows[:max_rows]]
    suffix = f"\n... ({len(rows) - max_rows} more rows)" if len(rows) > max_rows else ""
    return f"{header}\n{separator}\n" + "\n".join(data_rows) + suffix


def generate_insights(
    question: str,
    columns: list[str],
    rows: list[list[Any]],
) -> dict:
    results_text = _format_results(columns, rows)

    user_msg = f"""ORIGINAL QUESTION: {question}

QUERY RESULTS:
{results_text}

Generate the JSON insight now:"""

    response = chat(_SYSTEM, user_msg, max_tokens=600)

    # Strip markdown fences if present
    response = response.strip()
    if response.startswith("```"):
        response = response.split("\n", 1)[1]
        if "```" in response:
            response = response.rsplit("```", 1)[0]

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        # Fallback if LLM doesn't return valid JSON
        parsed = {
            "key_finding": f"Query returned {len(rows)} row(s).",
            "root_cause": "",
            "follow_up_questions": [],
        }

    return {
        "key_finding": parsed.get("key_finding", ""),
        "root_cause": parsed.get("root_cause", ""),
        "follow_up_questions": parsed.get("follow_up_questions", [])[:3],
    }
