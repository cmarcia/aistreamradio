import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.Configuration.config import settings
from app.Configuration.logging_config import logger
from app.utilities.database import Base, engine
from app.routers import api_router

# Create database tables on startup
Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    from sqlalchemy import text
    try:
        conn.execute(text("ALTER TABLE song_ratings ADD COLUMN user_id VARCHAR;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR;"))
        conn.commit()
    except Exception:
        pass

from starlette.middleware.sessions import SessionMiddleware
from app.Configuration.auth_config import auth_settings

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=settings.app_name)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SessionMiddleware, secret_key=auth_settings.auth_secret_key)





STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000.0
    logger.info(f"{request.method} {request.url.path} -> Status {response.status_code} ({duration_ms:.1f}ms)")
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code} error on {request.method} {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include modular API routers
app.include_router(api_router)
