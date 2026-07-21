from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.genres import GenreRepository
from app.repositories.songs import SongRepository
from app.repositories.stations import StationRepository


def get_genre_repository(db: Session = Depends(get_db)) -> GenreRepository:
    return GenreRepository(db)


def get_station_repository(db: Session = Depends(get_db)) -> StationRepository:
    return StationRepository(db)


def get_song_repository(db: Session = Depends(get_db)) -> SongRepository:
    return SongRepository(db)
