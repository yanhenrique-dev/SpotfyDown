"""
tests/core/test_downloader.py — Testes unitários para core/downloader.py
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from src.core.downloader import (
    sanitize_filename,
    build_ydl_opts,
    apply_metadata,
    DownloadResult,
)


class TestSanitizeFilename:
    def test_removes_invalid_chars(self):
        assert sanitize_filename('Track: "Special/File"') == "Track Special File"

    def test_collapses_whitespace(self):
        assert sanitize_filename("A   B") == "A B"

    def test_strips_trailing_dot(self):
        assert sanitize_filename("Name.") == "Name"

    def test_empty_becomes_default(self):
        result = sanitize_filename("  ")
        assert result == "Sem Nome"

    def test_normal_name_unchanged(self):
        assert sanitize_filename("My Song - Arctic Monkeys") == "My Song - Arctic Monkeys"


class TestBuildYdlOpts:
    def test_mp3_format(self):
        opts = build_ydl_opts("mp3", "320", "/tmp/test")
        post = opts["postprocessors"][0]
        assert post["key"] == "FFmpegExtractAudio"
        assert post["preferredcodec"] == "mp3"
        assert post["preferredquality"] == "320"

    def test_flac_format(self):
        opts = build_ydl_opts("flac", "0", "/tmp/test")
        post = opts["postprocessors"][0]
        assert post["preferredcodec"] == "flac"

    def test_cookies_file(self, tmp_path):
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("")
        opts = build_ydl_opts("mp3", "320", "/tmp/test",
                               cookies_path=str(cookie_file))
        assert opts["cookiefile"] == str(cookie_file)

    def test_cookies_browser(self):
        opts = build_ydl_opts("mp3", "320", "/tmp/test", cookies_browser="chrome")
        assert "cookiesfrombrowser" in opts

    def test_no_cookies(self):
        opts = build_ydl_opts("mp3", "320", "/tmp/test")
        assert "cookiefile" not in opts
        assert "cookiesfrombrowser" not in opts

    def test_progress_hook_added(self):
        hook = MagicMock()
        opts = build_ydl_opts("mp3", "320", "/tmp/test", progress_hook=hook)
        assert hook in opts["progress_hooks"]

    def test_output_template_set(self):
        opts = build_ydl_opts("mp3", "320", "/tmp/mysong")
        assert opts["outtmpl"] == "/tmp/mysong"


class TestDownloadResult:
    def test_success_is_truthy(self):
        assert DownloadResult(success=True)

    def test_failure_is_falsy(self):
        assert not DownloadResult(success=False, error="oops")

    def test_has_error_message(self):
        r = DownloadResult(success=False, error="network error")
        assert r.error == "network error"


class TestApplyMetadata:
    """Testes de smoke para apply_metadata — não fazem I/O de áudio real."""

    def test_does_not_raise_on_missing_file(self, mock_track):
        """Se o arquivo não existe, apply_metadata deve falhar silenciosamente."""
        # apply_metadata loga o erro internamente — não deve propagar exceção
        apply_metadata("/nonexistent/path.mp3", mock_track)
