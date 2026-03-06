#!/usr/bin/env python3
import sys
import signal
import logging

# Configura logging global
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s:%(lineno)d] %(message)s",
)

# Handle Ctrl+C gracefully
signal.signal(signal.SIGINT, signal.SIG_DFL)

from src.ui.app import SpotifyDownloaderApp

if __name__ == "__main__":
    app = SpotifyDownloaderApp()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
