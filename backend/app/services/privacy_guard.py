"""
Column-level privacy enforcement.
Blocks queries that reference sensitive columns for roles without permission.
"""

from dataclasses import dataclass

SENSITIVE_COLUMNS = {
    "email", "phone", "mobile", "ssn", "dob", "date_of_birth",
    "customer_name", "full_name", "address", "postcode", "zip",
    "credit_card", "card_number", "password", "salary", "income",
    "national_id", "passport",
}

# Role → set of columns that are blocked for that role
ROLE_POLICY: dict[str, set[str]] = {
    "viewer":  SENSITIVE_COLUMNS,
    "analyst": {"ssn", "credit_card", "card_number", "password", "national_id", "passport"},
    "admin":   set(),  # admins can see everything
}


@dataclass
class PrivacyDecision:
    allowed: bool
    blocked_columns: list[str]
    policy_reason: str


def filter_schema(schema: list[dict], user_role: str) -> tuple[list[dict], list[str]]:
    """
    Returns (allowed_columns, redacted_column_names).
    Strip sensitive columns from the schema before passing to the SQL generator
    so the LLM never generates SQL referencing blocked columns.
    """
    blocked = ROLE_POLICY.get(user_role, ROLE_POLICY["viewer"])
    allowed = [c for c in schema if c["name"].lower() not in blocked]
    redacted = [c["name"] for c in schema if c["name"].lower() in blocked]
    return allowed, redacted


def filter_result(
    columns: list[str], rows: list[list], user_role: str
) -> tuple[list[str], list[list], list[str]]:
    """
    Strip sensitive columns from query results after execution.
    Handles SELECT * and any other case where blocked columns slip through.
    Returns (safe_columns, safe_rows, redacted_column_names).
    """
    blocked = ROLE_POLICY.get(user_role, ROLE_POLICY["viewer"])
    safe_idx = [i for i, col in enumerate(columns) if col.lower() not in blocked]
    redacted = [col for col in columns if col.lower() in blocked]
    safe_columns = [columns[i] for i in safe_idx]
    safe_rows = [[row[i] for i in safe_idx] for row in rows]
    return safe_columns, safe_rows, redacted


def evaluate_sql(sql: str, user_role: str) -> PrivacyDecision:
    lowered = sql.lower()
    blocked = ROLE_POLICY.get(user_role, ROLE_POLICY["viewer"])
    found: list[str] = [col for col in SENSITIVE_COLUMNS if col in lowered and col in blocked]

    if found:
        return PrivacyDecision(
            allowed=False,
            blocked_columns=found,
            policy_reason=(
                f"Role '{user_role}' is not permitted to access columns: {', '.join(found)}. "
                "Contact your admin to request elevated access."
            ),
        )
    return PrivacyDecision(allowed=True, blocked_columns=[], policy_reason="")
