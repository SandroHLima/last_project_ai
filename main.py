"""
School Grades Agent API

Main FastAPI application for the school grades management system.
Provides both natural language agent interface and direct tool access.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import init_db
from api import agent_router, tools_router, users_router


# --------------- Lifespan ---------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler – initialise DB on startup."""
    if settings.debug:
        print("Initializing database...")
    init_db()
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )


# Include routers
app.include_router(agent_router)
app.include_router(tools_router)
app.include_router(users_router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check."""
    return {
        "status": "online",
        "service": "School Grades Agent API",
        "version": "1.0.0"
    }


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
