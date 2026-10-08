"""RatioBot entry point: poll ActivityWatch and show interventions."""

from __future__ import annotations

import json
import logging
import msvcrt
from pathlib import Path
import sys
import time
from tkinter import TclError

import database
from gemma_api import generate_roast
from overlay import RagebaitClippy
from tray import start_tray
from tracker import get_continuous_session, get_top_app

LOGGER = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60
INTERVENTION_THRESHOLD_MINUTES = 120
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
ALL_APPLICATIONS = "All applications"
INSTANCE_LOCK_PATH = Path(__file__).resolve().parent / ".ratiobot.lock"


def _acquire_instance_lock():
    """Allow only one Windows RatioBot monitor process at a time."""
    lock_file = INSTANCE_LOCK_PATH.open("a+")
    lock_file.seek(0)
    lock_file.write("1")
    lock_file.flush()
    lock_file.seek(0)
    try:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock_file.close()
        LOGGER.warning("RatioBot is already running; ignoring duplicate launch.")
        return None
    return lock_file


def _release_instance_lock(lock_file) -> None:
    """Release the process lock during a clean shutdown."""
    try:
        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        lock_file.close()


def _load_config() -> dict:
    """Load persisted settings for the current polling cycle."""
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
        raise ValueError("config.json must contain a JSON object")
    return config


def _matching_limit(app_name: str, app_limits: dict) -> float | None:
    """Match a specific app, falling back to the global application rule."""
    normalized = app_name.removesuffix(".exe").casefold()
    global_limit = None
    for configured_name, limit in app_limits.items():
        if configured_name.casefold() == ALL_APPLICATIONS.casefold():
            global_limit = float(limit)
        elif configured_name.casefold() == normalized:
            return float(limit)
    return global_limit


def run(stop_event=None) -> None:
    """Poll forever and trigger once for each threshold crossing."""
    instance_lock = _acquire_instance_lock()
    if instance_lock is None:
        return
    if stop_event is None:
        import threading

        stop_event = threading.Event()
    try:
        database.initialize_database()
        start_tray(stop_event)
        threshold_triggered = False

        while not stop_event.is_set():
            try:
                config = _load_config()
                app_name, active_minutes = get_top_app(hours=24)
                app_limit = (
                    _matching_limit(app_name, config.get("app_limits", {}))
                    if app_name
                    else None
                )
                session_minutes = get_continuous_session()
                session_limit = float(config.get("max_session_minutes", 240))
                app_triggered = (
                    app_name is not None
                    and app_limit is not None
                    and active_minutes > app_limit
                )
                session_triggered = session_minutes > session_limit
                over_threshold = app_triggered or session_triggered

                if not over_threshold:
                    threshold_triggered = False
                elif not threshold_triggered:
                    trigger_name = app_name if app_triggered else "continuous session"
                    trigger_minutes = active_minutes if app_triggered else session_minutes
                    LOGGER.info(
                        "%s has been active for %.1f minutes; showing intervention.",
                        trigger_name,
                        trigger_minutes,
                    )
                    roast = generate_roast(
                        trigger_name or "your screen",
                        trigger_minutes,
                    )
                    before_strikes = int(config.get("strikes", 0))
                    database.insert_log(
                        trigger_name or "unknown",
                        trigger_minutes,
                        before_strikes,
                    )
                    RagebaitClippy(
                        roast,
                        strikes=before_strikes,
                        audio_file=config.get("audio_file", "assets/quack.wav"),
                    ).show()
                    threshold_triggered = True
            except (RuntimeError, OSError, TclError, ValueError):
                LOGGER.exception("RatioBot poll failed; it will retry on the next cycle.")

            stop_event.wait(POLL_INTERVAL_SECONDS)
    finally:
        _release_instance_lock(instance_lock)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        run()
    except KeyboardInterrupt:
        LOGGER.info("RatioBot stopped from the terminal.")
        sys.exit(0)
