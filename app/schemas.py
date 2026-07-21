from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GenreBase(BaseModel):
    name: str
    description: str | None = None


class GenreCreate(GenreBase):
    pass


class Genre(GenreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class StationBase(BaseModel):
    name: str
    frequency: str
    genre_id: int | None = None
    stream_url: str = "https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8"
    metadata_url: str | None = ("https://d3d4yli4hf5"
                                "bmh.cloudfront.net/metadata.json")
    current_artist: str | None = None
    current_title: str | None = None
    current_album: str | None = None
    has_track_info: bool = True
    date: str | None = Field(default_factory=lambda: str(datetime.now(timezone.utc).year))
    bit_depth: int | None = 16
    sample_rate: int | None = 44100
    cover_url: str | None = None
    primary_color: str | None = "#00f3ff"
    secondary_color: str | None = "#3b82f6"


class StationCreate(StationBase):
    pass


class Station(StationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    genre: Genre | None = None


class SongRatingCreate(BaseModel):
    artist: str
    title: str
    listener_id: str
    rating: Literal["up", "down"]
    cover_image: str | None = Field(default=None, max_length=2_000_000)


class SongRatingSummary(BaseModel):
    artist: str
    title: str
    thumbs_up: int
    thumbs_down: int
    user_rating: Literal["up", "down"] | None = None


class DislikedSong(BaseModel):
    artist: str
    title: str
    rated_at: datetime
    cover_image: str | None = None


class DislikedSongsPage(BaseModel):
    items: list[DislikedSong]
    total: int
    page: int
    page_size: int


class ArtistBase(BaseModel):
    name: str


class ArtistCreate(ArtistBase):
    pass


class Artist(ArtistBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class AlbumBase(BaseModel):
    title: str
    artist_id: int | None = None
    cover_url: str | None = None
    release_year: int | None = None


class AlbumCreate(AlbumBase):
    pass


class Album(AlbumBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    artist: Artist | None = None


class ITunesSearchQuery(BaseModel):
    title: str
    artist: str
    release_date: str | None = None
    album: str | None = None


class ITunesSearchResult(BaseModel):
    artist_name: str
    track_title: str
    album_name: str | None = None
    cover_url: str | None = None
    release_date: str | None = None
    release_year: int | None = None
    itunes_url: str | None = None
    genre: str | None = None
    artist_id: int | None = None
    album_id: int | None = None
    cached: bool = False


