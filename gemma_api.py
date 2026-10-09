"""Roast generation using local Ollama (Gemma 2)."""

from __future__ import annotations

import logging
import re

import requests

LOGGER = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma2:2b"
REQUEST_TIMEOUT_SECONDS = 10.0


def _prompt(app_name: str, minutes: float) -> str:
    """Build the instruction sent to Ollama."""
    return (
        "Write exactly two short sentences as a toxic but playful, "
        "chronically-online Gen-Z roast. Use gender-neutral casual terms such as "
        "'bro' or 'dude'; do not use gendered terms, slurs, threats, or hate. "
        f"The user has spent {minutes:.0f} active minutes in {app_name}. "
        "Tell them to touch real grass."
    )


def _two_sentences(text: str) -> str:
    """Keep model output concise while preserving its generated wording."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        raise RuntimeError("The language model returned an empty roast.")

    sentences = re.findall(r"[^.!?]+[.!?]", cleaned)
    if len(sentences) >= 2:
        return " ".join(sentence.strip() for sentence in sentences[:2])
    first = cleaned.rstrip(".!?") + "."
    return f"{first} Now go touch real grass."


def generate_roast(
    app_name: str,
    minutes: float,
    ollama_url: str | None = None,
    ollama_model: str | None = None,
) -> str:
    """Return a two-sentence roast from local Ollama."""
    if not app_name.strip():
        raise ValueError("app_name must not be empty")
    if minutes < 0:
        raise ValueError("minutes must not be negative")

    clean_app = app_name.removesuffix(".exe").strip() or "your screen"
    prompt = _prompt(clean_app, minutes)
    url = ollama_url or OLLAMA_URL
    model = ollama_model or OLLAMA_MODEL

    try:
        response = requests.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        result = payload.get("response") if isinstance(payload, dict) else None
        if not isinstance(result, str):
            raise RuntimeError("Ollama returned no response text.")
        return _two_sentences(result)
    except Exception as exc:
        LOGGER.warning("Ollama unavailable (%s); using generic message.", exc)
        return f"You've been on {clean_app} for {minutes:.0f} minutes. Go touch grass!"

