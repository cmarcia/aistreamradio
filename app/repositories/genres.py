from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


class GenreRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[models.Genre]:
        return list(self.db.scalars(select(models.Genre)).all())

    def get_by_id(self, genre_id: int) -> models.Genre | None:
        return self.db.get(models.Genre, genre_id)

    def get_by_name(self, name: str) -> models.Genre | None:
        return self.db.scalar(select(models.Genre).where(models.Genre.name == name))

    def create(self, payload: schemas.GenreCreate) -> models.Genre:
        genre = models.Genre(**payload.model_dump())
        self.db.add(genre)
        self.db.commit()
        self.db.refresh(genre)
        return genre

    def get_or_create(self, name: str, description: str | None = None) -> models.Genre:
        genre = self.get_by_name(name)
        if not genre:
            genre = models.Genre(name=name, description=description)
            self.db.add(genre)
            self.db.flush()
        return genre
