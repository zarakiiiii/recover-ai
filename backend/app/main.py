from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException, status

from app.api.recovery import router as recovery_router
from app.core.config import settings
from app.db.init_db import check_db_connection, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("recoverai.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    logger.info(f"Starting {settings.PROJECT_NAME} backend in {settings.ENVIRONMENT} mode...")
    # Attempt DB connectivity and schema creation on startup if database is available
    if check_db_connection():
        logger.info("Connected to PostgreSQL successfully. Initializing tables...")
        init_db()
    else:
        logger.warning(
            "PostgreSQL is currently unreachable on startup. "
            "Tables will be created once connection is established."
        )
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME} backend...")


app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    version="0.1.0",
    description="Backend service and API for RecoverAI",
    lifespan=lifespan,
)

# Register API routers
app.include_router(recovery_router, prefix="/api")


@app.get("/health")
def health_check():
    """Basic service health check."""
    return {
        "status": "ok",
        "service": "recover-ai-backend",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/db")
def database_health_check():
    """Verify backend connectivity to PostgreSQL."""
    is_connected = check_db_connection()
    if not is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        )
    return {
        "status": "ok",
        "database": "connected",
        "postgres_server": settings.POSTGRES_SERVER,
        "postgres_db": settings.POSTGRES_DB,
    }
