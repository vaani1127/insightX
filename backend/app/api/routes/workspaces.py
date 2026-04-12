import json
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import db
from app.models.schemas import WorkspaceCreate, WorkspaceOut

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceOut, status_code=201)
def create_workspace(payload: WorkspaceCreate, user: dict = Depends(get_current_user)) -> WorkspaceOut:
    ws_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO workspaces (id, user_id, name, description) VALUES (?, ?, ?, ?)",
        [ws_id, user["id"], payload.name, payload.description],
    )
    return WorkspaceOut(
        id=ws_id,
        name=payload.name,
        description=payload.description,
        table_name=None,
        columns=None,
        row_count=0,
        created_at="",
    )


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(user: dict = Depends(get_current_user)) -> list[WorkspaceOut]:
    rows = db.fetchall(
        "SELECT id, name, description, table_name, columns, row_count, created_at "
        "FROM workspaces WHERE user_id = ? ORDER BY created_at DESC",
        [user["id"]],
    )
    result = []
    for r in rows:
        cols = json.loads(r[4]) if r[4] else None
        result.append(
            WorkspaceOut(
                id=r[0],
                name=r[1],
                description=r[2] or "",
                table_name=r[3],
                columns=cols,
                row_count=r[5] or 0,
                created_at=str(r[6]),
            )
        )
    return result


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(workspace_id: str, user: dict = Depends(get_current_user)) -> WorkspaceOut:
    row = db.fetchone(
        "SELECT id, name, description, table_name, columns, row_count, created_at "
        "FROM workspaces WHERE id = ? AND user_id = ?",
        [workspace_id, user["id"]],
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    cols = json.loads(row[4]) if row[4] else None
    return WorkspaceOut(
        id=row[0],
        name=row[1],
        description=row[2] or "",
        table_name=row[3],
        columns=cols,
        row_count=row[5] or 0,
        created_at=str(row[6]),
    )


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(workspace_id: str, user: dict = Depends(get_current_user)) -> None:
    row = db.fetchone(
        "SELECT table_name FROM workspaces WHERE id = ? AND user_id = ?",
        [workspace_id, user["id"]],
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    if row[0]:
        db.drop_table(row[0])
    db.execute("DELETE FROM workspaces WHERE id = ?", [workspace_id])
    db.execute("DELETE FROM query_history WHERE workspace_id = ?", [workspace_id])
    db.execute("DELETE FROM conversation_turns WHERE workspace_id = ?", [workspace_id])
