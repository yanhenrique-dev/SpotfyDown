"""
ui/results_page.py — Página de resultados com lista de faixas e barra de ações.
"""
import logging
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from .components import TrackRow

logger = logging.getLogger(__name__)


class ResultsPage(Gtk.Box):
    """
    Exibe a lista de faixas, barra superior de filtros e barra de ação inferior.

    Callbacks:
        on_download(rows) — lista de TrackRow selecionados
        on_cancel()       — solicita cancelamento
    """

    def __init__(self, on_download, on_cancel, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self._on_download_cb = on_download
        self._on_cancel_cb = on_cancel
        self._rows: list[TrackRow] = []

        # ── Header com nome do conteúdo ──────────────────────────────────────
        self.content_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.content_header.set_margin_top(16)
        self.content_header.set_margin_start(16)
        self.content_header.set_margin_end(16)
        self.content_header.set_margin_bottom(8)

        self.content_name_label = Gtk.Label(label="")
        self.content_name_label.add_css_class("title-2")
        self.content_name_label.set_halign(Gtk.Align.START)
        self.content_name_label.set_ellipsize(3)
        self.content_header.append(self.content_name_label)

        self.content_subtitle = Gtk.Label(label="")
        self.content_subtitle.add_css_class("dim-label")
        self.content_subtitle.set_halign(Gtk.Align.START)
        self.content_header.append(self.content_subtitle)

        self.content_header.set_visible(False)
        self.append(self.content_header)

        # ── Toolbar de seleção + filtro ──────────────────────────────────────
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(8)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)

        btn_all = Gtk.Button(label="Todos")
        btn_all.connect("clicked", lambda _: self._toggle_all(True))
        btn_none = Gtk.Button(label="Nenhum")
        btn_none.connect("clicked", lambda _: self._toggle_all(False))

        toolbar.append(Gtk.Label(label="Seleção:"))
        toolbar.append(btn_all)
        toolbar.append(btn_none)
        toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        self.lbl_count = Gtk.Label(label="0 Faixas")
        toolbar.append(self.lbl_count)

        # Filtro de texto
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar.append(spacer)

        self.filter_entry = Gtk.SearchEntry(placeholder_text="Filtrar...")
        self.filter_entry.set_max_width_chars(24)
        self.filter_entry.connect("search-changed", self._on_filter_changed)
        toolbar.append(self.filter_entry)

        self.append(toolbar)

        # ── Lista de faixas ──────────────────────────────────────────────────
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)

        # Filtro personalizado
        self.list_box.set_filter_func(self._filter_func)

        clamp = Adw.Clamp(maximum_size=800)
        clamp.set_child(self.list_box)
        scrolled.set_child(clamp)
        self.append(scrolled)

        # ── Barra de ação inferior ───────────────────────────────────────────
        action_bar = Gtk.ActionBar()

        self.cancel_btn = Gtk.Button(
            label="Cancelar", icon_name="process-stop-symbolic"
        )
        self.cancel_btn.add_css_class("destructive-action")
        self.cancel_btn.set_visible(False)
        self.cancel_btn.connect("clicked", self._on_cancel)
        action_bar.pack_start(self.cancel_btn)

        center_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        center_col.set_halign(Gtk.Align.CENTER)

        self.status_label = Gtk.Label(label="Pronto")
        center_col.append(self.status_label)

        self.global_progress = Gtk.ProgressBar()
        self.global_progress.set_size_request(200, -1)
        self.global_progress.set_visible(False)
        center_col.append(self.global_progress)

        action_bar.set_center_widget(center_col)

        self.download_btn = Gtk.Button(label="Baixar Selecionados")
        self.download_btn.add_css_class("suggested-action")
        self.download_btn.add_css_class("pill")
        self.download_btn.connect("clicked", self._on_download)
        action_bar.pack_end(self.download_btn)

        self.append(action_bar)

    # ── API pública ───────────────────────────────────────────────────────────

    def populate(self, tracks: list[dict], content_name: str = "") -> None:
        """Preenche a lista com as faixas fornecidas."""
        self._rows.clear()
        self.list_box.remove_all()
        self.filter_entry.set_text("")

        if content_name:
            self.content_name_label.set_text(content_name)
            self.content_subtitle.set_text(f"Salvo em: {content_name}/")
            self.content_header.set_visible(True)
        else:
            self.content_header.set_visible(False)

        for track in tracks:
            row = TrackRow(track)
            row.content_name = content_name
            self.list_box.append(row)
            self._rows.append(row)

        self.lbl_count.set_text(f"{len(tracks)} Faixas")
        self._update_status("Pronto")

    def set_downloading(self, downloading: bool) -> None:
        """Alterna entre estado de download e estado de repouso."""
        self.download_btn.set_sensitive(not downloading)
        self.cancel_btn.set_visible(downloading)
        self.cancel_btn.set_sensitive(downloading)
        self.global_progress.set_visible(downloading)
        if downloading:
            self.global_progress.set_fraction(0.0)

    def update_row_progress(self, row: TrackRow, pct: float) -> None:
        row.update_progress(pct)

    def row_done(self, row: TrackRow, success: bool,
                 done: int, total: int, successes: int) -> None:
        row.set_finished_state(success)
        self._update_status(f"Processando {done}/{total} ({successes} ✓)")
        self.global_progress.set_fraction(done / total)

    def all_done(self, success_count: int, total: int, cancelled: bool) -> None:
        self.set_downloading(False)
        if cancelled:
            msg = "Cancelado pelo usuário."
        else:
            msg = f"Concluído! {success_count}/{total} com sucesso."
        self._update_status(msg)

    def _update_status(self, msg: str) -> None:
        self.status_label.set_text(msg)

    def get_selected_rows(self) -> list[TrackRow]:
        return [r for r in self._rows if r.check.get_active() and r.get_visible()]

    # ── Callbacks internos ────────────────────────────────────────────────────

    def _toggle_all(self, state: bool) -> None:
        for row in self._rows:
            row.check.set_active(state)

    def _on_filter_changed(self, entry) -> None:
        self.list_box.invalidate_filter()

    def _filter_func(self, row) -> bool:
        query = self.filter_entry.get_text().lower()
        if not query:
            return True
        if not isinstance(row, TrackRow):
            return True
        track = getattr(row, "track", {})
        name = track.get("name", "").lower()
        artists = ", ".join(a.get("name", "") for a in track.get("artists", [])).lower()
        album = track.get("album", {}).get("name", "").lower()
        return query in name or query in artists or query in album

    def _on_download(self, _btn) -> None:
        rows = self.get_selected_rows()
        if rows and self._on_download_cb:
            self._on_download_cb(rows)

    def _on_cancel(self, _btn) -> None:
        self.cancel_btn.set_sensitive(False)
        self._update_status("Cancelando...")
        if self._on_cancel_cb:
            self._on_cancel_cb()
