"""aw-touchgrass: poll ActivityWatch and show a duck when you need to touch grass."""

from __future__ import annotations

import argparse
import json
import logging
import msvcrt
from pathlib import Path
import re
import sys
import threading
import time
from tkinter import TclError

from gemma_api import generate_roast
from overlay import DuckOverlay
from tray import ensure_config_exists, get_config_path, start_tray
from tracker import get_continuous_session, get_top_app

LOGGER = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60
ALL_APPLICATIONS = "All applications"
INSTANCE_LOCK_PATH = Path(__file__).resolve().parent / ".ratiobot.lock"


def _acquire_instance_lock():
    """Allow only one monitor process at a time (Windows)."""
    lock_file = INSTANCE_LOCK_PATH.open("a+")
    lock_file.seek(0)
    lock_file.write("1")
    lock_file.flush()
    lock_file.seek(0)
    try:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock_file.close()
        msg = "aw-touchgrass is already running in the background (check your system tray)."
        LOGGER.warning(msg)
        print(msg)
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
    config_path = ensure_config_exists()
    try:
        with config_path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
        if isinstance(config, dict):
            return config
    except Exception as exc:
        LOGGER.warning("Could not read config.json (%s); using defaults.", exc)
    return {
        "ollama_endpoint": "http://localhost:11434/api/generate",
        "ollama_model": "gemma2:2b",
        "audio_file": "assets/quack.wav",
        "max_session_minutes": 120,
        "default_app_limit_minutes": 60,
        "app_limits": {},
    }


def _matching_limit(
    app_name: str,
    app_limits: dict,
    default_limit: float | None = None,
) -> float | None:
    """Match a specific app limit, falling back to the global rule or default_limit."""
    normalized = app_name.removesuffix(".exe").casefold()
    global_limit = float(default_limit) if default_limit is not None else None
    for configured_name, limit in app_limits.items():
        if configured_name.casefold() == ALL_APPLICATIONS.casefold():
            global_limit = float(limit)
        elif configured_name.casefold() == normalized:
            return float(limit)
    return global_limit


def run(stop_event=None) -> None:
    """Poll ActivityWatch and show the duck overlay when thresholds are crossed."""
    instance_lock = _acquire_instance_lock()
    if instance_lock is None:
        return
    if stop_event is None:
        stop_event = threading.Event()
    try:
        start_tray(stop_event)
        threshold_triggered = False

        while not stop_event.is_set():
            try:
                config = _load_config()
                app_name, active_minutes = get_top_app(hours=24)
                app_limit = (
                    _matching_limit(
                        app_name,
                        config.get("app_limits", {}),
                        default_limit=config.get("default_app_limit_minutes"),
                    )
                    if app_name
                    else None
                )
                session_minutes = get_continuous_session()
                session_limit = float(config.get("max_session_minutes", 120))

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
                        "%s has been active for %.1f minutes; showing duck.",
                        trigger_name,
                        trigger_minutes,
                    )
                    roast = generate_roast(
                        trigger_name or "your screen",
                        trigger_minutes,
                        ollama_url=config.get("ollama_endpoint"),
                        ollama_model=config.get("ollama_model"),
                    )
                    DuckOverlay(
                        roast,
                        audio_file=config.get("audio_file", "assets/quack.wav"),
                    ).show()
                    threshold_triggered = True
            except (RuntimeError, OSError, TclError, ValueError):
                LOGGER.exception("Poll cycle failed; will retry next cycle.")

            stop_event.wait(POLL_INTERVAL_SECONDS)
    finally:
        _release_instance_lock(instance_lock)


def parse_duration_to_minutes(text: str) -> float:
    """Parse duration string like '6 hours', '1h 30m', '45m', '6' into minutes."""
    cleaned = text.strip().lower()
    total_minutes = 0.0
    matched = False

    days_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:d|day|days)\b", cleaned)
    if days_match:
        total_minutes += float(days_match.group(1)) * 1440.0
        matched = True

    hours_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\b", cleaned)
    if hours_match:
        total_minutes += float(hours_match.group(1)) * 60.0
        matched = True

    mins_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m|min|mins|minute|minutes)\b", cleaned)
    if mins_match:
        total_minutes += float(mins_match.group(1))
        matched = True

    secs_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds)\b", cleaned)
    if secs_match:
        total_minutes += float(secs_match.group(1)) / 60.0
        matched = True

    if matched:
        return total_minutes

    try:
        val = float(cleaned)
        return val * 60.0 if val <= 24 else val
    except ValueError:
        pass

    raise ValueError(f"Could not parse duration from '{text}'")


def trigger_immediately(app_name: str, minutes: float) -> None:
    """Immediately generate a roast and display the duck overlay."""
    LOGGER.info("Immediate duck trigger for '%s' (%.1f minutes)", app_name, minutes)
    config = _load_config()
    roast = generate_roast(
        app_name,
        minutes,
        ollama_url=config.get("ollama_endpoint"),
        ollama_model=config.get("ollama_model"),
    )
    DuckOverlay(
        roast,
        audio_file=config.get("audio_file", "assets/quack.wav"),
    ).show()


def main(argv: list[str] | None = None) -> None:
    """Main CLI entrypoint with argument parsing."""
    parser = argparse.ArgumentParser(
        description="TouchGrass Duck: monitors screen time and reminds you to touch grass.",
    )
    parser.add_argument(
        "app",
        nargs="?",
        default=None,
        help="Target application name (e.g. reddit, chrome, league).",
    )
    parser.add_argument(
        "duration",
        nargs="*",
        default=[],
        help="Duration spent (e.g. '6 hours', '6h', '360 mins', '6').",
    )
    parser.add_argument(
        "--app",
        dest="app_flag",
        help="Target application name.",
    )
    parser.add_argument(
        "--hours",
        type=float,
        help="Duration in hours.",
    )
    parser.add_argument(
        "--minutes",
        type=float,
        help="Duration in minutes.",
    )

    args = parser.parse_args(argv)

    app_name = args.app_flag or args.app
    minutes = None

    if args.minutes is not None:
        minutes = args.minutes
    elif args.hours is not None:
        minutes = args.hours * 60.0
    elif args.duration:
        duration_text = " ".join(args.duration)
        try:
            minutes = parse_duration_to_minutes(duration_text)
        except ValueError:
            LOGGER.error("Invalid duration format: '%s'", duration_text)
            print(f"Error: Could not parse duration '{duration_text}'. Try e.g. '6 hours', '6h', '360m'.")
            sys.exit(1)

    if app_name:
        if minutes is None:
            minutes = 120.0
        trigger_immediately(app_name, minutes)
        return

    run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        main()
    except KeyboardInterrupt:
        LOGGER.info("aw-touchgrass stopped from the terminal.")
        sys.exit(0)
