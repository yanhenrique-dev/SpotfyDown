"""
ui/search_page.py — Página inicial de busca (URL do Spotify).
"""
import logging
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

logger = logging.getLogger(__name__)


class SearchPage(Gtk.Box):
    """
    Página central com campo de URL e dicas de uso.

    Sinais (emulados via callbacks):
        on_search(url: str) — chamado quando o usuário clica em Buscar
    """

    def __init__(self, on_search, api_configured: bool = False, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)
        self._on_search = on_search

        # Banner de aviso se API não configurada
        self.api_banner = Adw.Banner(
            title="Configure a API do Spotify nas ⚙ Configurações para começar."
        )
        self.api_banner.set_revealed(not api_configured)
        self.append(self.api_banner)

        # Área central
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        center.set_vexpand(True)
        center.set_valign(Gtk.Align.CENTER)
        center.set_margin_start(32)
        center.set_margin_end(32)

        # Ícone grande
        icon = Gtk.Image.new_from_icon_name("folder-music-symbolic")
        icon.set_pixel_size(96)
        icon.add_css_class("dim-label")
        center.append(icon)

        # Título
        title_lbl = Gtk.Label(label="Spotify Downloader")
        title_lbl.add_css_class("title-1")
        center.append(title_lbl)

        # Subtítulo
        sub_lbl = Gtk.Label(
            label="Cole o link de uma playlist, álbum, artista ou faixa do Spotify"
        )
        sub_lbl.add_css_class("dim-label")
        sub_lbl.set_wrap(True)
        sub_lbl.set_justify(Gtk.Justification.CENTER)
        center.append(sub_lbl)

        # Entrada + botão
        clamp = Adw.Clamp(maximum_size=520)
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_box.add_css_class("linked")

        self.url_entry = Gtk.Entry(
            placeholder_text="https://open.spotify.com/playlist/..."
        )
        self.url_entry.set_hexpand(True)
        self.url_entry.connect("activate", self._on_activate)

        self.search_btn = Gtk.Button(label="Buscar")
        self.search_btn.add_css_class("suggested-action")
        self.search_btn.connect("clicked", self._on_activate)

        input_box.append(self.url_entry)
        input_box.append(self.search_btn)
        clamp.set_child(input_box)
        center.append(clamp)

        # Spinner de carregamento
        self.spinner = Gtk.Spinner()
        center.append(self.spinner)

        # Chips de dicas
        tips_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        tips_box.set_halign(Gtk.Align.CENTER)
        tips_box.set_margin_top(8)
        for icon_name, tip in [
            ("audio-x-generic-symbolic", "Faixas"),
            ("media-optical-symbolic", "Álbuns"),
            ("playlist-symbolic", "Playlists"),
            ("avatar-default-symbolic", "Artistas"),
        ]:
            col = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            col.set_halign(Gtk.Align.CENTER)
            ic = Gtk.Image.new_from_icon_name(icon_name)
            ic.add_css_class("dim-label")
            lbl = Gtk.Label(label=tip)
            lbl.add_css_class("dim-label")
            lbl.add_css_class("caption")
            col.append(ic)
            col.append(lbl)
            tips_box.append(col)

        center.append(tips_box)
        self.append(center)

    # ── API pública ───────────────────────────────────────────────────────────

    def set_loading(self, loading: bool) -> None:
        """Ativa/desativa estado de carregamento."""
        if loading:
            self.spinner.start()
            self.search_btn.set_sensitive(False)
        else:
            self.spinner.stop()
            self.search_btn.set_sensitive(True)

    def set_api_configured(self, configured: bool) -> None:
        self.api_banner.set_revealed(not configured)

    def get_url(self) -> str:
        return self.url_entry.get_text().strip()

    def clear(self) -> None:
        self.url_entry.set_text("")

    # ── Callbacks internos ────────────────────────────────────────────────────

    def _on_activate(self, _widget) -> None:
        url = self.url_entry.get_text().strip()
        if url and self._on_search:
            self._on_search(url)
