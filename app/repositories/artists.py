from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


class ArtistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, artist_id: int) -> models.Artist | None:
        return self.db.get(models.Artist, artist_id)

    def get_by_name(self, name: str) -> models.Artist | None:
        return self.db.scalar(
            select(models.Artist).where(models.Artist.name == name)
        )

    def create(self, artist_in: schemas.ArtistCreate) -> models.Artist:
        artist = models.Artist(name=artist_in.name)
        self.db.add(artist)
        self.db.commit()
        self.db.refresh(artist)
        return artist

    def get_or_create(self, name: str) -> models.Artist:
        artist = self.get_by_name(name)
        if artist is None:
            artist = models.Artist(name=name)
            self.db.add(artist)
            self.db.commit()
            self.db.refresh(artist)
        return artist
