"""
Metric dictionary — canonical definitions for common business terms.
Passed as context to the LLM so it generates consistent SQL regardless
of how the user phrases the question.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MetricDefinition:
    canonical_name: str
    aliases: list[str]
    sql_expression: str
    description: str


# These are generic definitions. They're injected into the SQL-gen prompt
# as a hint — the LLM will prefer these expressions over ad-hoc ones.
METRIC_DICTIONARY: list[MetricDefinition] = [
    MetricDefinition(
        canonical_name="revenue",
        aliases=["revenue", "sales", "net revenue", "total revenue", "income"],
        sql_expression="SUM(net_revenue_usd)",
        description="Total net revenue in USD",
    ),
    MetricDefinition(
        canonical_name="orders",
        aliases=["orders", "order count", "number of orders", "transactions"],
        sql_expression="COUNT(DISTINCT order_id)",
        description="Distinct order count",
    ),
    MetricDefinition(
        canonical_name="average_order_value",
        aliases=["aov", "average order value", "avg order value", "average sale"],
        sql_expression="AVG(net_revenue_usd)",
        description="Average order value in USD",
    ),
    MetricDefinition(
        canonical_name="active_users",
        aliases=["active users", "users", "unique users", "dau", "mau"],
        sql_expression="COUNT(DISTINCT user_id)",
        description="Distinct active users",
    ),
    MetricDefinition(
        canonical_name="churn_rate",
        aliases=["churn", "churn rate", "attrition"],
        sql_expression="AVG(churn_rate)",
        description="Average churn rate as a proportion",
    ),
    MetricDefinition(
        canonical_name="costs",
        aliases=["cost", "costs", "expenses", "spending", "expenditure"],
        sql_expression="SUM(cost_usd)",
        description="Total costs in USD",
    ),
    MetricDefinition(
        canonical_name="signups",
        aliases=["signups", "new signups", "registrations", "new users"],
        sql_expression="SUM(signups)",
        description="Total new signups",
    ),
]


def build_metric_context() -> str:
    """Return a formatted string listing all metric definitions for the LLM prompt."""
    lines = ["METRIC DICTIONARY (always use these expressions when they apply):"]
    for m in METRIC_DICTIONARY:
        aliases = ", ".join(f'"{a}"' for a in m.aliases)
        lines.append(f"  - {m.canonical_name}: {m.sql_expression}  [{aliases}]  — {m.description}")
    return "\n".join(lines)
