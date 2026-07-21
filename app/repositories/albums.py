from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


class AlbumRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, album_id: int) -> models.Album | None:
        return self.db.get(models.Album, album_id)

    def get_by_title_and_artist(
        self, title: str, artist_id: int | None = None
    ) -> models.Album | None:
        query = select(models.Album).where(models.Album.title == title)
        if artist_id is not None:
            query = query.where(models.Album.artist_id == artist_id)
        return self.db.scalar(query)

    def create(self, album_in: schemas.AlbumCreate) -> models.Album:
        album = models.Album(
            title=album_in.title,
            artist_id=album_in.artist_id,
            cover_url=album_in.cover_url,
            release_year=album_in.release_year,
        )
        self.db.add(album)
        self.db.commit()
        self.db.refresh(album)
        return album

    def get_or_create(
        self,
        title: str,
        artist_id: int | None = None,
        cover_url: str | None = None,
        release_year: int | None = None,
    ) -> models.Album:
        album = self.get_by_title_and_artist(title, artist_id)
        if album is None:
            album = models.Album(
                title=title,
                artist_id=artist_id,
                cover_url=cover_url,
                release_year=release_year,
            )
            self.db.add(album)
            self.db.commit()
            self.db.refresh(album)
        else:
            updated = False
            if cover_url and not album.cover_url:
                album.cover_url = cover_url
                updated = True
            if release_year and not album.release_year:
                album.release_year = release_year
                updated = True
            if updated:
                self.db.commit()
                self.db.refresh(album)
        return album
