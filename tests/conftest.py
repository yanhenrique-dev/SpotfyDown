"""
tests/conftest.py — Fixtures compartilhadas para todos os testes.
"""
import shutil
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch


# ── Cache isolation ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_spotify_cache():
    """Limpa o cache do Spotify antes de cada teste para garantir isolamento."""
    cache_dir = Path.home() / ".cache" / "spotify_downloader"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    yield


# ── Fixtures do Spotify ────────────────────────────────────────────────────────

@pytest.fixture
def mock_track() -> dict:
    """Faixa Spotify mínima válida."""
    return {
        "id": "t001",
        "name": "Test Track",
        "track_number": 1,
        "disc_number": 1,
        "duration_ms": 200_000,
        "artists": [{"name": "Test Artist"}],
        "album": {
            "name": "Test Album",
            "release_date": "2024-01-15",
            "images": [{"url": "https://i.scdn.co/image/test"}],
        },
        "external_urls": {"spotify": "https://open.spotify.com/track/t001"},
    }


@pytest.fixture
def mock_playlist() -> dict:
    """Resposta mínima de playlist da API do Spotify."""
    return {
        "id": "pl001",
        "name": "Test Playlist",
        "tracks": {
            "items": [
                {
                    "track": {
                        "id": f"t{i:03d}",
                        "name": f"Track {i}",
                        "track_number": i,
                        "disc_number": 1,
                        "duration_ms": 180_000 + i * 1000,
                        "artists": [{"name": "Artist"}],
                        "album": {
                            "name": "Album",
                            "release_date": "2024",
                            "images": [],
                        },
                    }
                }
                for i in range(1, 4)
            ],
            "next": None,
            "total": 3,
        },
    }


@pytest.fixture
def mock_spotify_client(mock_playlist) -> MagicMock:
    """Cliente Spotipy mockado com métodos principais."""
    client = MagicMock()
    client.playlist.return_value = mock_playlist
    client.album.return_value = {
        "id": "alb001",
        "name": "Test Album",
        "tracks": {
            "items": [],
            "next": None,
            "total": 0,
        },
        "images": [],
    }
    client.track.return_value = {
        "id": "t001",
        "name": "Single Track",
        "track_number": 1,
        "disc_number": 1,
        "duration_ms": 200_000,
        "artists": [{"name": "Solo Artist"}],
        "album": {"name": "Single", "release_date": "2024", "images": []},
    }
    client.artist_albums.return_value = {
        "items": [{"id": "alb001", "name": "Best Of"}],
        "next": None,
    }
    # album() is called for each album stub; return one track so artist test passes
    client.album.return_value = {
        "id": "alb001",
        "name": "Best Of",
        "tracks": {
            "items": [
                {
                    "id": "t001",
                    "name": "Top Track",
                    "track_number": 1,
                    "disc_number": 1,
                    "duration_ms": 200_000,
                    "artists": [{"name": "Test Artist"}],
                }
            ],
            "next": None,
            "total": 1,
        },
        "images": [],
    }
    return client
