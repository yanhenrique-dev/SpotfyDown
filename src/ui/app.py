"""
ui/app.py — Orchestrador principal do SpotifyDownloader (ponto de entrada GTK).
Delega toda a lógica de UI a SearchPage, ResultsPage e SettingsDialog.
"""
import shutil
import logging
import threading
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, GLib, Gio

from ..config import config
from ..core.spotify import get_spotify_content, SpotifyContentError
from ..core.download_manager import DownloadManager
from .search_page import SearchPage
from .results_page import ResultsPage
from .settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)

# Mensagens de erro amigáveis mapeadas pelo código tipado
_ERROR_MESSAGES: dict[str, str] = {
    "invalid_url": "Link inválido. Cole um link do Spotify (open.spotify.com/...).",
    "unauthorized": "Credenciais inválidas. Verifique o Client ID e Secret nas configurações.",
    "not_found": "Conteúdo não encontrado. Verifique se o link está correto.",
    "editorial": (
        "Playlists editoriais (Daily Mix, Release Radar) não são acessíveis "
        "com Client Credentials do Spotify."
    ),
    "api_error": "Erro na API do Spotify. Tente novamente mais tarde.",
}


class SpotifyDownloaderApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="com.github.spotifydownloader.pro", **kwargs)
        self._download_manager = DownloadManager()
        self.connect("startup", self._on_startup)
        self.connect("activate", self._on_activate)

    # ── Ciclo de vida GTK ───────────────────────────────────────────────────

    def _on_startup(self, _app) -> None:
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK)

    def _on_activate(self, _app) -> None:
        config.load_config()

        self._win = Adw.ApplicationWindow(
            application=self, title="Spotify Downloader Ultra"
        )
        self._win.set_default_size(1000, 750)

        # Toast overlay envolve tudo
        self._toast_overlay = Adw.ToastOverlay()
        self._win.set_content(self._toast_overlay)

        # ToolbarView global
        toolbar_view = Adw.ToolbarView()
        self._toast_overlay.set_child(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        self._back_btn = Gtk.Button(icon_name="go-previous-symbolic")
        self._back_btn.set_visible(False)
        self._back_btn.connect("clicked", lambda _: self._show_search())
        header.pack_start(self._back_btn)

        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.connect("clicked", lambda _: self._open_settings())
        header.pack_end(settings_btn)

        # Stack: search | results
        self._stack = Adw.ViewStack()
        toolbar_view.set_content(self._stack)

        self._search_page = SearchPage(
            on_search=self._start_search,
            api_configured=bool(config.client_id),
        )
        self._stack.add_titled(self._search_page, "search", "Busca")

        self._results_page = ResultsPage(
            on_download=self._start_download,
            on_cancel=self._download_manager.cancel,
        )
        self._stack.add_titled(self._results_page, "results", "Lista")

        self._check_ffmpeg()
        self._win.present()

    # ── Busca ──────────────────────────────────────────────────────────────

    def _start_search(self, url: str) -> None:
        if not config.spotify_client:
            self._toast("Configure a API do Spotify primeiro!")
            return
        self._search_page.set_loading(True)
        threading.Thread(target=self._fetch_content, args=(url,), daemon=True).start()

    def _fetch_content(self, url: str) -> None:
        try:
            result = get_spotify_content(config.spotify_client, url)
            tracks = result.get("tracks", [])
            name = result.get("name", "")
            GLib.idle_add(self._populate_results, tracks, name)
        except SpotifyContentError as exc:
            msg = _ERROR_MESSAGES.get(exc.code, f"Erro: {exc}")
            GLib.idle_add(self._toast, msg, 6)
            GLib.idle_add(self._search_page.set_loading, False)
        except Exception as exc:
            logger.exception("Erro inesperado ao buscar conteúdo do Spotify.")
            GLib.idle_add(self._toast, f"Erro inesperado: {str(exc)[:120]}", 6)
            GLib.idle_add(self._search_page.set_loading, False)

    def _populate_results(self, tracks: list, name: str) -> None:
        self._results_page.populate(tracks, name)
        self._search_page.set_loading(False)
        self._search_page.set_api_configured(True)
        self._stack.set_visible_child_name("results")
        self._back_btn.set_visible(True)

    def _show_search(self) -> None:
        self._stack.set_visible_child_name("search")
        self._back_btn.set_visible(False)

    # ── Downloads ──────────────────────────────────────────────────────────

    def _start_download(self, rows: list) -> None:
        self._results_page.set_downloading(True)
        self._back_btn.set_sensitive(False)
        self._download_manager.start(
            rows,
            on_row_start=lambda r: r.set_downloading_state(),
            on_row_progress=self._results_page.update_row_progress,
            on_row_done=self._results_page.row_done,
            on_all_done=self._on_all_done,
        )

    def _on_all_done(self, success: int, total: int, cancelled: bool) -> None:
        self._results_page.all_done(success, total, cancelled)
        self._back_btn.set_sensitive(True)

        msg = "Cancelado pelo usuário." if cancelled else f"{success}/{total} músicas baixadas."
        self._toast(msg, timeout=4, action_label="Abrir Pasta",
                    action_cb=lambda: self._open_folder())
        self._send_notification(success, total, cancelled)

    # ── Configurações ──────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        SettingsDialog(
            parent=self._win,
            on_saved=self._on_settings_saved,
        ).present()

    def _on_settings_saved(self) -> None:
        self._toast("Configurações salvas!")
        self._search_page.set_api_configured(bool(config.client_id))

    # ── Utilitários ────────────────────────────────────────────────────────

    def _toast(self, msg: str, timeout: int = 3,
               action_label: str = "", action_cb=None) -> None:
        toast = Adw.Toast.new(msg)
        toast.set_timeout(timeout)
        if action_label and action_cb:
            toast.set_button_label(action_label)
            toast.connect("button-clicked", lambda _: action_cb())
        self._toast_overlay.add_toast(toast)

    def _check_ffmpeg(self) -> None:
        if not shutil.which("ffmpeg"):
            self._toast("⚠️ FFmpeg não encontrado. Instale para melhor qualidade.", 5)

    def _open_folder(self) -> None:
        import os
        import subprocess
        try:
            os.makedirs(config.download_path, exist_ok=True)
            subprocess.Popen(["xdg-open", config.download_path])
        except Exception:
            logger.exception("Erro ao abrir pasta de downloads.")

    def _send_notification(self, success: int, total: int, cancelled: bool) -> None:
        try:
            n = Gio.Notification.new("Spotify Downloader")
            body = "Download cancelado." if cancelled else f"{success} de {total} músicas baixadas."
            n.set_body(body)
            n.set_priority(Gio.NotificationPriority.NORMAL)
            self.send_notification(None, n)
        except Exception:
            logger.warning("Não foi possível enviar notificação do sistema.")
