import json
import logging
from pathlib import Path
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

logger = logging.getLogger(__name__)

# --- CONSTANTES ---
CACHE_DIR = Path.home() / ".cache" / "spotify_downloader"
CONFIG_FILE = Path.home() / ".spotify_downloader_config.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Tenta usar keyring; se não disponível, usa armazenamento em texto (fallback)
try:
    import keyring
    _KEYRING_SERVICE = "spotify_downloader"
    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False
    logger.debug("keyring não disponível; client_secret armazenado em JSON.")


def _keyring_get(key: str) -> str:
    """Lê segredo do keyring, retornando '' em caso de falha."""
    if not _KEYRING_AVAILABLE:
        return ""
    try:
        value = keyring.get_password(_KEYRING_SERVICE, key)
        return value or ""
    except Exception as exc:
        logger.debug("keyring.get_password falhou para '%s': %s", key, exc)
        return ""


def _keyring_set(key: str, value: str) -> None:
    """Grava segredo no keyring."""
    if not _KEYRING_AVAILABLE:
        return
    try:
        keyring.set_password(_KEYRING_SERVICE, key, value)
    except Exception as exc:
        logger.debug("keyring.set_password falhou para '%s': %s", key, exc)


class ConfigManager:
    def __init__(self) -> None:
        self.client_id: str = ""
        self.client_secret: str = ""
        self.download_path: str = str(Path.home() / "Downloads" / "Spotify")
        self.cookies_path: str = ""
        self.cookies_browser: str = ""
        self.audio_format: str = "mp3"
        self.audio_quality: str = "320"
        self.max_workers: int = 3
        self.spotify_client: Optional[spotipy.Spotify] = None

    def load_config(self) -> None:
        if not CONFIG_FILE.exists():
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
                c = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Falha ao carregar config (%s); usando valores padrão.", exc)
            return

        self.client_id = c.get("client_id", "")
        self.download_path = c.get("path", self.download_path)
        self.cookies_path = c.get("cookies_path", "")
        self.cookies_browser = c.get("cookies_browser", "")
        self.audio_format = c.get("format", "mp3")
        self.audio_quality = c.get("quality", "320")
        self.max_workers = int(c.get("max_workers", 3))

        # Prefere keyring; cai para JSON legacy somente se keyring vazio
        self.client_secret = _keyring_get("client_secret") or c.get("client_secret", "")

        if self.client_id:
            self.init_spotify_client()

    def save_config(
        self,
        cid: str,
        csec: str,
        fmt: str,
        qual: str,
        cookies: str = "",
        browser: str = "",
        max_workers: int = 3,
    ) -> None:
        """Salva configurações. client_secret vai para keyring (se disponível)."""
        self.client_id = cid
        self.client_secret = csec
        self.cookies_path = cookies
        self.cookies_browser = browser
        self.audio_format = fmt
        self.audio_quality = qual
        self.max_workers = max_workers

        # Armazena segredo no keyring; JSON guarda apenas referência
        _keyring_set("client_secret", csec)

        cfg = {
            "client_id": cid,
            # Omite client_secret do JSON quando keyring disponível
            **({"client_secret": csec} if not _KEYRING_AVAILABLE else {}),
            "path": self.download_path,
            "cookies_path": cookies,
            "cookies_browser": browser,
            "format": fmt,
            "quality": qual,
            "max_workers": max_workers,
        }

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2)
        except OSError as exc:
            logger.error("Não foi possível gravar o arquivo de configuração: %s", exc)

        if self.client_id:
            self.init_spotify_client()

    def init_spotify_client(self) -> None:
        try:
            auth = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            self.spotify_client = spotipy.Spotify(auth_manager=auth)
            logger.info("Cliente Spotify inicializado com sucesso.")
        except Exception as exc:
            self.spotify_client = None
            logger.error("Falha ao inicializar cliente Spotify: %s", exc)


# Global instance
config = ConfigManager()
