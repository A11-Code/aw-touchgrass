"""ActivityWatch telemetry helpers for RatioBot using aw-client and IST timezone."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

from aw_client import ActivityWatchClient

LOGGER = logging.getLogger(__name__)

ACTIVITYWATCH_URL = os.getenv(
    "ACTIVITYWATCH_URL", "http://localhost:5600/api/0"
).rstrip("/")
REQUEST_TIMEOUT_SECONDS = 3
IST = timezone(timedelta(hours=5, minutes=30))

_CACHE_TTL_SECONDS = 5.0
_cache_time: float = 0.0
_cache_data: tuple[str | None, float, float, list[str], bool] | None = None


def get_client() -> ActivityWatchClient:
    """Return an ActivityWatchClient instance configured from ACTIVITYWATCH_URL."""
    parsed = urlparse(ACTIVITYWATCH_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5600
    return ActivityWatchClient(client_name="aw-touchgrass", host=host, port=port)


def _parse_timestamp(value: Any) -> datetime | None:
    """Convert an ActivityWatch timestamp into an aware IST datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).astimezone(IST)
        return value.astimezone(IST)
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc).astimezone(IST)
    return parsed.astimezone(IST)


def _bucket_id(bucket: dict[str, Any]) -> str | None:
    """Return a bucket identifier from either common API response shapes."""
    for key in ("id", "bucket_id", "bucketId"):
        value = bucket.get(key)
        if isinstance(value, str):
            return value
    return None


def _is_window_bucket(bucket_id: str, metadata: dict[str, Any]) -> bool:
    """Identify the desktop-window watcher bucket without relying on one schema."""
    searchable = " ".join(
        str(metadata.get(key, "")) for key in ("id", "name", "client", "type")
    )
    return "aw-watcher-window" in f"{bucket_id} {searchable}".lower()


def _application_name(event_data: dict[str, Any]) -> str | None:
    """Extract an application name from ActivityWatch's event data."""
    for key in ("app", "application", "name"):
        value = event_data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _find_window_bucket(payload: Any) -> str | None:
    """Find the window watcher bucket in dict- or list-shaped API responses."""
    if isinstance(payload, dict):
        candidates = [
            {"id": key, **value}
            for key, value in payload.items()
            if isinstance(value, dict)
        ]
    elif isinstance(payload, list):
        candidates = [item for item in payload if isinstance(item, dict)]
    else:
        candidates = []

    for candidate in candidates:
        bucket_id = _bucket_id(candidate)
        if bucket_id and _is_window_bucket(bucket_id, candidate):
            return bucket_id
    return None


def _find_bucket(payload: Any, marker: str) -> str | None:
    """Find a bucket whose identifier or metadata contains ``marker``."""
    if isinstance(payload, dict):
        candidates = [
            {"id": key, **value}
            for key, value in payload.items()
            if isinstance(value, dict)
        ]
    elif isinstance(payload, list):
        candidates = [item for item in payload if isinstance(item, dict)]
    else:
        candidates = []

    marker = marker.lower()
    for candidate in candidates:
        bucket_id = _bucket_id(candidate)
        if bucket_id and marker in f"{bucket_id} {candidate}".lower():
            return bucket_id
    return None


def _get_event_details(event: Any) -> tuple[datetime | None, float, dict[str, Any]]:
    """Extract (timestamp, duration_seconds, data_dict) from an aw-client Event or dict."""
    if isinstance(event, dict):
        ts_val = getattr(event, "timestamp", None)
        if ts_val is None:
            ts_val = event.get("timestamp")
        ts = _parse_timestamp(ts_val)

        dur_val = getattr(event, "duration", None)
        if isinstance(dur_val, timedelta):
            dur_sec = dur_val.total_seconds()
        elif isinstance(dur_val, (int, float)):
            dur_sec = float(dur_val)
        else:
            raw_dur = event.get("duration")
            dur_sec = float(raw_dur) if isinstance(raw_dur, (int, float)) else 0.0

        data_val = getattr(event, "data", None)
        if not isinstance(data_val, dict):
            raw_data = event.get("data")
            data_val = raw_data if isinstance(raw_data, dict) else {}

        return ts, dur_sec, data_val
    return None, 0.0, {}


def clear_cache() -> None:
    """Clear the in-memory telemetry cache."""
    global _cache_time, _cache_data
    _cache_time = 0.0
    _cache_data = None


def get_telemetry_summary(
    hours: float = 24.0, use_cache: bool = True
) -> tuple[str | None, float, float, list[str], bool]:
    """Batch query ActivityWatch telemetry once and return (top_app, top_minutes, session_minutes, recent_apps, aw_connected)."""
    global _cache_time, _cache_data

    now_mono = time.monotonic()
    if use_cache and _cache_data is not None and (now_mono - _cache_time) < _CACHE_TTL_SECONDS:
        return _cache_data

    end = datetime.now(IST)
    start = end - timedelta(hours=hours)

    top_app_name: str | None = None
    top_app_minutes: float = 0.0
    session_minutes: float = 0.0
    recent_apps: list[str] = []
    aw_connected: bool = False

    try:
        client = get_client()
        buckets = client.get_buckets()
        aw_connected = True

        window_bucket_id = _find_window_bucket(buckets)
        afk_bucket_id = _find_bucket(buckets, "aw-watcher-afk")

        # 1. Fetch Window Events
        window_events = []
        if window_bucket_id is not None:
            window_events = client.get_events(window_bucket_id, start=start, end=end)

        # 2. Fetch AFK Events
        afk_events = []
        if afk_bucket_id is not None:
            afk_events = client.get_events(afk_bucket_id, start=start, end=end)

        # Process Window Events -> Top App & Recent Apps
        if isinstance(window_events, list):
            durations: defaultdict[str, float] = defaultdict(float)
            app_set = set()
            for event in window_events:
                timestamp, duration, data = _get_event_details(event)
                if timestamp is None or duration <= 0:
                    continue
                if start <= timestamp <= end:
                    app_name = _application_name(data)
                    if app_name:
                        durations[app_name] += duration
                        app_set.add(app_name.removesuffix(".exe"))
            recent_apps = sorted(app_set, key=str.casefold)

            if durations:
                best_name, best_seconds = max(durations.items(), key=lambda item: item[1])
                top_app_name = best_name
                top_app_minutes = best_seconds / 60.0

        # Process AFK Events -> Continuous Session
        if isinstance(afk_events, list):
            events_with_times = []
            for event in afk_events:
                timestamp, duration, data = _get_event_details(event)
                if timestamp and duration > 0:
                    events_with_times.append((timestamp, duration, data))
            events_with_times.sort(key=lambda item: item[0])

            session_seconds = 0.0
            for _timestamp, duration, data in events_with_times:
                status = data.get("status") if isinstance(data, dict) else None
                if status == "afk" and duration > 15 * 60:
                    session_seconds = 0.0
                elif status in (None, "not-afk"):
                    session_seconds += duration
            session_minutes = session_seconds / 60.0

    except Exception as exc:
        LOGGER.warning("Unable to read ActivityWatch telemetry: %s", exc)
        aw_connected = False

    result = (top_app_name, top_app_minutes, session_minutes, recent_apps, aw_connected)
    if use_cache:
        _cache_data = result
        _cache_time = now_mono
    return result


def get_recent_apps() -> list[str]:
    """Return unique application names observed by the window watcher in 24 hours."""
    _, _, _, recent_apps, _ = get_telemetry_summary(hours=24.0, use_cache=True)
    return recent_apps


def get_continuous_session() -> float:
    """Return active minutes since the last AFK gap longer than 15 minutes."""
    _, _, session_minutes, _, _ = get_telemetry_summary(hours=24.0, use_cache=True)
    return session_minutes


def get_top_app(hours: float = 2) -> tuple[str | None, float]:
    """Return the most-used application and its active minutes."""
    if hours <= 0:
        raise ValueError("hours must be greater than zero")
    top_app_name, top_app_minutes, _, _, _ = get_telemetry_summary(hours=hours, use_cache=False)
    return top_app_name, top_app_minutes


def is_activitywatch_connected() -> bool:
    """Check if the ActivityWatch server is reachable."""
    _, _, _, _, aw_connected = get_telemetry_summary(hours=24.0, use_cache=True)
    return aw_connected




