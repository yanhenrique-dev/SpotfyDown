"""
downloader.py — Download e aplicação de metadados para faixas individuais.

Funções públicas:
  build_ydl_opts()   — constrói configuração yt-dlp (pura, testável)
  download_track()   — baixa uma única faixa e aplica metadados
  apply_metadata()   — aplica ID3/FLAC tags ao arquivo de áudio
"""
import os
import re
import logging
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

import yt_dlp
from yt_dlp.utils import DownloadError
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, TRCK, TDRC, TCON
from mutagen.flac import FLAC, Picture

from ..config import config

logger = logging.getLogger(__name__)

# Fase de progresso passada ao callback
ProgressPhase = str  # 'downloading' | 'converting' | 'metadata' | 'done'
ProgressCallback = Callable[[ProgressPhase, float], None]


@dataclass
class DownloadResult:
    """Resultado tipado de um download individual."""
    success: bool
    error: Optional[str] = None

    def __bool__(self) -> bool:
        return self.success


# ─── Helpers ──────────────────────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivo/pasta."""
    name = re.sub(r'[<>:"/\\|?*]', ' ', name)   # replace with space, not ''
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.rstrip('.')
    return name or "Sem Nome"


def build_ydl_opts(
    audio_format: str,
    audio_quality: str,
    output_template: str,
    cookies_browser: str = "",
    cookies_path: str = "",
    progress_hook: Optional[Callable] = None,
) -> dict:
    """
    Constrói o dicionário de opções do yt-dlp.
    Função pura — não acessa estado global (facilita testes).
    """
    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
    }

    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    if cookies_browser:
        opts["cookiesfrombrowser"] = (cookies_browser, None, None, None)
    elif cookies_path and os.path.exists(cookies_path):
        opts["cookiefile"] = cookies_path

    if audio_format == "flac":
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "flac"}
        ]
    else:
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": audio_quality,
            }
        ]

    return opts


# ─── Download principal ───────────────────────────────────────────────────────

def download_track(
    track: dict,
    download_path: str,
    audio_format: str = "mp3",
    audio_quality: str = "320",
    content_name: str = "",
    progress_callback: Optional[ProgressCallback] = None,
) -> DownloadResult:
    """
    Baixa uma única faixa usando yt-dlp e aplica metadados.

    Args:
        track: Objeto de faixa do Spotify (dict)
        download_path: Diretório base de download
        audio_format: 'mp3' ou 'flac'
        audio_quality: Bitrate para MP3 (ex: '320')
        content_name: Nome da playlist/álbum para organizar em subpasta
        progress_callback: Chamado com (phase, fraction 0.0-1.0)

    Returns:
        DownloadResult com success e mensagem de erro opcional
    """
    def _progress(phase: ProgressPhase, pct: float) -> None:
        if progress_callback:
            try:
                progress_callback(phase, pct)
            except Exception:
                pass

    try:
        name = track.get("name", "Desconhecido")
        artists = track.get("artists", [])
        artist = artists[0].get("name", "Desconhecido") if artists else "Desconhecido"
        all_artists = ", ".join(a.get("name", "") for a in artists)
        album_info = track.get("album", {})
        album_name = album_info.get("name", "")

        # Query de busca inclui álbum para reduzir remixes/covers
        search_query = f"{artist} - {name}"
        if album_name:
            search_query += f" {album_name}"

        safe_name = sanitize_filename(f"{artist} - {name}")

        # Subpasta por playlist/álbum
        final_dir = download_path
        if content_name:
            final_dir = os.path.join(download_path, sanitize_filename(content_name))
        os.makedirs(final_dir, exist_ok=True)

        ext = "flac" if audio_format == "flac" else "mp3"
        final_path = os.path.join(final_dir, f"{safe_name}.{ext}")


        if os.path.exists(final_path):
            _progress("done", 1.0)
            return DownloadResult(success=True)

        def ydl_hook(d: dict) -> None:
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    _progress("downloading", 0.75 * downloaded / total)
            elif status == "finished":
                _progress("converting", 0.75)

        ydl_opts = build_ydl_opts(
            audio_format=audio_format,
            audio_quality=audio_quality,
            output_template=os.path.join(final_dir, safe_name),
            cookies_browser=config.cookies_browser,
            cookies_path=config.cookies_path,
            progress_hook=ydl_hook,
        )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                retcode = ydl.download([f"ytsearch1:{search_query} audio"])
                if retcode != 0:
                    raise DownloadError(f"yt-dlp retornou erro {retcode}")
            except DownloadError as exc:
                if "Requested format is not available" in str(exc):
                    logger.warning("Formato indisponível para '%s', tentando fallback...", name)
                    fallback_opts = {**ydl_opts, "format": "best"}
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl2:
                        retcode = ydl2.download([f"ytsearch1:{search_query} audio"])
                        if retcode != 0:
                            raise DownloadError(f"yt-dlp fallback retornou erro {retcode}")
                else:
                    raise

        
        if not os.path.exists(final_path):
            logger.error("Download concluído mas arquivo não encontrado: %s", final_path)
            return DownloadResult(success=False, error="Arquivo não gerado pelo conversor")

        _progress("metadata", 0.90)
        apply_metadata(final_path, track)
        _progress("done", 1.0)

        return DownloadResult(success=True)

    except DownloadError as exc:
        logger.error("yt-dlp falhou para '%s': %s", track.get("name", "?"), exc)
        return DownloadResult(success=False, error=f"Download falhou: {exc}")
    except Exception as exc:
        logger.exception("Erro inesperado ao baixar '%s'", track.get("name", "?"))
        return DownloadResult(success=False, error=str(exc))


# ─── Metadados ────────────────────────────────────────────────────────────────

def _download_cover(images: list[dict], title: str) -> Optional[bytes]:
    """Baixa a imagem de maior resolução disponível. Retorna None se falhar."""
    if not images:
        return None
    url = images[0].get("url", "")
    if not url:
        return None
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read()
    except Exception as exc:
        logger.warning("Não foi possível baixar capa para '%s': %s", title, exc)
        return None


def apply_metadata(path: str, track: dict) -> None:
    """Aplica metadados ID3 (MP3) ou Vorbis Comments (FLAC) ao arquivo de áudio."""
    title = track.get("name", "")
    artists = track.get("artists", [])
    artist_str = ", ".join(a.get("name", "") for a in artists)
    album_info = track.get("album", {})
    album = album_info.get("name", "")
    track_number = str(track.get("track_number", ""))
    disc_number = str(track.get("disc_number", ""))
    release_date = album_info.get("release_date", "")
    year = release_date[:4] if release_date else ""
    genres = track.get("genres") or album_info.get("genres") or []
    genre_str = ", ".join(genres)

    img_data = _download_cover(album_info.get("images", []), title)

    try:
        if path.endswith(".mp3"):
            _apply_mp3(path, title, artist_str, album, track_number,
                       disc_number, year, genre_str, img_data)
        elif path.endswith(".flac"):
            _apply_flac(path, title, artist_str, album, track_number,
                        disc_number, year, genre_str, img_data)
    except Exception as exc:
        logger.error("Erro ao aplicar metadados para '%s': %s", title, exc)


def _apply_mp3(path, title, artist, album, track_number, disc_number,
               year, genre, img_data):
    audio = MP3(path, ID3=ID3)
    try:
        audio.add_tags()
    except Exception:
        pass  # Tags já existem

    tags = audio.tags
    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    tags.add(TALB(encoding=3, text=album))
    if track_number:
        tags.add(TRCK(encoding=3, text=track_number))
    if year:
        tags.add(TDRC(encoding=3, text=year))
    if genre:
        tags.add(TCON(encoding=3, text=genre))
    if img_data:
        tags.add(APIC(encoding=3, mime="image/jpeg", type=3,
                      desc="Cover", data=img_data))
    audio.save()


def _apply_flac(path, title, artist, album, track_number, disc_number,
                year, genre, img_data):
    audio = FLAC(path)
    audio["title"] = title
    audio["artist"] = artist
    audio["album"] = album
    if track_number:
        audio["tracknumber"] = track_number
    if disc_number:
        audio["discnumber"] = disc_number
    if year:
        audio["date"] = year
    if genre:
        audio["genre"] = genre
    if img_data:
        pic = Picture()
        pic.data = img_data
        pic.type = 3
        pic.mime = "image/jpeg"
        audio.clear_pictures()
        audio.add_picture(pic)
    audio.save()
