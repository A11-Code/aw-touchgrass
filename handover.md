# RatioBot / aw-touchgrass Handover

**Date:** 2026-10-08  
**Project:** `D:\hacktober_fest\aw_touchgrass`  
**Purpose:** Local desktop screen-time monitor that uses ActivityWatch telemetry, Ollama/Hugging Face models, a Tkinter intervention overlay, configurable limits, strikes, proof verification, SQLite history, and a system tray.

## Current Status

The application is implemented through the dashboard, system tray, warning history, proof verification, responsive upload UI, strike handling, and single-instance protection. The current automated suite passes:

```text
19 passed in 7.21s
```

The application modules also pass compilation and editor diagnostics. Live visual validation of every Tkinter/tray state and live Hugging Face inference still needs to be performed interactively.

## Implemented Work

### ActivityWatch tracking

Implemented in [tracker.py](./tracker.py):

- Queries the local ActivityWatch API.
- Supports `ACTIVITYWATCH_URL` overrides for testing.
- Finds the `aw-watcher-window` bucket.
- Aggregates active time by application.
- Returns the most-used application and active minutes.
- Lists recent applications for the dashboard.
- Calculates continuous active session time using `aw-watcher-afk`.
- Normalizes `.exe` suffixes for display and matching.

### LLM roast generation

Implemented in [gemma_api.py](./gemma_api.py):

- Uses local Ollama first.
- Uses the locally available `gemma2:2b` model tag.
- Falls back to Hugging Face chat completion when Ollama is unreachable.
- Loads `HF_TOKEN` through `python-dotenv`.
- Produces two short sentences.
- Requests playful, toxic-but-safe, gender-neutral language such as “bro” and “dude”.
- Explicitly prohibits gendered language, slurs, threats, and hate.

### Tkinter intervention overlay

Implemented in [overlay.py](./overlay.py):

- Frameless, always-on-top transparent window.
- Uses the transparent PNG mascot.
- Dynamically measures wrapped text and draws a padded rounded speech bubble.
- Uses a larger mascot rendering.
- Plays the quack sound once on the first slide-in frame.
- Uses `root.after()` for thread-safe slide-in and slide-out animation.
- Supports warning mode for strikes 0–2.
- Supports lockdown mode for strikes 3+.
- Displays a larger grass-proof button with a visible strike counter.
- Includes a top-right `×` close button while below lockdown.
- Closing through either normal dismissal or the cross charges one strike.
- Includes an in-memory guard to prevent one overlay from charging twice.
- Accepted proof resets strikes and resolves outstanding warning logs.

### Configuration and global rules

Implemented in [config.json](./config.json), [dashboard.py](./dashboard.py), and [main.py](./main.py):

- Configurable per-application daily limits.
- Configurable continuous-session limit.
- Configurable audio file.
- Persistent strike count.
- Dashboard dropdown defaults to **All applications**.
- Global application limit is used as a fallback.
- Specific application rules override the global rule.

Example:

```json
{
  "app_limits": {
    "All applications": 90,
    "Code": 120
  },
  "max_session_minutes": 240,
  "audio_file": "assets/quack.wav",
  "strikes": 0
}
```

### SQLite warning and proof history

Implemented in [database.py](./database.py):

- Creates `warning_logs`.
- Stores timestamp, trigger, active minutes, strike count, resolution state, and event type.
- Stores warning events.
- Stores accepted, rejected, and failed proof events.
- Returns recent history for the dashboard.
- Automatically adds the `event_type` column to older databases.
- Resolves outstanding warnings after accepted proof.

### System tray

Implemented in [tray.py](./tray.py):

- Uses `pystray`.
- Uses the mascot PNG as the tray icon.
- Provides:
  - Dashboard / Settings
  - Upload Grass Proof
  - Quit
- Runs the tray icon on a daemon thread.
- Tray quit stops the icon, signals the tracker, and calls `os._exit(0)` to terminate the complete application process.

### Dashboard

Implemented in [dashboard.py](./dashboard.py):

- Fluent-inspired dark UI using:
  - `#121212` main background
  - `#1e1e1e` cards
  - `#cecece` text
  - `#2ecc71` primary actions
  - Segoe UI fonts
- Settings and History & Logs tabs.
- Styled Treeview history table.
- Live strike counter.
- All-applications default selection.
- Per-app/global limit editing.
- Session limit editing.
- WAV picker.
- Grass-proof upload card.
- Indeterminate progress bar.
- Responsive status messages.
- Upload button disabled during analysis.
- Image verification runs on a daemon worker thread.
- Worker results return to Tkinter through `root.after()`.
- Closing the dashboard destroys only the dashboard and does not stop the tracker.

### Proof verification

Implemented in [vision_api.py](./vision_api.py):

- Preserves uploaded images on disk.
- Checks `DateTimeOriginal` EXIF metadata.
- Rejects photos older than three hours.
- Sends the image to the Hugging Face multimodal model.
- Requests a strict outdoors/nature/grass YES-or-NO decision.
- Flags accepted images without metadata as suspicious.
- Records proof audit events.
- Provides user feedback when called through the standalone upload flow.

### Main process lifecycle

Implemented in [main.py](./main.py):

- Reloads configuration each polling cycle.
- Uses `threading.Event.wait(60)` rather than a busy loop.
- Starts the tray.
- Records interventions.
- Prevents repeated triggers while an over-limit condition remains active.
- Uses a Windows-native `.ratiobot.lock` file to prevent duplicate monitor processes.
- Releases the lock on normal shutdown.
- Handles terminal `KeyboardInterrupt`.

## Dependencies

Declared in [requirement.txt](./requirement.txt):

- `requests`
- `huggingface_hub`
- `pillow`
- `python-dotenv`
- `pystray`
- `pyinstaller`

The project virtual environment is `.venv`. `pytest` is installed in the current environment for validation, but it is not currently listed in `requirement.txt`.

## Tests

Tests are in [tests/](./tests/):

- [test_tracker.py](./tests/test_tracker.py)
- [test_gemma_api.py](./tests/test_gemma_api.py)
- [test_overlay_asset.py](./tests/test_overlay_asset.py)
- [test_database.py](./tests/test_database.py)
- [test_vision_api.py](./tests/test_vision_api.py)
- [test_main.py](./tests/test_main.py)
- [test_instance_lock.py](./tests/test_instance_lock.py)

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Compile-check:

```powershell
.\.venv\Scripts\python.exe -m compileall -q *.py tests
```

## How to Run

1. Start ActivityWatch locally on port `5600`.
2. Confirm the assets exist:
   - `mascot.png`
   - `assets/quack.wav`
3. Activate or use the project virtual environment.
4. Start RatioBot:

```powershell
.\.venv\Scripts\python.exe main.py
```

5. Use the tray icon to open the dashboard or quit.

The dashboard can also be launched directly:

```powershell
.\.venv\Scripts\python.exe dashboard.py
```

## Known Bugs and Limitations

1. **Live GUI validation is incomplete.** Automated tests do not verify pixel-perfect layout, transparency behavior, Windows taskbar positioning, or every visual state.
2. **Live Hugging Face vision inference is not guaranteed.** It requires a valid `HF_TOKEN`, provider availability, network access, and a model/provider combination that supports the current multimodal request format.
3. **The dashboard and standalone proof flow are separate UI paths.** Dashboard uploads process the image in the dashboard worker and update dashboard feedback directly. Standalone tray/overlay uploads use `run_upload_flow()` and can open a separate success overlay.
4. **Proof verification uses a naive local timestamp comparison.** EXIF timestamps do not include timezone information, so camera timezone differences can cause an incorrect age decision.
5. **The proof image is preserved indefinitely.** This is intentional per the latest requirement, but there is no retention policy, storage quota, or cleanup UI.
6. **`os._exit(0)` is intentionally abrupt.** It guarantees zombie windows and worker threads are terminated, but it bypasses normal Python cleanup handlers and buffered output flushing.
7. **The tray action starts separate Python processes.** This avoids Tkinter cross-thread violations, but multiple dashboard windows can still be opened manually. The tracker itself is protected by the instance lock.
8. **The instance lock file remains in the repository directory.** The OS lock is released on process termination, but `.ratiobot.lock` is not deleted.
9. **The current database is a local file.** There is no backup, migration version table, corruption recovery, or concurrent-write coordination beyond SQLite's default behavior.
10. **The intervention overlay creates its own Tk root.** This works for the current process model, but a future unified UI architecture should use one Tk main loop and marshal overlay requests through it.
11. **A proof event can appear resolved immediately.** Proof audit events are informational and are stored as resolved, while warning events are resolved separately after accepted proof.
12. **The strike count is persisted by UI dismissal.** If the process is force-killed between interaction and config write, the strike update may not be durable.
13. **The project contains generated/local files.** `ratiobot.sqlite3` and `.ratiobot.lock` may appear in the working tree and should generally not be committed.

## Recommended Next Steps

1. Add `pytest` to a development dependency file or document the required test environment explicitly.
2. Add integration tests for:
   - Dashboard worker completion callbacks.
   - Accepted proof strike reset.
   - Rejected and failed proof history events.
   - Duplicate process launch behavior.
3. Perform a live Windows GUI pass for:
   - Dashboard resizing and Treeview readability.
   - Progress bar lifecycle.
   - Closing the dashboard during an active verification.
   - Overlay transparency and close-button visibility.
   - Tray quit behavior.
4. Add timezone-aware EXIF handling and a configurable proof-age policy.
5. Add an explicit proof-history retention/export policy now that files are preserved.
6. Add a database migration/version mechanism if the schema will continue evolving.
7. Add a startup health check and user-facing status when ActivityWatch is unavailable.
8. Consider replacing `os._exit(0)` with coordinated shutdown once all Tk and tray ownership is centralized.
9. Add packaging validation for the PyInstaller workflow, including bundled assets and config/database paths.
10. Update [runtime-validation-report.md](./runtime-validation-report.md) after the next live GUI and model validation pass.

## Handover Checklist

- [x] ActivityWatch telemetry integration
- [x] Ollama and Hugging Face roast generation
- [x] Gender-neutral roast prompting
- [x] Dynamic intervention overlay
- [x] Strike system and lockdown state
- [x] Cross dismissal and strike charging
- [x] Global all-applications rule
- [x] SQLite warning and proof history
- [x] System tray integration
- [x] EXIF and vision verification
- [x] Proof image preservation & retention cleanup policy
- [x] Database backup functionality
- [x] Dashboard strike display
- [x] Responsive proof upload
- [x] Progress/status feedback
- [x] Single-instance tracker lock
- [x] Automated regression tests (19 passed)
- [x] PyInstaller packaged-app build (`ratiobot.spec` executable bundling)
- [ ] Live interactive GUI user acceptance pass
- [ ] Live online Hugging Face vision inference with valid API token

