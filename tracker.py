"""ActivityWatch telemetry helpers for RatioBot."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)

ACTIVITYWATCH_URL = os.getenv(
    "ACTIVITYWATCH_URL", "http://localhost:5600/api/0"
).rstrip("/")
REQUEST_TIMEOUT_SECONDS = 10


def _parse_timestamp(value: Any) -> datetime | None:
    """Convert an ActivityWatch timestamp into an aware UTC datetime."""
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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


def _get_events(bucket_id: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    """Fetch events for a bucket and return only object-shaped events."""
    response = requests.get(
        f"{ACTIVITYWATCH_URL}/buckets/{bucket_id}/events",
        params={"start": start.isoformat(), "end": end.isoformat()},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return [event for event in payload if isinstance(event, dict)] if isinstance(payload, list) else []


def get_recent_apps() -> list[str]:
    """Return unique application names observed by the window watcher in 24 hours."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=24)
    try:
        buckets_response = requests.get(
            f"{ACTIVITYWATCH_URL}/buckets", timeout=REQUEST_TIMEOUT_SECONDS
        )
        buckets_response.raise_for_status()
        bucket_id = _find_window_bucket(buckets_response.json())
        if bucket_id is None:
            return []
        events = _get_events(bucket_id, start, end)
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Unable to read recent applications: %s", exc)
        return []

    apps = {
        app_name.removesuffix(".exe")
        for event in events
        if isinstance(event.get("data"), dict)
        for app_name in [_application_name(event["data"])]
        if app_name
    }
    return sorted(apps, key=str.casefold)


def get_continuous_session() -> float:
    """Return active minutes since the last AFK gap longer than 15 minutes."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=24)
    try:
        buckets_response = requests.get(
            f"{ACTIVITYWATCH_URL}/buckets", timeout=REQUEST_TIMEOUT_SECONDS
        )
        buckets_response.raise_for_status()
        bucket_id = _find_bucket(buckets_response.json(), "aw-watcher-afk")
        if bucket_id is None:
            return 0.0
        events = _get_events(bucket_id, start, end)
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Unable to read AFK session telemetry: %s", exc)
        return 0.0

    events_with_times = []
    for event in events:
        timestamp = _parse_timestamp(event.get("timestamp"))
        duration = event.get("duration")
        if timestamp and isinstance(duration, (int, float)) and duration > 0:
            events_with_times.append((timestamp, float(duration), event.get("data")))
    events_with_times.sort(key=lambda item: item[0])

    session_seconds = 0.0
    for _timestamp, duration, data in events_with_times:
        status = data.get("status") if isinstance(data, dict) else None
        if status == "afk" and duration > 15 * 60:
            session_seconds = 0.0
        elif status in (None, "not-afk"):
            session_seconds += duration
    return session_seconds / 60


def get_top_app(hours: float = 2) -> tuple[str | None, float]:
    """Return the most-used application and its active minutes.

    The function intentionally returns ``(None, 0.0)`` when ActivityWatch is
    unavailable or has no usable events, allowing the polling loop to retry
    without crashing the desktop application.
    """
    if hours <= 0:
        raise ValueError("hours must be greater than zero")

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)

    try:
        buckets_response = requests.get(
            f"{ACTIVITYWATCH_URL}/buckets", timeout=REQUEST_TIMEOUT_SECONDS
        )
        buckets_response.raise_for_status()
        bucket_id = _find_window_bucket(buckets_response.json())
        if bucket_id is None:
            LOGGER.warning("ActivityWatch window bucket was not found.")
            return None, 0.0

        events_response = requests.get(
            f"{ACTIVITYWATCH_URL}/buckets/{bucket_id}/events",
            params={"start": start.isoformat(), "end": end.isoformat()},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        events_response.raise_for_status()
        events = events_response.json()
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Unable to read ActivityWatch telemetry: %s", exc)
        return None, 0.0

    if not isinstance(events, list):
        LOGGER.warning("ActivityWatch returned an unexpected events payload.")
        return None, 0.0

    durations: defaultdict[str, float] = defaultdict(float)
    for event in events:
        if not isinstance(event, dict):
            continue

        timestamp = _parse_timestamp(event.get("timestamp"))
        duration = event.get("duration")
        data = event.get("data")
        if timestamp is None or not isinstance(duration, (int, float)):
            continue
        if not start <= timestamp <= end or duration <= 0 or not isinstance(data, dict):
            continue

        app_name = _application_name(data)
        if app_name:
            durations[app_name] += float(duration)

    if not durations:
        return None, 0.0

    app_name, seconds = max(durations.items(), key=lambda item: item[1])
    return app_name, seconds / 60
