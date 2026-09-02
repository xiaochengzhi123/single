from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from signaltutor import __version__
from signaltutor.api.dependencies import get_services
from signaltutor.api.routes_auth import router as auth_router
from signaltutor.api.routes_chat import router as chat_router
from signaltutor.api.routes_feedback import router as feedback_router
from signaltutor.api.routes_learning import router as learning_router
from signaltutor.api.routes_problems import router as problems_router
from signaltutor.api.routes_students import router as students_router
from signaltutor.config.logging import configure_logging
from signaltutor.exceptions import SignalTutorError


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    services = get_services()
    if services.settings.env == "production" and services.settings.uses_insecure_auth_defaults:
        raise RuntimeError("生产环境必须配置 AUTH_SECRET 和 ADMIN_API_KEY")
    services.settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="SignalTutor API",
    version=__version__,
    description="可验证的考研《信号与系统》多模态辅导 Agent",
    lifespan=lifespan,
)
settings = get_services().settings
development_origin_regex = (
    r"^http://(?:localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|"
    r"192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}):300\d$"
    if settings.env == "development"
    else None
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_origin_regex=development_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(problems_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(students_router)
app.include_router(feedback_router)
app.include_router(learning_router)


@app.exception_handler(SignalTutorError)
async def handle_domain_error(request: Request, exc: SignalTutorError) -> JSONResponse:
    return JSONResponse(
        status_code=422, content={"error": {"code": exc.__class__.__name__, "message": str(exc)}}
    )


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "model_mode": "qwen" if settings.model_enabled else "offline",
    }
