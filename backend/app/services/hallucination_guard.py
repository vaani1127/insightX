"""
Semantic Hallucination Guard — InsightX's key differentiator.

How it works:
1. Extract all numeric claims from the LLM-generated narrative
   (e.g. "revenue increased by 15%" → {"15%", "15"})
2. Extract all numeric values from the actual SQL result
3. For each narrative claim, check if a matching value exists in the result
4. Flag discrepancies

This catches cases where the LLM hallucinates numbers that don't match
the real query output — a critical trust signal for a financial platform.
"""

import re
from typing import Any

from app.models.schemas import HallucinationCheck


# Patterns to extract numeric values from text
_NUM_PATTERN = re.compile(
    r"""
    (?:
        [-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?   # e.g. 1,200,000.50
        |[-+]?\d+(?:\.\d+)?                   # e.g. 1200 or 3.14
    )
    (?:[kKmMbB%])?                            # optional suffix
    """,
    re.VERBOSE,
)


def _normalize_number(raw: str) -> float | None:
    """Convert a string like '1.2M', '15%', '3,000' to float."""
    s = raw.replace(",", "").strip()
    multipliers = {"k": 1e3, "m": 1e6, "b": 1e9}
    suffix = s[-1].lower() if s and s[-1].lower() in multipliers else None
    if suffix:
        s = s[:-1]
    if s.endswith("%"):
        s = s[:-1]
    try:
        val = float(s)
        if suffix:
            val *= multipliers[suffix]
        return val
    except ValueError:
        return None


def _extract_numbers_from_text(text: str) -> list[float]:
    raw_matches = _NUM_PATTERN.findall(text)
    results = []
    for raw in raw_matches:
        n = _normalize_number(raw)
        if n is not None:
            results.append(n)
    return results


def _extract_numbers_from_result(columns: list[str], rows: list[list[Any]]) -> set[float]:
    values: set[float] = set()
    for row in rows:
        for cell in row:
            if isinstance(cell, (int, float)) and not isinstance(cell, bool):
                values.add(float(cell))
    return values


def _close_enough(claimed: float, actual_values: set[float], tolerance: float = 0.05) -> bool:
    """Return True if any actual value is within tolerance% of the claimed value."""
    if claimed == 0:
        return 0.0 in actual_values
    for actual in actual_values:
        if actual == 0:
            continue
        if abs(claimed - actual) / max(abs(claimed), abs(actual)) <= tolerance:
            return True
    return False


def check(
    narrative: str,
    columns: list[str],
    rows: list[list[Any]],
) -> HallucinationCheck:
    """
    Compare numeric claims in the narrative against actual query results.
    Returns a HallucinationCheck with passed=True if all claims are supported.
    """
    if not rows:
        # No data — narrative should acknowledge this
        if any(phrase in narrative.lower() for phrase in ["no data", "no results", "couldn't find", "not found"]):
            return HallucinationCheck(passed=True)
        return HallucinationCheck(
            passed=False,
            discrepancies=["Narrative makes claims but query returned no rows."],
        )

    claimed_numbers = _extract_numbers_from_text(narrative)
    actual_numbers = _extract_numbers_from_result(columns, rows)

    if not claimed_numbers:
        return HallucinationCheck(passed=True)

    discrepancies: list[str] = []
    for claimed in claimed_numbers:
        # Skip very small numbers (likely percentages or indices that won't match)
        if abs(claimed) < 1:
            continue
        if not _close_enough(claimed, actual_numbers):
            discrepancies.append(
                f"Narrative mentions {claimed:,.2f} but this value was not found in query results."
            )

    return HallucinationCheck(
        passed=len(discrepancies) == 0,
        discrepancies=discrepancies,
    )
