"""System tray icon for the duck screamer background process."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading

from PIL import Image
import pystray
from pystray import MenuItem

LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent

DEFAULT_CONFIG = {
    "ollama_endpoint": "http://localhost:11434/api/generate",
    "ollama_model": "gemma2:2b",
    "audio_file": "assets/quack.wav",
    "max_session_minutes": 120,
    "default_app_limit_minutes": 60,
    "app_limits": {},
}


def get_config_path() -> Path:
    """Return persistent config path, located next to executable when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config.json"
    return BASE_DIR / "config.json"


def ensure_config_exists() -> Path:
    """Ensure the config file exists on disk, populating defaults if missing."""
    config_path = get_config_path()
    if not config_path.exists():
        try:
            bundled_config = BASE_DIR / "config.json"
            if bundled_config.exists() and bundled_config.resolve() != config_path.resolve():
                import shutil
                shutil.copy2(bundled_config, config_path)
                return config_path
        except Exception:
            pass
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception:
            LOGGER.exception("Failed to create default config at %s", config_path)
    return config_path


def open_config_file(_icon: pystray.Icon | None = None, _item: MenuItem | None = None) -> None:
    """Open config.json in the system's default editor or notepad."""
    config_path = ensure_config_exists()

    def _open() -> None:
        try:
            if os.name == "nt":
                try:
                    os.startfile(str(config_path))
                except OSError:
                    subprocess.Popen(["notepad.exe", str(config_path)])
            else:
                subprocess.Popen(["xdg-open", str(config_path)])
        except Exception:
            LOGGER.exception("Failed to open config file: %s", config_path)

    threading.Thread(target=_open, name="open-config-thread", daemon=True).start()


def set_audio_file(file_path: str) -> None:
    """Update the audio_file setting in config.json."""
    config_path = ensure_config_exists()
    try:
        config = {}
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)

        path_obj = Path(file_path)
        try:
            rel = path_obj.relative_to(BASE_DIR)
            config["audio_file"] = str(rel).replace("\\", "/")
        except ValueError:
            config["audio_file"] = str(path_obj.resolve())

        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        LOGGER.info("Updated audio file to: %s", config["audio_file"])
    except Exception:
        LOGGER.exception("Failed to write updated audio file to config.json")


def start_tray(stop_event: threading.Event) -> threading.Thread:
    """Start the tray icon on a daemon thread and return that thread."""
    icon_path = BASE_DIR / "mascot.png"
    image = Image.open(icon_path).convert("RGBA")

    def on_change_stuff(_icon: pystray.Icon, _item: MenuItem) -> None:
        open_config_file()

    def quit_application(icon: pystray.Icon, _item: MenuItem) -> None:
        stop_event.set()
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        MenuItem("Change Stuff", on_change_stuff),
        MenuItem("Quit", quit_application),
    )
    icon = pystray.Icon("aw-touchgrass", image, "TouchGrass Duck", menu)
    thread = threading.Thread(target=icon.run, name="touchgrass-tray", daemon=True)
    thread.start()
    return thread
