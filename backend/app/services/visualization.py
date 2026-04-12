"""
Rule-based chart type selector.
Looks at column types and result shape to pick the best visualization.
"""

from typing import Any, Literal

ChartType = Literal["bar", "line", "pie", "metric", "table"]

_TIME_KEYWORDS = {"date", "week", "month", "year", "quarter", "day", "time", "period", "created"}
_CATEGORY_KEYWORDS = {"region", "product", "category", "channel", "department", "type", "segment", "status"}


def choose_visualization(
    columns: list[str],
    rows: list[list[Any]],
) -> ChartType:
    if not rows:
        return "table"

    num_rows = len(rows)
    num_cols = len(columns)
    col_names_lower = [c.lower() for c in columns]

    # Single scalar value → metric card
    if num_rows == 1 and num_cols == 1:
        return "metric"

    # Single row, multiple columns → metric or table
    if num_rows == 1:
        return "table"

    has_time_col = any(kw in col for col in col_names_lower for kw in _TIME_KEYWORDS)
    has_category_col = any(kw in col for col in col_names_lower for kw in _CATEGORY_KEYWORDS)
    has_numeric = any(
        isinstance(row[i], (int, float)) and not isinstance(row[i], bool)
        for row in rows[:5]
        for i in range(num_cols)
    )

    if not has_numeric:
        return "table"

    # Time series → line chart
    if has_time_col and num_rows >= 3:
        return "line"

    # Small categorical breakdown → pie
    if has_category_col and 2 <= num_rows <= 6:
        return "pie"

    # Larger categorical breakdown → bar
    if has_category_col or (num_rows <= 20 and num_cols <= 3):
        return "bar"

    return "table"
