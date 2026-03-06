"""
tests/core/test_spotify.py — Testes unitários para core/spotify.py
"""
import pytest
from unittest.mock import MagicMock

from src.core.spotify import get_spotify_content, SpotifyContentError


class TestGetSpotifyContent:

    def test_playlist_returns_tracks(self, mock_spotify_client):
        url = "https://open.spotify.com/playlist/pl001"
        result = get_spotify_content(mock_spotify_client, url)
        assert result["content_type"] == "playlist"
        assert result["name"]  # não vazio
        tracks = result["tracks"]
        assert len(tracks) == 3
        # Cada faixa deve ter campos básicos
        for t in tracks:
            assert "name" in t
            assert "artists" in t
            assert "album" in t

    def test_single_track_url(self, mock_spotify_client):
        url = "https://open.spotify.com/track/t001"
        result = get_spotify_content(mock_spotify_client, url)
        assert result["content_type"] == "track"
        assert len(result["tracks"]) == 1

    def test_album_url(self, mock_spotify_client):
        # Album com tracks vazias mas válido
        mock_spotify_client.album.return_value["tracks"]["items"] = [
            {
                "id": "t001",
                "name": "Album Track",
                "track_number": 1,
                "disc_number": 1,
                "duration_ms": 200_000,
                "artists": [{"name": "Artist"}],
            }
        ]
        url = "https://open.spotify.com/album/alb001"
        result = get_spotify_content(mock_spotify_client, url)
        assert result["content_type"] == "album"

    def test_artist_url_returns_top_tracks(self, mock_spotify_client):
        url = "https://open.spotify.com/artist/ar001"
        result = get_spotify_content(mock_spotify_client, url)
        assert result["content_type"] == "artist"
        assert len(result["tracks"]) >= 1

    def test_invalid_url_raises_error(self, mock_spotify_client):
        with pytest.raises(SpotifyContentError) as exc_info:
            get_spotify_content(mock_spotify_client, "https://not-spotify.com/foo")
        assert exc_info.value.code == "invalid_url"

    def test_unsupported_spotify_url_raises_error(self, mock_spotify_client):
        with pytest.raises(SpotifyContentError) as exc_info:
            get_spotify_content(mock_spotify_client, "https://open.spotify.com/user/abc123")
        assert exc_info.value.code == "invalid_url"

    def test_filters_none_tracks(self, mock_spotify_client):
        """Items de playlist com track=None (faixas locais) devem ser ignorados."""
        mock_spotify_client.playlist.return_value["tracks"]["items"].insert(0, {"track": None})
        url = "https://open.spotify.com/playlist/pl001"
        result = get_spotify_content(mock_spotify_client, url)
        for t in result["tracks"]:
            assert t is not None
            assert "name" in t
