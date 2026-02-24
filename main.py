"""
School Grades Agent API

Main FastAPI application for the school grades management system.
Provides both natural language agent interface and direct tool access.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db, get_db_context, User
from api import agent_router, tools_router, users_router


# --------------- Lifespan ---------------

def _auto_seed_if_empty():
    """Populate the database with sample data if tables are empty."""
    try:
        with get_db_context() as db:
            if db.query(User).count() == 0:
                print("Empty database detected — seeding sample data...")
                from database.seed import seed_database
                seed_database()
    except Exception as exc:
        print(f"Auto-seed skipped ({exc})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler – initialise DB on startup."""
    if settings.debug:
        print("Initializing database...")
    init_db()
    _auto_seed_if_empty()
    if settings.debug:
        print("Database initialized.")
    yield


# --------------- FastAPI app ---------------

app = FastAPI(
    title="School Grades Agent API",
    description="""
API for managing school grades with an AI agent interface.

## Features

### Agent Interface
- Natural language processing for grade queries
- Intent detection and entity extraction
- Guardrails for authorization enforcement

### Authorization Rules
- **Teachers**: Can add/update grades, view all students, generate reports
- **Students**: Can only view their own grades and summaries
- **No delete operations**: Deletion is not allowed by design

### Guardrails
- Pre-execution: Blocks obvious unauthorized requests
- Tool-layer: Enforces rules even if guardrails are bypassed
- Post-execution: Sanitizes responses to prevent data leakage
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )


app.include_router(agent_router)
app.include_router(tools_router)
app.include_router(users_router)


@app.get("/", tags=["UI"], include_in_schema=False)
async def root():
    """Serve the web interface."""
    return FileResponse("static/index.html")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )