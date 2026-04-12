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
