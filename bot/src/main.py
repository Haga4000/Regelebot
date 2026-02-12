import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api.health import router as health_router
from api.webhook import router as webhook_router
from config import settings
from core.database import engine
from models import Base

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Validate LLM config at startup — fail fast if misconfigured
    from llm import create_llm_provider

    provider = create_llm_provider()
    base_url = f" via {settings.LLM_BASE_URL}" if settings.LLM_BASE_URL else ""
    logger.info(
        "LLM ready: provider=%s model=%s%s",
        settings.LLM_PROVIDER,
        provider.model,
        base_url,
    )

    yield
    await engine.dispose()


app = FastAPI(title="Regelebot", version="0.1.0", lifespan=lifespan)

# CORS — restrict to internal Docker origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://gateway:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["X-Webhook-Secret"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(health_router)
app.include_router(webhook_router)
