import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.auth import create_access_token
from app.core.database import db
from app.core.security import hash_password, verify_password
from app.models.schemas import AuthResponse, LoginRequest, SignupRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest) -> AuthResponse:
    existing = db.fetchone("SELECT id FROM users WHERE email = ?", [payload.email])
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (id, email, username, password_hash) VALUES (?, ?, ?, ?)",
        [user_id, payload.email, payload.username, hash_password(payload.password)],
    )
    token = create_access_token(user_id, payload.email, payload.username)
    return AuthResponse(
        access_token=token,
        user_id=user_id,
        username=payload.username,
        email=payload.email,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    row = db.fetchone(
        "SELECT id, username, password_hash FROM users WHERE email = ?", [payload.email]
    )
    if row is None or not verify_password(payload.password, row[2]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(row[0], payload.email, row[1])
    return AuthResponse(
        access_token=token,
        user_id=row[0],
        username=row[1],
        email=payload.email,
    )


@router.get("/me")
def me(user: dict = __import__("fastapi").Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user)) -> dict:
    return user
