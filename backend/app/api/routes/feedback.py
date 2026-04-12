import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import db
from app.models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackRequest, user: dict = Depends(get_current_user)) -> FeedbackResponse:
    exists = db.fetchone(
        "SELECT id FROM query_history WHERE id = ? AND user_id = ?",
        [payload.query_history_id, user["id"]],
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="Query history entry not found.")

    db.execute(
        "INSERT INTO feedback (id, query_history_id, user_id, was_helpful, correction) "
        "VALUES (?, ?, ?, ?, ?)",
        [str(uuid.uuid4()), payload.query_history_id, user["id"],
         payload.was_helpful, payload.correction],
    )
    return FeedbackResponse()
