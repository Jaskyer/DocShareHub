import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Set noisy loggers to WARNING level
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

from app.config import settings
from app.database import init_db
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.security_middleware import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init database
    await init_db()
    yield
    # Shutdown: nothing special needed


app = FastAPI(
    title="文档托管平台",
    description="企业文档托管与分享平台",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware (order matters: outermost first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuthMiddleware)

# Static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Import and register routers
from app.routers import auth, projects, documents, url_mappings, access_requests, favorites, feishu_webhook, pages, file_serve  # noqa: E402

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(url_mappings.router)
app.include_router(access_requests.router)
app.include_router(favorites.router)
app.include_router(feishu_webhook.router)
app.include_router(pages.router)
app.include_router(file_serve.router)
