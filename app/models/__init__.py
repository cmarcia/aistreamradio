import importlib
import sys

from app.database import Base
from app.models import album, artist, genre, song, song_artist, song_rating, station, user

# If app.database was reloaded (e.g. in test fixtures), Base changed.
# Reload submodules so all models register on the new Base.metadata.
if hasattr(genre, "Genre") and genre.Genre.metadata is not Base.metadata:
    if "app.models.user" in sys.modules:
        importlib.reload(user)
    if "app.models.song_artist" in sys.modules:
        importlib.reload(song_artist)
    if "app.models.genre" in sys.modules:
        importlib.reload(genre)
    if "app.models.station" in sys.modules:
        importlib.reload(station)
    if "app.models.song" in sys.modules:
        importlib.reload(song)
    if "app.models.song_rating" in sys.modules:
        importlib.reload(song_rating)
    if "app.models.artist" in sys.modules:
        importlib.reload(artist)
    if "app.models.album" in sys.modules:
        importlib.reload(album)

from app.models.album import Album
from app.models.artist import Artist
from app.models.genre import Genre
from app.models.song import Song
from app.models.song_artist import song_artists
from app.models.song_rating import SongRating
from app.models.station import Station
from app.models.user import User

__all__ = [
    "Album",
    "Artist",
    "Genre",
    "Song",
    "SongRating",
    "Station",
    "User",
    "song_artists",
]

