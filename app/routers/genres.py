from fastapi import APIRouter, Depends, HTTPException

from app.utilities import schemas
from app.repositories.deps import get_genre_repository
from app.repositories.genres import GenreRepository

router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("", response_model=list[schemas.Genre])
def list_genres(repo: GenreRepository = Depends(get_genre_repository)):
    return repo.get_all()


@router.post("", response_model=schemas.Genre, status_code=201)
def create_genre(
    payload: schemas.GenreCreate, repo: GenreRepository = Depends(get_genre_repository)
):
    existing = repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(status_code=409, detail="Genre already exists")
    return repo.create(payload)


@router.get("/{genre_id}", response_model=schemas.Genre)
def get_genre(genre_id: int, repo: GenreRepository = Depends(get_genre_repository)):
    genre = repo.get_by_id(genre_id)
    if genre is None:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre
