import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, ai, auth, budgets, categories, chat, ocr, saving_goals, transactions
from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app() -> FastAPI:
    """Application factory for FastAPI app."""
    init_db()

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

    # API Routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(categories.router, prefix="/api/v1")
    app.include_router(transactions.router, prefix="/api/v1")
    app.include_router(budgets.router, prefix="/api/v1")
    app.include_router(saving_goals.router, prefix="/api/v1")
    app.include_router(ocr.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(ai.router, prefix="/api/v1")

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app


app = create_app()
