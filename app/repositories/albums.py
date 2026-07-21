from sqlalchemy import func, select
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

    def get_by_artist_name_and_title(
        self, artist_name: str, album_title: str | None = None, track_title: str | None = None
    ) -> models.Album | None:
        """
        Finds an existing Album in the DB for the given artist name.
        Optionally filters by album_title or track_title.
        Returns the Album object if found with a valid cover_url.
        """
        if not artist_name:
            return None

        from app.services.itunes import clean_metadata_string

        norm_artist = artist_name.strip().lower()
        clean_artist = clean_metadata_string(artist_name).lower()
        artist_candidates = list(filter(None, {norm_artist, clean_artist}))

        if album_title and album_title.strip():
            norm_album = album_title.strip().lower()
            clean_album = clean_metadata_string(album_title).lower()
            album_candidates = list(filter(None, {norm_album, clean_album}))

            for art in artist_candidates:
                for alb in album_candidates:
                    query = (
                        select(models.Album)
                        .join(models.Artist)
                        .where(func.lower(models.Artist.name) == art)
                        .where(func.lower(models.Album.title) == alb)
                    )
                    album = self.db.scalar(query)
                    if album and album.cover_url:
                        return album

        for art in artist_candidates:
            fallback_query = (
                select(models.Album)
                .join(models.Artist)
                .where(func.lower(models.Artist.name) == art)
                .where(models.Album.cover_url.is_not(None))
            )
            album = self.db.scalar(fallback_query)
            if album:
                return album

        return None



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
