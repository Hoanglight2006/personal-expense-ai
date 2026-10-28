from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def init_db():
    """Ensure static directories exist and database schema has all columns."""
    Path("static/avatars").mkdir(parents=True, exist_ok=True)
    try:
        import app.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            inspector = inspect(conn)
            if "users" in inspector.get_table_names():
                columns = [c["name"] for c in inspector.get_columns("users")]
                if "avatar_url" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) NULL"))
                if "role" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(10) NOT NULL DEFAULT 'user'"))
                if "is_locked" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT 0"))
    except Exception:
        pass


def get_db():
    """FastAPI dependency – yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
