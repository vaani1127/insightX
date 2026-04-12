from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import db
from app.models.schemas import ColumnInfo, TableSchema

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/{workspace_id}", response_model=TableSchema)
def get_schema(workspace_id: str, user: dict = Depends(get_current_user)) -> TableSchema:
    row = db.fetchone(
        "SELECT table_name, row_count FROM workspaces WHERE id = ? AND user_id = ?",
        [workspace_id, user["id"]],
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    if row[0] is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded to this workspace yet.")

    schema = db.table_schema(row[0])
    return TableSchema(
        table_name=row[0],
        columns=[ColumnInfo(name=c["name"], type=c["type"]) for c in schema],
        row_count=row[1] or 0,
    )
