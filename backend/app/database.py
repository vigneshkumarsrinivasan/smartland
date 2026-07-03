"""
Database setup — SQLite locally (PostGIS/Postgres target for production).
See CLAUDE.md for the swap instructions.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite fallback. To swap for Postgres set DATABASE_URL env var:
# DATABASE_URL=postgresql+psycopg2://user:pass@localhost/landsignal
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./landsignal.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=engine)
    upgrade_db()


def upgrade_db():
    """Apply additive schema migrations. Safe to call on every startup."""
    from sqlalchemy import text
    migrations = [
        "ALTER TABLE data_sources ADD COLUMN last_run_at DATETIME",
        "ALTER TABLE data_sources ADD COLUMN freshness_hours INTEGER DEFAULT 24",
        "ALTER TABLE infrastructure_projects ADD COLUMN data_source TEXT",
        "ALTER TABLE infrastructure_projects ADD COLUMN source_url TEXT",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # column already exists — safe to ignore
