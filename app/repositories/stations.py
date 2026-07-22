import json
from pathlib import Path
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models
from app.utilities import schemas
from app.Configuration.logging_config import logger
from app.repositories.genres import GenreRepository


class StationRepository:
    def __init__(self, db: Session):
        self.db = db
        self.genre_repo = GenreRepository(db)

    def get_all(self) -> Sequence[models.Station]:
        stations = self.db.scalars(
            select(models.Station).options(joinedload(models.Station.genre))
        ).all()
        if not stations:
            logger.info("No station records found in database. Auto-seeding initial dataset...")
            self.seed_initial_data()
            stations = self.db.scalars(
                select(models.Station).options(joinedload(models.Station.genre))
            ).all()
        return stations

    def get_by_id(self, station_id: int) -> models.Station | None:
        return self.db.scalar(
            select(models.Station)
            .where(models.Station.id == station_id)
            .options(joinedload(models.Station.genre))
        )

    def create(self, payload: schemas.StationCreate) -> models.Station:
        logger.info(f"Creating new station: '{payload.name}' ({payload.frequency})")
        station = models.Station(**payload.model_dump())
        self.db.add(station)
        self.db.commit()
        self.db.refresh(station)
        return station

    def update_live_metadata(
        self, station: models.Station, artist: str, title: str, cover_url: str | None = None
    ) -> models.Station:
        logger.info(f"Updating station '{station.name}' (ID={station.id}) live metadata -> '{artist} - {title}'")
        if station.current_title != title or station.current_artist != artist:
            station.cover_url = cover_url
        elif cover_url:
            station.cover_url = cover_url

        station.current_artist = artist or station.name
        station.current_title = title
        station.has_track_info = True
        self.db.commit()
        self.db.refresh(station)
        return station

    def seed_initial_data(self, json_path: Path | None = None) -> Sequence[models.Station]:
        if json_path is None:
            json_path = Path(__file__).parent.parent.parent / "data" / "initial_stations.json"

        if not json_path.exists():
            logger.warning(f"Initial station seed dataset not found at path: {json_path}")
            return []

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            genres_map = {}

            for g_data in data.get("genres", []):
                name = g_data["name"]
                g = self.genre_repo.get_or_create(name=name, description=g_data.get("description"))
                genres_map[name] = g.id

            stations = []
            for idx, st_data in enumerate(data.get("stations", []), start=1):
                st = dict(st_data)
                name = st["name"]
                genre_name = st.pop("genre", None)
                genre_id = genres_map.get(genre_name) if genre_name else None

                if "metadata_url" not in st or not st["metadata_url"]:
                    st["metadata_url"] = f"/stations/{idx}/metadata"

                existing = self.db.scalar(select(models.Station).where(models.Station.name == name))
                if existing:
                    existing.genre_id = genre_id
                    existing.frequency = st.get("frequency", existing.frequency)
                    existing.stream_url = st.get("stream_url", existing.stream_url)
                    existing.metadata_url = st.get("metadata_url", existing.metadata_url)
                    existing.primary_color = st.get("primary_color", existing.primary_color)
                    existing.secondary_color = st.get("secondary_color", existing.secondary_color)
                    stations.append(existing)
                else:
                    station = models.Station(genre_id=genre_id, **st)
                    self.db.add(station)
                    stations.append(station)

            self.db.commit()
            logger.info(f"Successfully synced {len(stations)} station records in database from {json_path.name}")
            return stations
        except Exception as exc:
            logger.error(f"Error seeding initial stations from {json_path}: {exc}", exc_info=True)
            self.db.rollback()
            return []

