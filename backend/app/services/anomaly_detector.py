"""
Statistical anomaly detection on query results.
Uses Z-score for outlier detection on numeric columns.
Returns flagged rows with severity levels.
"""

import math
from typing import Any

from app.models.schemas import AnomalyFlag


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stddev(values: list[float], mean: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def detect_anomalies(columns: list[str], rows: list[list[Any]]) -> list[AnomalyFlag]:
    """
    For each numeric column, compute Z-scores across all rows.
    Flag values with |Z| >= 2.0 as warning, |Z| >= 3.0 as critical.
    """
    if len(rows) < 3:
        return []  # Not enough data for meaningful stats

    flags: list[AnomalyFlag] = []

    for col_idx, col_name in enumerate(columns):
        # Extract numeric values
        values: list[float] = []
        for row in rows:
            val = row[col_idx]
            if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(float(val)):
                values.append(float(val))

        if len(values) < 3:
            continue

        mean = _mean(values)
        std = _stddev(values, mean)

        if std == 0:
            continue

        for i, val in enumerate(values):
            z = abs(val - mean) / std
            if z >= 2.0:
                severity = "critical" if z >= 3.0 else "warning"
                flags.append(AnomalyFlag(
                    column=col_name,
                    value=val,
                    z_score=round(z, 2),
                    severity=severity,
                ))

    return flags


def anomaly_summary(flags: list[AnomalyFlag]) -> list[str]:
    """Human-readable anomaly strings for the InsightsOut.anomalies field."""
    summaries = []
    for f in flags:
        direction = "high" if f.z_score > 0 else "low"
        summaries.append(
            f"{f.column} has an unusually {direction} value ({f.value:,.2f}, Z={f.z_score}) — "
            f"{'⚠ warning' if f.severity == 'warning' else '🔴 critical'}"
        )
    return summaries
