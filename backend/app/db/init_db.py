import logging
from sqlalchemy import text
from app.db.session import engine
from app.models import Base

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Initialize database tables using SQLAlchemy Base metadata."""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")


def check_db_connection() -> bool:
    """Verify backend connectivity to PostgreSQL."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
