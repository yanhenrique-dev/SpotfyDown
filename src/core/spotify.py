"""
spotify.py — Spotify API wrapper.

Suportados:
  - Faixas    (/track/)
  - Álbuns    (/album/)
  - Playlists (/playlist/)
  - Artistas  (/artist/)  ← novo
"""
import json
import time
import logging
from pathlib import Path
from typing import Any

import spotipy

from ..config import CACHE_DIR

logger = logging.getLogger(__name__)


# ─── Exceções ────────────────────────────────────────────────────────────────

class SpotifyContentError(Exception):
    """Erro tipado em operações com a API do Spotify."""

    CODES = {
        "invalid_url",      # URL não é um link válido do Spotify
        "unauthorized",     # Credenciais inválidas ou expiradas
        "not_found",        # Recurso não encontrado (404)
        "editorial",        # Playlists editoriais inacessíveis c/ Client Credentials
        "api_error",        # Outro erro da API
    }

    def __init__(self, message: str, code: str = "api_error") -> None:
        super().__init__(message)
        self.code = code


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _paginate(client: spotipy.Spotify, first_page: dict) -> list[dict]:
    """Coleta todos os itens de um endpoint paginado da API Spotify."""
    items = list(first_page.get("items", []))
    page = first_page
    while page.get("next"):
        page = client.next(page)
        items.extend(page.get("items", []))
    return items


def _enrich_tracks_with_album(tracks: list[dict], album_info: dict) -> list[dict]:
    """Injeta informações do álbum em cada faixa (evitando referências circulares)."""
    safe_album = {k: v for k, v in album_info.items() if k != "tracks"}
    for track in tracks:
        track["album"] = safe_album
    return tracks


def _detect_content_type(url: str) -> str:
    """Detecta o tipo de conteúdo a partir da URL do Spotify."""
    if "/artist/" in url:
        return "artist"
    if "/album/" in url:
        return "album"
    if "/track/" in url:
        return "track"
    if "/playlist/" in url:
        return "playlist"
    raise SpotifyContentError(
        "Link inválido. Cole um link do Spotify (open.spotify.com/...).",
        code="invalid_url",
    )


def _extract_id(url: str) -> str:
    return url.split("/")[-1].split("?")[0]


# ─── Fetchers por tipo ────────────────────────────────────────────────────────

def _fetch_track(client: spotipy.Spotify, content_id: str) -> dict[str, Any]:
    track = client.track(content_id)
    return {
        "name": track.get("album", {}).get("name", ""),
        "content_type": "track",
        "tracks": [track],
    }


def _fetch_album(client: spotipy.Spotify, content_id: str) -> dict[str, Any]:
    full_album = client.album(content_id)
    album_name = full_album.get("name", "Álbum")
    tracks = _paginate(client, full_album["tracks"])
    _enrich_tracks_with_album(tracks, full_album)
    return {
        "name": album_name,
        "content_type": "album",
        "cover_url": (full_album.get("images") or [{}])[0].get("url", ""),
        "tracks": tracks,
    }


def _fetch_playlist(client: spotipy.Spotify, content_id: str) -> dict[str, Any]:
    playlist_info = client.playlist(content_id)
    playlist_name = playlist_info.get("name", "Playlist")
    raw_items = _paginate(client, playlist_info["tracks"])
    # Filtra itens sem faixa (null tracks ocorrem em playlists editadas)
    tracks = [item["track"] for item in raw_items if item.get("track")]
    return {
        "name": playlist_name,
        "content_type": "playlist",
        "cover_url": (playlist_info.get("images") or [{}])[0].get("url", ""),
        "tracks": tracks,
    }


def _fetch_artist(client: spotipy.Spotify, content_id: str) -> dict[str, Any]:
    """Retorna a discografia completa do artista (álbuns + singles)."""
    artist_info = client.artist(content_id)
    artist_name = artist_info.get("name", "Artista")
    cover_url = (artist_info.get("images") or [{}])[0].get("url", "")

    # Coleta todos os álbuns e singles (sem compilações para evitar duplicatas)
    raw_albums = _paginate(
        client,
        client.artist_albums(content_id, album_type="album,single", limit=50),
    )

    all_tracks: list[dict] = []
    seen_names: set[str] = set()  # Deduplica por nome de álbum

    for album_stub in raw_albums:
        album_name = album_stub.get("name", "")
        # Evita álbuns duplicados (edições regionais, reissues com mesmo nome)
        if album_name.lower() in seen_names:
            continue
        seen_names.add(album_name.lower())

        full_album = client.album(album_stub["id"])
        tracks = _paginate(client, full_album["tracks"])
        _enrich_tracks_with_album(tracks, full_album)
        all_tracks.extend(tracks)

    return {
        "name": artist_name,
        "content_type": "artist",
        "cover_url": cover_url,
        "tracks": all_tracks,
    }


# ─── API Pública ──────────────────────────────────────────────────────────────

def get_spotify_content(client: spotipy.Spotify, url: str) -> dict[str, Any]:
    """
    Busca conteúdo da API Spotify (faixa, álbum, playlist ou artista).

    Returns:
        {
          "name": str,           # Nome do conteúdo
          "content_type": str,   # "track" | "album" | "playlist" | "artist"
          "cover_url": str,      # URL da imagem de capa (pode ser "")
          "tracks": list[dict],  # Lista de objetos de faixa Spotify
        }

    Raises:
        SpotifyContentError: Em casos de URL inválida, credenciais ruins, etc.
    """
    if not client:
        raise SpotifyContentError(
            "Cliente Spotify não inicializado. Configure as credenciais.",
            code="unauthorized",
        )

    try:
        content_type = _detect_content_type(url)
    except SpotifyContentError:
        raise

    content_id = _extract_id(url)
    cache_file = CACHE_DIR / f"{content_type}_{content_id}.json"

    # ── Cache hit (válido por 1 hora) ─────────────────────────────────────────
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < 3600:
            try:
                with open(cache_file, "r", encoding="utf-8") as fh:
                    cached = json.load(fh)
                # Compatibilidade com cache antigo (lista pura)
                if isinstance(cached, list):
                    return {"name": "", "content_type": content_type,
                            "cover_url": "", "tracks": cached}
                return cached
            except (json.JSONDecodeError, OSError):
                cache_file.unlink(missing_ok=True)

    # ── Fetch da API ──────────────────────────────────────────────────────────
    try:
        fetchers = {
            "track":    _fetch_track,
            "album":    _fetch_album,
            "playlist": _fetch_playlist,
            "artist":   _fetch_artist,
        }
        result = fetchers[content_type](client, content_id)

    except spotipy.SpotifyException as exc:
        status = exc.http_status
        http_str = str(status)
        reason = str(exc)

        if status == 401 or "Unauthorized" in reason:
            raise SpotifyContentError(
                "Credenciais inválidas. Verifique o Client ID e Secret.",
                code="unauthorized",
            ) from exc
        if status == 404 or "not found" in reason.lower():
            if "editorial" in reason.lower() or "playlist" in content_type:
                raise SpotifyContentError(
                    "Playlist não encontrada. Playlists editoriais (Daily Mix, "
                    "Release Radar) não são acessíveis via Client Credentials.",
                    code="editorial",
                ) from exc
            raise SpotifyContentError(
                f"Recurso não encontrado (HTTP {http_str}).",
                code="not_found",
            ) from exc
        raise SpotifyContentError(
            f"Erro da API do Spotify (HTTP {http_str}): {reason[:150]}",
            code="api_error",
        ) from exc

    # ── Salva no cache ────────────────────────────────────────────────────────
    try:
        with open(cache_file, "w", encoding="utf-8") as fh:
            json.dump(result, fh)
    except (OSError, TypeError) as exc:
        logger.warning("Não foi possível salvar cache para '%s': %s", content_id, exc)

    return result
