from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Table

from app.utilities.database import Base

song_artists = Table(
    "song_artists",
    Base.metadata,
    Column("song_id", Integer, ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True),
    Column("artist_id", Integer, ForeignKey("artists.id", ondelete="CASCADE"), primary_key=True),
)
