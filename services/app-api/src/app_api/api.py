from __future__ import annotations

from pathlib import Path

from app_api.analysis import MealAnalysisOrchestrator
from app_api.models import UploadRequest
from app_api.openai_responses import OpenAIResponsesMealAnalyzer
from app_api.schemas import (
    AuthRequest,
    ErrorResponse,
    HealthResponse,
    LoginResponse,
    MealCreateRequest,
    MealListResponse,
    MealQuestionRequest,
    RegisterResponse,
    RootResponse,
)
from app_api.storage import InMemoryMealStore

try:
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:  # pragma: no cover
    FastAPI = None
    HTTPException = Exception
    FileResponse = None
    JSONResponse = None
    StaticFiles = None

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> "FastAPI | None":
    if FastAPI is None:
        return None

    try:
        vision_client = OpenAIResponsesMealAnalyzer()
    except RuntimeError:
        vision_client = None
    orchestrator = MealAnalysisOrchestrator(InMemoryMealStore(), vision_client=vision_client)
    app = FastAPI(title="app-api", version="0.1.0")
    if StaticFiles is not None:
        app.mount("/app/static", StaticFiles(directory=STATIC_DIR), name="app-static")

    if JSONResponse is not None:
        @app.exception_handler(Exception)
        async def unhandled_exception_handler(_, exc: Exception) -> "JSONResponse":
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(error=str(exc) or "Internal Server Error").model_dump(),
            )

    @app.get("/", response_model=RootResponse)
    def root() -> RootResponse:
        return RootResponse(
            service="app-api",
            status="ok",
            docs_url="/docs",
            health_url="/health",
            web_app_url="/app",
            openai_responses_enabled=vision_client is not None,
            routes=[
                "/demo",
                "/auth/register",
                "/auth/login",
                "/meals",
                "/meals/{meal_id}",
                "/meals/{meal_id}/questions",
                "/meals/{meal_id}/export",
            ],
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="app-api", status="ok")

    @app.get("/app")
    def web_app() -> "FileResponse":
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/demo")
    def demo_web_app() -> "FileResponse":
        return FileResponse(STATIC_DIR / "demo.html")

    @app.post("/auth/register")
    def register(payload: AuthRequest) -> RegisterResponse:
        return RegisterResponse(user_id=payload.email or "demo-user", status="registered")

    @app.post("/auth/login")
    def login(payload: AuthRequest) -> LoginResponse:
        return LoginResponse(access_token=f"demo-token-{payload.email or 'user'}")

    @app.post("/meals")
    def create_meal(payload: MealCreateRequest, x_user_id: str = Header(default="demo-user")) -> dict:
        try:
            upload = UploadRequest(**payload.model_dump())
            return orchestrator.create_meal(x_user_id, upload).to_dict()
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error) or "Internal Server Error") from error

    @app.get("/meals")
    def list_meals(x_user_id: str = Header(default="demo-user")) -> MealListResponse:
        return MealListResponse(items=[record.to_dict() for record in orchestrator.list_meals(x_user_id)])

    @app.get("/meals/{meal_id}")
    def get_meal(meal_id: str) -> dict:
        record = orchestrator.get_meal(meal_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Meal not found")
        return record.to_dict()

    @app.post("/meals/{meal_id}/export")
    def export_meal(meal_id: str) -> dict:
        try:
            return orchestrator.export_meal(meal_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Meal not found") from error

    @app.post("/meals/{meal_id}/questions")
    def ask_meal_question(meal_id: str, payload: MealQuestionRequest) -> dict:
        try:
            return orchestrator.answer_meal_question(meal_id, payload.question)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Meal not found") from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    return app


app = create_app()
