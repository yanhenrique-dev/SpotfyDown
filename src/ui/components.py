import html
import logging
import threading
import urllib.request
from pathlib import Path
from gi.repository import Gtk, Adw, GLib, Gdk

from ..config import CACHE_DIR

logger = logging.getLogger(__name__)

class TrackRow(Adw.ActionRow):
    """
    Linha da lista melhorada com suporte a Capas e Progresso Individual.
    """
    def __init__(self, track, **kwargs):
        super().__init__(**kwargs)
        self.track = track
        
        # Dados básicos
        title = html.escape(track.get('name') or 'Desconhecido')
        artists = track.get('artists', [])
        artist_name = html.escape((artists[0].get('name') if artists else None) or 'Desconhecido')
        album_name = html.escape(track.get('album', {}).get('name', ''))
        
        self.set_title(title)
        
        # Subtitle com artista e álbum
        if album_name:
            self.set_subtitle(f"{artist_name}  •  {album_name}")
        else:
            self.set_subtitle(artist_name)
        
        # Duração da faixa
        duration_ms = track.get('duration_ms', 0)
        if duration_ms > 0:
            mins = duration_ms // 60000
            secs = (duration_ms % 60000) // 1000
            duration_label = Gtk.Label(label=f"{mins}:{secs:02d}")
            duration_label.add_css_class("dim-label")
            duration_label.add_css_class("caption")
            duration_label.set_valign(Gtk.Align.CENTER)
            self.add_suffix(duration_label)
        
        # Imagem da Capa (Placeholder inicial)
        self.cover_img = Gtk.Image.new_from_icon_name("folder-music-symbolic")
        self.cover_img.set_pixel_size(48)
        self.add_prefix(self.cover_img)
        
        # Checkbox de seleção
        self.check = Gtk.CheckButton()
        self.check.set_active(True)
        self.check.set_valign(Gtk.Align.CENTER)
        self.add_suffix(self.check)
        
        # Barra de Progresso Individual (Oculta inicialmente)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_size_request(100, -1)
        self.progress_bar.set_valign(Gtk.Align.CENTER)
        self.progress_bar.set_visible(False)
        self.add_suffix(self.progress_bar)

        # Ícone de Status
        self.status_icon = Gtk.Image()
        self.status_icon.set_visible(False)
        self.add_suffix(self.status_icon)

        # Inicia carregamento da imagem em background
        self.load_cover_async()

    def load_cover_async(self):
        """Baixa a capa em thread separada para não travar a UI"""
        threading.Thread(target=self._fetch_image, daemon=True).start()

    def _fetch_image(self):
        try:
            imgs = self.track.get('album', {}).get('images', [])
            if not imgs:
                return
            
            # Pega a menor imagem para a lista (thumbnail)
            url = imgs[-1]['url'] 
            track_id = self.track.get('id', 'unknown')
            filename = CACHE_DIR / f"thumb_{track_id}.jpg"
            
            if not filename.exists():
                urllib.request.urlretrieve(url, filename)
            
            # Atualiza UI na thread principal
            GLib.idle_add(self._update_cover_ui, str(filename))
        except Exception:
            logger.warning("Erro ao baixar capa da faixa '%s'", self.track.get('name', ''))

    def _update_cover_ui(self, filepath):
        try:
            paintable = Gdk.Texture.new_from_filename(filepath)
            self.cover_img.set_from_paintable(paintable)
        except Exception:
            logger.debug("Não foi possível renderizar capa (usando placeholder).")

    def set_downloading_state(self):
        self.check.set_visible(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)

    def update_progress(self, fraction):
        """Atualiza progresso real (0.0 a 1.0)"""
        self.progress_bar.set_fraction(min(fraction, 1.0))

    def set_finished_state(self, success):
        self.progress_bar.set_visible(False)
        self.status_icon.set_visible(True)
        if success:
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
            self.status_icon.add_css_class("success")
        else:
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
            self.status_icon.add_css_class("error")
