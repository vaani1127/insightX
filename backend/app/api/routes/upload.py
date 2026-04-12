"""
Upload CSV or Excel → auto-ingest into DuckDB as a workspace table.
"""

import json
import re
import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import db
from app.models.schemas import UploadResponse

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def _safe_table_name(workspace_id: str) -> str:
    short = workspace_id.replace("-", "")[:12]
    return f"ds_{short}"


def _sanitize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns to safe SQL identifiers."""
    df.columns = [
        re.sub(r"[^0-9a-zA-Z_]", "_", str(c)).strip("_").lower() or f"col_{i}"
        for i, c in enumerate(df.columns)
    ]
    return df


@router.post("/{workspace_id}", response_model=UploadResponse)
async def upload_file(
    workspace_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> UploadResponse:
    # Verify workspace belongs to user
    ws = db.fetchone(
        "SELECT id FROM workspaces WHERE id = ? AND user_id = ?",
        [workspace_id, user["id"]],
    )
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported.")

    # Save upload directory per user/workspace
    upload_dir = Path(settings.uploads_dir) / user["id"] / workspace_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / (file.filename or f"upload{suffix}")

    content = await file.read()
    file_path.write_bytes(content)

    # Parse with pandas (handles both CSV and Excel)
    try:
        if suffix == ".csv":
            df = pd.read_csv(file_path, encoding_errors="replace")
        else:
            df = pd.read_excel(file_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}") from exc

    df = _sanitize_columns(df)

    # Save as temp CSV for DuckDB ingestion (DuckDB reads CSV natively)
    csv_path = upload_dir / "data.csv"
    df.to_csv(csv_path, index=False)

    table_name = _safe_table_name(workspace_id)
    try:
        columns, row_count = db.load_csv(table_name, str(csv_path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"DuckDB ingestion failed: {exc}") from exc

    # Update workspace metadata
    db.execute(
        "UPDATE workspaces SET table_name = ?, columns = ?, row_count = ?, file_path = ? WHERE id = ?",
        [table_name, json.dumps(columns), row_count, str(csv_path), workspace_id],
    )

    return UploadResponse(
        workspace_id=workspace_id,
        table_name=table_name,
        columns=columns,
        row_count=row_count,
    )
