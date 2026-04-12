from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, EmailStr


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    email: str


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------
class WorkspaceCreate(BaseModel):
    name: str
    description: str = ""


class WorkspaceOut(BaseModel):
    id: str
    name: str
    description: str
    table_name: Optional[str]
    columns: Optional[list[str]]
    row_count: int
    created_at: str


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
class UploadResponse(BaseModel):
    workspace_id: str
    table_name: str
    columns: list[str]
    row_count: int


# ---------------------------------------------------------------------------
# Query pipeline
# ---------------------------------------------------------------------------
class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    workspace_id: str
    user_role: str = "analyst"


class Assumption(BaseModel):
    field: str
    value: str
    reason: str


class HallucinationCheck(BaseModel):
    passed: bool
    discrepancies: list[str] = []


class TrustLayerOut(BaseModel):
    sql: str
    confidence: Literal["high", "medium", "low"]
    confidence_reason: str
    data_sources: list[str]
    metrics_used: list[str]
    assumptions: list[Assumption]
    hallucination_check: HallucinationCheck


class AnomalyFlag(BaseModel):
    column: str
    value: float
    z_score: float
    severity: Literal["warning", "critical"]


class InsightsOut(BaseModel):
    key_finding: str
    anomalies: list[str]
    follow_up_questions: list[str]


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int


class QueryResponse(BaseModel):
    narrative: str
    sql: str
    result: QueryResult
    insights: InsightsOut
    trust_layer: TrustLayerOut
    visualization: Literal["bar", "line", "pie", "metric", "table"]
    anomaly_flags: list[AnomalyFlag] = []
    query_history_id: str


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
class FeedbackRequest(BaseModel):
    query_history_id: str
    was_helpful: bool
    correction: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str = "logged"


# ---------------------------------------------------------------------------
# Schema / metadata
# ---------------------------------------------------------------------------
class ColumnInfo(BaseModel):
    name: str
    type: str


class TableSchema(BaseModel):
    table_name: str
    columns: list[ColumnInfo]
    row_count: int


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
class HistoryItem(BaseModel):
    id: str
    query: str
    sql_generated: Optional[str]
    narrative: Optional[str]
    chart_type: Optional[str]
    created_at: str
