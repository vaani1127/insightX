from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, feedback, history, query, schema, upload, workspaces
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — tighten allow_origins in production to your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(schema.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": settings.version}
