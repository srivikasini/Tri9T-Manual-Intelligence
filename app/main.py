"""Main FastAPI application entrypoint."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, logger
from app.api import api_router

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler initializing DB tables on startup."""
    logger.info("Initializing Tri9T Manual Intelligence Platform...")
    init_db()
    logger.info("Database tables initialized successfully.")
    yield
    logger.info("Shutting down Tri9T Manual Intelligence Platform...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade Manual Intelligence Platform for technical document extraction, "
        "hierarchical version diffing, grounded QA test generation, and staleness/impact analysis."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global unhandled exception handler to prevent leaking stack traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An internal server error occurred. Please consult application logs.",
            "path": request.url.path
        }
    )

from fastapi.responses import JSONResponse, HTMLResponse
from pathlib import Path

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Health & Status"])
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "documentation": "/docs",
        "dashboard": "/dashboard"
    }

@app.get("/health", tags=["Health & Status"])
def health_check():
    return {"status": "healthy"}

@app.get("/dashboard", response_class=HTMLResponse, tags=["Visual Dashboard"])
def get_dashboard():
    """Interactive visual web dashboard for browsing sections, diffing, QA generation, and staleness."""
    dashboard_path = Path(__file__).parent / "static" / "dashboard.html"
    if dashboard_path.exists():
        return dashboard_path.read_text(encoding="utf-8")
    return "<h1>Dashboard file not found</h1>"
