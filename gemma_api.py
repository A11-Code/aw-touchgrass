"""Roast generation using local Ollama with a Hugging Face fallback."""

from __future__ import annotations

import logging
import os
import re

import requests
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

LOGGER = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
# Ollama currently exposes Gemma 2 through its 2B local tag.
OLLAMA_MODEL = "gemma2:2b"
HUGGINGFACE_MODEL = "google/gemma-2-9b-it"
REQUEST_TIMEOUT_SECONDS = 30

load_dotenv()


def _prompt(app_name: str, minutes: float) -> str:
    """Build the shared instruction used by both inference providers."""
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


def _generate_with_ollama(prompt: str) -> str:
    """Generate a roast from the local Ollama HTTP API."""
    response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("response") if isinstance(payload, dict) else None
    if not isinstance(result, str):
        raise RuntimeError("Ollama returned no response text.")
    return result


def _generate_with_huggingface(prompt: str) -> str:
    """Generate a roast from Hugging Face Serverless Inference."""
    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "Ollama is unavailable and HF_TOKEN is not configured for fallback."
        )

    client = InferenceClient(token=token, model=HUGGINGFACE_MODEL)
    response = client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.9,
    )
    content = response.choices[0].message.content
    if not isinstance(content, str):
        raise RuntimeError("Hugging Face returned no response text.")
    return content


def generate_roast(app_name: str, minutes: float) -> str:
    """Return a two-sentence roast, preferring local inference."""
    if not app_name.strip():
        raise ValueError("app_name must not be empty")
    if minutes < 0:
        raise ValueError("minutes must not be negative")

    prompt = _prompt(app_name.strip(), minutes)
    try:
        return _two_sentences(_generate_with_ollama(prompt))
    except (requests.ConnectionError, requests.Timeout) as exc:
        LOGGER.info("Ollama unavailable; using Hugging Face fallback: %s", exc)
        return _two_sentences(_generate_with_huggingface(prompt))
