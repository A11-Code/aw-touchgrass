"""System tray integration for the RatioBot background process."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import threading

from PIL import Image
import pystray
from pystray import MenuItem

BASE_DIR = Path(__file__).resolve().parent


def _launch(module: str) -> None:
    subprocess.Popen(
        [sys.executable, str(BASE_DIR / module)],
        cwd=BASE_DIR,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def start_tray(stop_event: threading.Event) -> threading.Thread:
    """Start the tray icon on a daemon thread and return that thread."""
    icon_path = BASE_DIR / "mascot.png"
    image = Image.open(icon_path).convert("RGBA")

    def quit_application(icon: pystray.Icon, _item: MenuItem) -> None:
        stop_event.set()
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        MenuItem("Dashboard / Settings", lambda _icon, _item: _launch("dashboard.py")),
        MenuItem("Upload Grass Proof", lambda _icon, _item: _launch("vision_api.py")),
        MenuItem("Quit", quit_application),
    )
    icon = pystray.Icon("ratiobot", image, "RatioBot", menu)
    thread = threading.Thread(target=icon.run, name="ratiobot-tray", daemon=True)
    thread.start()
    return thread
