from __future__ import annotations

from pathlib import Path

from nutrition_service.database import NutritionDatabase
from nutrition_service.service import NutritionService

try:
    from fastapi import FastAPI, HTTPException
except ImportError:  # pragma: no cover
    FastAPI = None
    HTTPException = Exception


DB_PATH = Path(__file__).resolve().parents[4] / "data" / "nutrition.sqlite3"


def create_app() -> "FastAPI | None":
    if FastAPI is None:
        return None

    database = NutritionDatabase(DB_PATH)
    service = NutritionService(database)
    app = FastAPI(title="nutrition-service", version="0.1.0")

    @app.get("/")
    def root() -> dict:
        return {
            "service": "nutrition-service",
            "status": "ok",
            "docs_url": "/docs",
            "health_url": "/health",
            "routes": [
                "/nutrition/lookup",
                "/nutrition/analyze",
            ],
        }

    @app.get("/health")
    def health() -> dict:
        return {"service": "nutrition-service", "status": "ok"}

    @app.post("/nutrition/lookup")
    def lookup(payload: dict) -> dict:
        food_code = payload["food_code"]
        try:
            return service.lookup(food_code)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/nutrition/search")
    def search(payload: dict) -> dict:
        return service.search(
            payload["query"],
            limit=int(payload.get("limit", 5)),
        )

    @app.post("/nutrition/analyze")
    def analyze(payload: dict) -> dict:
        try:
            return service.analyze(
                payload["meal_items"],
                requires_user_clarification=payload.get("requires_user_clarification", False),
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    return app


app = create_app()
