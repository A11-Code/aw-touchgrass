# RatioBot Runtime Validation Report

**Generated**: 2026-10-08  
**Target**: `D:\hacktober_fest\aw_touchgrass`

## Summary

| Step | Status | Exit Code | Details |
|------|--------|-----------|---------|
| Static validation | PASS | 0 | No syntax errors or Pylance diagnostics in the application modules. |
| Unit tests | PASS | 0 | 9 tests passed across telemetry, model fallback, mascot loading, SQLite logging, and proof verification. |
| Feature syntax/import validation | PASS | 0 | Database, tray, dashboard, vision, overlay, and main modules compile successfully. |
| ActivityWatch smoke check | PASS | 0 | Live tracker returned `chrome.exe` with approximately 48 active minutes. |
| Ollama availability | PASS | 0 | Ollama `/api/tags` returned HTTP 200 and exposes `gemma2:2b`. |
| Ollama generation | UNVERIFIED | 1 | Real generation exceeded the 30-second timeout. |
| Hugging Face live fallback | UNVERIFIED | 1 | The fallback path is unit-tested; live access was not completed after Ollama timed out. |
| Tkinter visual startup | UNVERIFIED | n/a | Requires an interactive desktop window session. |

## Overall

**NEEDS_SIGNOFF** — application logic and focused tests pass, but live model generation, tray behavior, and visual Tkinter behavior still require an interactive run.

## Test Evidence

Command:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Result:

```text
9 passed in 0.66s
OK
```

Covered behaviors:

- ActivityWatch event aggregation and missing-bucket handling.
- Ollama-first selection.
- Timeout fallback to Hugging Face.
- Hugging Face chat-completion response parsing.
- PNG mascot loading and resizing.
- SQLite warning insertion, retrieval, and resolution.
- EXIF age rejection, metadata-free suspicion detection, and uploaded-file cleanup.

## New Feature Coverage

- `database.py` creates `warning_logs`, records interventions, returns recent history, and resolves open warnings.
- `tray.py` starts a daemon `pystray` icon with dashboard, proof-upload, and quit actions.
- `vision_api.py` enforces the three-hour EXIF rule, calls the Hugging Face vision model, flags metadata-free positive proofs, and deletes uploads in a `finally` block.
- `dashboard.py` exposes settings, upload, and the ten most recent warning logs.
- `main.py` initializes logging, records interventions, reloads limits each cycle, and uses `Event.wait(60)` for efficient shutdown-aware polling.
- `overlay.py` resets strikes and resolves warning logs after accepted proof.

## Environment

```text
Docker: UNAVAILABLE (daemon not responding)
Node.js: AVAILABLE (v22.23.2)
Playwright: AVAILABLE (v1.64.0)
ActivityWatch: AVAILABLE (HTTP redirect followed by requests; live tracker returned data)
Ollama: AVAILABLE (HTTP 200 from /api/tags)
Ollama model: gemma2:2b
```

## Changes Made During Validation

- Updated the overlay to load the added root-level `mascot.jpg`.
- Updated the Ollama model tag to the locally installed `gemma2:2b`.
- Updated Hugging Face fallback to use `chat_completion`, which matches the installed provider support for `google/gemma-2-9b-it`.
- Added focused tests under `tests/`.
