from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("", response_model=list[schemas.Genre])
def list_genres(db: Session = Depends(get_db)):
    return db.scalars(select(models.Genre)).all()


@router.post("", response_model=schemas.Genre, status_code=201)
def create_genre(payload: schemas.GenreCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(models.Genre).where(models.Genre.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Genre already exists")
    genre = models.Genre(**payload.model_dump())
    db.add(genre)
    db.commit()
    db.refresh(genre)
    return genre


@router.get("/{genre_id}", response_model=schemas.Genre)
def get_genre(genre_id: int, db: Session = Depends(get_db)):
    genre = db.get(models.Genre, genre_id)
    if genre is None:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre
