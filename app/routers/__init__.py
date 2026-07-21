from fastapi import APIRouter

from app.routers.genres import router as genres_router
from app.routers.health import router as health_router
from app.routers.itunes import router as itunes_router
from app.routers.songs import router as songs_router
from app.routers.stations import router as stations_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(genres_router)
api_router.include_router(stations_router)
api_router.include_router(songs_router)
api_router.include_router(itunes_router)

