"""
DownloadManager — gerencia a fila de downloads em paralelo.
Separa toda a lógica de threading/execução de app.py.
"""
import os
import logging
import threading
import concurrent.futures
from gi.repository import GLib

from ..config import config
from .downloader import download_track

logger = logging.getLogger(__name__)

_DEFAULT_MAX_WORKERS = 3


class DownloadManager:
    """
    Gerencia downloads paralelos de faixas.

    Uso:
        dm = DownloadManager()
        dm.start(rows, on_progress=callback, on_done=callback)
        dm.cancel()
    """

    def __init__(self):
        self._stop_event = threading.Event()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, rows, on_row_start=None, on_row_progress=None,
              on_row_done=None, on_all_done=None):
        """
        Inicia downloads em background.

        Args:
            rows: lista de TrackRow com atributo .track
            on_row_start(row): chamado quando uma faixa começa
            on_row_progress(row, pct): chamado com progresso 0.0-1.0
            on_row_done(row, success, done, total, successes): chamado ao terminar cada faixa
            on_all_done(success_count, total, cancelled): chamado ao finalizar tudo
        """
        if self._running:
            logger.warning("DownloadManager: tentativa de iniciar enquanto já está rodando.")
            return

        self._stop_event.clear()
        self._running = True

        thread = threading.Thread(
            target=self._run,
            args=(rows, on_row_start, on_row_progress, on_row_done, on_all_done),
            daemon=True,
        )
        thread.start()

    def cancel(self):
        """Sinaliza cancelamento. Downloads em andamento terminam o arquivo atual."""
        self._stop_event.set()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self, rows, on_row_start, on_row_progress, on_row_done, on_all_done):
        os.makedirs(config.download_path, exist_ok=True)
        total = len(rows)
        max_workers = getattr(config, "max_workers", _DEFAULT_MAX_WORKERS)

        if on_row_start:
            for row in rows:
                GLib.idle_add(on_row_start, row)

        done_count = 0
        success_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

            def make_progress(row):
                def cb(phase: str, pct: float):
                    if on_row_progress:
                        GLib.idle_add(on_row_progress, row, pct)
                return cb

            futures = {
                executor.submit(
                    download_track,
                    row.track,
                    config.download_path,
                    config.audio_format,
                    config.audio_quality,
                    row.content_name if hasattr(row, "content_name") else "",
                    make_progress(row),
                ): row
                for row in rows
            }

            for future in concurrent.futures.as_completed(futures):
                if self._stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                row = futures[future]
                try:
                    result = future.result()
                    success = bool(result)  # DownloadResult is bool-compatible
                except Exception:
                    logger.exception("Erro inesperado no future do download.")
                    success = False

                done_count += 1
                if success:
                    success_count += 1

                if on_row_done:
                    GLib.idle_add(on_row_done, row, success, done_count, total, success_count)

        self._running = False

        if on_all_done:
            cancelled = self._stop_event.is_set()
            GLib.idle_add(on_all_done, success_count, total, cancelled)
