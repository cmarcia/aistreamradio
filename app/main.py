from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import api_router

# Create database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include modular API routers
app.include_router(api_router)
