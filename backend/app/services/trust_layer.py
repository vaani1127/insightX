"""
Builds the Trust Layer object — the full transparency record for every query.
"""

from app.models.schemas import Assumption, HallucinationCheck, TrustLayerOut
from app.services.metric_dictionary import METRIC_DICTIONARY


def _detect_metrics_used(sql: str) -> list[str]:
    """Scan the SQL for known metric expressions and return their canonical names."""
    sql_lower = sql.lower()
    found = []
    seen = set()
    for metric in METRIC_DICTIONARY:
        expr_lower = metric.sql_expression.lower()
        if expr_lower in sql_lower and metric.canonical_name not in seen:
            found.append(metric.canonical_name)
            seen.add(metric.canonical_name)
    return found


def _confidence_score(
    hallucination_check: HallucinationCheck,
    row_count: int,
    assumptions: list[Assumption],
) -> tuple[str, str]:
    if not hallucination_check.passed:
        return "low", "Narrative discrepancies detected by hallucination guard."
    if row_count == 0:
        return "low", "Query returned no rows — result may be filtered too aggressively."
    if len(assumptions) >= 3:
        return "medium", "Multiple time/filter assumptions were made — verify they match your intent."
    if assumptions:
        return "medium", "One or more temporal assumptions were made (see below)."
    return "high", "All narrative claims verified against query results. No assumptions required."


def build_trust_layer(
    sql: str,
    table_name: str,
    assumptions: list[Assumption],
    hallucination_check: HallucinationCheck,
    row_count: int,
) -> TrustLayerOut:
    metrics_used = _detect_metrics_used(sql)
    confidence, reason = _confidence_score(hallucination_check, row_count, assumptions)

    return TrustLayerOut(
        sql=sql,
        confidence=confidence,
        confidence_reason=reason,
        data_sources=[table_name],
        metrics_used=metrics_used,
        assumptions=assumptions,
        hallucination_check=hallucination_check,
    )
