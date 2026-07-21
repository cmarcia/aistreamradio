from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["health"])
STATIC_DIR = Path(__file__).parent.parent / "static"


@router.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/health")
def health():
    return {"status": "ok"}
