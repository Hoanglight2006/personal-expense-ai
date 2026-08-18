from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.api.routes import auth, categories, transactions, budgets, saving_goals, ocr, excel, chat, ai
from app.database import Base, engine
from app.config import settings


def init_db_and_static():
    """Ensure static directories exist and database schema has all columns."""
    static_dir = Path("static/avatars")
    static_dir.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            inspector = inspect(conn)
            if "users" in inspector.get_table_names():
                columns = [c["name"] for c in inspector.get_columns("users")]
                if "avatar_url" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) NULL"))
    except Exception:
        pass


def create_app() -> FastAPI:
    init_db_and_static()

    app = FastAPI(
        title="Personal Expense AI API",
        version="1.0.0",
        description="API for Personal Expense Management system with AI integration.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static assets (avatars, uploads, etc.)
    static_path = Path("static")
    static_path.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(categories.router, prefix="/api/v1")
    app.include_router(transactions.router, prefix="/api/v1")
    app.include_router(budgets.router, prefix="/api/v1")
    app.include_router(saving_goals.router, prefix="/api/v1")
    app.include_router(ocr.router, prefix="/api/v1")
    app.include_router(excel.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(ai.router, prefix="/api/v1")

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app


app = create_app()
