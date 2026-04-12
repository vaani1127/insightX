"""
Resolves ambiguous time phrases into concrete date ranges.
Returns both the resolved SQL snippet and an Assumption record for the Trust Layer.
"""

import re
from datetime import date, timedelta

from app.models.schemas import Assumption


def _month_range(d: date) -> tuple[date, date]:
    first = d.replace(day=1)
    if first.month == 12:
        last = first.replace(day=31)
    else:
        last = first.replace(month=first.month + 1) - timedelta(days=1)
    return first, last


def resolve_time_phrases(question: str, today: date | None = None) -> tuple[str, list[Assumption]]:
    """
    Returns (modified_question_with_placeholders_replaced, assumptions_list).
    The SQL generator will receive both and use them to build accurate WHERE clauses.
    """
    today = today or date.today()
    assumptions: list[Assumption] = []
    q = question.lower()

    if "last month" in q:
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        start, end = _month_range(last_prev)
        assumptions.append(Assumption(
            field="time_range",
            value=f"{start.isoformat()} to {end.isoformat()}",
            reason=f"'last month' interpreted as {start.strftime('%B %Y')} ({start} → {end})",
        ))

    if "this month" in q:
        start, end = _month_range(today)
        assumptions.append(Assumption(
            field="time_range",
            value=f"{start.isoformat()} to {end.isoformat()}",
            reason=f"'this month' interpreted as {start.strftime('%B %Y')} ({start} → {end})",
        ))

    if "last week" in q:
        end = today - timedelta(days=today.weekday() + 1)
        start = end - timedelta(days=6)
        assumptions.append(Assumption(
            field="time_range",
            value=f"{start.isoformat()} to {end.isoformat()}",
            reason=f"'last week' interpreted as Mon {start} → Sun {end}",
        ))

    if "this week" in q:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        assumptions.append(Assumption(
            field="time_range",
            value=f"{start.isoformat()} to {end.isoformat()}",
            reason=f"'this week' interpreted as Mon {start} → Sun {end}",
        ))

    if re.search(r"last (quarter|q\d)", q):
        current_q = (today.month - 1) // 3
        if current_q == 0:
            start = date(today.year - 1, 10, 1)
            end = date(today.year - 1, 12, 31)
        else:
            start_month = (current_q - 1) * 3 + 1
            start = date(today.year, start_month, 1)
            end = today.replace(day=1) - timedelta(days=1)
        assumptions.append(Assumption(
            field="time_range",
            value=f"{start.isoformat()} to {end.isoformat()}",
            reason=f"'last quarter' interpreted as {start} → {end}",
        ))

    if "last year" in q:
        start = date(today.year - 1, 1, 1)
        end = date(today.year - 1, 12, 31)
        assumptions.append(Assumption(
            field="time_range",
            value=f"{start.isoformat()} to {end.isoformat()}",
            reason=f"'last year' interpreted as full year {today.year - 1}",
        ))

    if "this year" in q:
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
        assumptions.append(Assumption(
            field="time_range",
            value=f"{start.isoformat()} to {end.isoformat()}",
            reason=f"'this year' interpreted as full year {today.year}",
        ))

    return question, assumptions


def is_ambiguous(question: str) -> bool:
    vague = [
        "how are we doing", "what's going on", "give me an update",
        "what happened", "anything interesting", "tell me something",
    ]
    q = question.lower()
    return any(phrase in q for phrase in vague)
