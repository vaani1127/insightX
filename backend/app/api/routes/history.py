from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import db
from app.models.schemas import HistoryItem

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/{workspace_id}", response_model=list[HistoryItem])
def get_history(workspace_id: str, user: dict = Depends(get_current_user)) -> list[HistoryItem]:
    ws = db.fetchone(
        "SELECT id FROM workspaces WHERE id = ? AND user_id = ?",
        [workspace_id, user["id"]],
    )
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    rows = db.fetchall(
        "SELECT id, query, sql_generated, narrative, chart_type, created_at "
        "FROM query_history WHERE workspace_id = ? AND user_id = ? "
        "ORDER BY created_at DESC LIMIT 50",
        [workspace_id, user["id"]],
    )
    return [
        HistoryItem(
            id=r[0],
            query=r[1],
            sql_generated=r[2],
            narrative=r[3],
            chart_type=r[4],
            created_at=str(r[5]),
        )
        for r in rows
    ]


@router.delete("/{workspace_id}", status_code=204)
def clear_history(workspace_id: str, user: dict = Depends(get_current_user)) -> None:
    db.execute(
        "DELETE FROM query_history WHERE workspace_id = ? AND user_id = ?",
        [workspace_id, user["id"]],
    )
    db.execute(
        "DELETE FROM conversation_turns WHERE workspace_id = ? AND user_id = ?",
        [workspace_id, user["id"]],
    )
