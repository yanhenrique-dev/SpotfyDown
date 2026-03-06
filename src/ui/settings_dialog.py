"""
ui/settings_dialog.py — Janela de configurações de preferências.
"""
import os
import logging
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

from ..config import config

logger = logging.getLogger(__name__)

_BROWSERS = ["chrome", "firefox", "opera", "edge", "chromium"]


class SettingsDialog(Adw.PreferencesWindow):
    """
    Janela de configurações — API do Spotify, autenticação YouTube e preferências de download.
    Chama `on_saved()` após salvar com sucesso.
    """

    def __init__(self, parent, on_saved=None, **kwargs):
        super().__init__(transient_for=parent, title="Configurações", **kwargs)
        self._on_saved = on_saved
        self._build_ui()

    # ── Construção ────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        page = Adw.PreferencesPage()
        try:
            self.add_page(page)
        except AttributeError:
            self.add(page)

        # ── Credenciais Spotify ──────────────────────────────────────────────
        grp_api = Adw.PreferencesGroup(
            title="Spotify API",
            description="Credenciais em open.spotify.com/developer",
        )
        page.add(grp_api)

        self._row_id = Adw.EntryRow(title="Client ID")
        self._row_id.set_text(config.client_id)
        grp_api.add(self._row_id)

        self._row_sec = Adw.PasswordEntryRow(title="Client Secret")
        self._row_sec.set_text(config.client_secret)
        grp_api.add(self._row_sec)

        # ── Autenticação YouTube ─────────────────────────────────────────────
        grp_yt = Adw.PreferencesGroup(
            title="Autenticação do YouTube",
            description="Necessário apenas se o YouTube bloquear downloads",
        )
        page.add(grp_yt)

        self._combo_auth = Adw.ComboRow(title="Método")
        auth_model = Gtk.StringList()
        for m in ["Sem Autenticação", "Arquivo cookies.txt", "Extrair do Navegador"]:
            auth_model.append(m)
        self._combo_auth.set_model(auth_model)
        grp_yt.add(self._combo_auth)

        self._row_cookies = Adw.EntryRow(title="Caminho do cookies.txt")
        self._row_cookies.set_text(config.cookies_path)
        self._row_cookies.set_show_apply_button(True)
        btn_file = Gtk.Button(icon_name="folder-open-symbolic")
        btn_file.set_valign(Gtk.Align.CENTER)
        btn_file.connect("clicked", self._on_select_cookies)
        self._row_cookies.add_suffix(btn_file)
        grp_yt.add(self._row_cookies)

        self._combo_browser = Adw.ComboRow(title="Navegador")
        browser_model = Gtk.StringList()
        for b in _BROWSERS:
            browser_model.append(b)
        self._combo_browser.set_model(browser_model)
        if config.cookies_browser in _BROWSERS:
            self._combo_browser.set_selected(_BROWSERS.index(config.cookies_browser))
        grp_yt.add(self._combo_browser)

        self._combo_auth.connect("notify::selected", self._on_auth_method_changed)
        if config.cookies_browser:
            self._combo_auth.set_selected(2)
        elif config.cookies_path:
            self._combo_auth.set_selected(1)
        else:
            self._combo_auth.set_selected(0)
        self._on_auth_method_changed(None, None)

        # ── Qualidade de download ────────────────────────────────────────────
        grp_dl = Adw.PreferencesGroup(title="Preferências de Download")
        page.add(grp_dl)

        self._combo_quality = Adw.ComboRow(title="Qualidade / Formato")
        quality_model = Gtk.StringList()
        for q in ["MP3 Alta Qualidade (320kbps)", "MP3 Leve (128kbps)", "FLAC (Lossless)"]:
            quality_model.append(q)
        self._combo_quality.set_model(quality_model)
        if config.audio_format == "flac":
            self._combo_quality.set_selected(2)
        elif config.audio_quality == "128":
            self._combo_quality.set_selected(1)
        else:
            self._combo_quality.set_selected(0)
        grp_dl.add(self._combo_quality)

        # ── Ações ────────────────────────────────────────────────────────────
        grp_actions = Adw.PreferencesGroup()
        page.add(grp_actions)

        btn_save = Gtk.Button(label="Salvar", margin_top=20)
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", self._on_save)
        grp_actions.add(btn_save)

        btn_open = Gtk.Button(label="Abrir Pasta de Downloads", margin_top=10)
        btn_open.connect("clicked", lambda _: self._open_folder())
        grp_actions.add(btn_open)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_auth_method_changed(self, _combo, _param) -> None:
        idx = self._combo_auth.get_selected()
        self._row_cookies.set_visible(idx == 1)
        self._combo_browser.set_visible(idx == 2)

    def _on_select_cookies(self, _btn) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Selecione o arquivo cookies.txt")
        f = Gtk.FileFilter()
        f.set_name("Text Files")
        f.add_pattern("*.txt")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self.get_transient_for(), None, self._on_cookies_selected)

    def _on_cookies_selected(self, dialog, result) -> None:
        try:
            file = dialog.open_finish(result)
            if file:
                self._row_cookies.set_text(file.get_path())
        except Exception:
            logger.debug("Seleção de arquivo de cookies cancelada.")

    def _on_save(self, _btn) -> None:
        quality_map = {0: ("mp3", "320"), 1: ("mp3", "128"), 2: ("flac", "0")}
        fmt, qual = quality_map.get(self._combo_quality.get_selected(), ("mp3", "320"))

        auth_idx = self._combo_auth.get_selected()
        cookies = self._row_cookies.get_text() if auth_idx == 1 else ""
        browser = _BROWSERS[self._combo_browser.get_selected()] if auth_idx == 2 else ""

        config.save_config(
            self._row_id.get_text(),
            self._row_sec.get_text(),
            fmt,
            qual,
            cookies,
            browser,
        )

        self.close()
        if self._on_saved:
            self._on_saved()

    def _open_folder(self) -> None:
        try:
            os.makedirs(config.download_path, exist_ok=True)
            import subprocess
            subprocess.Popen(["xdg-open", config.download_path])
        except Exception:
            logger.exception("Erro ao abrir pasta de downloads.")
