# 🦆 TouchGrass Duck (aw-touchgrass)

A lightweight, distraction-shaming system tray companion for Windows that monitors your computer usage via [ActivityWatch](https://activitywatch.net/) and has an angry duck scream and roast you when you've been on your computer or a specific app for too long.

---

## ✨ Features

- **ActivityWatch Telemetry**: Continuously tracks your active window usage and prolonged session times without collecting unnecessary data.
- **Screaming Duck Overlay**: A transparent, animated duck pops up over your taskbar quacking loudly and demanding that you go touch grass.
- **AI Roasts with Local Ollama**: Generates funny, toxic Gen-Z roasts using your local Ollama instance (default: `gemma2:2b`). If Ollama is offline or unavailable, it falls back to a clean default reminder.
- **System Tray Integration**:
  - Lives in your system tray with minimal resource usage.
  - **"Change Stuff"**: Instantly opens `config.json` in your default text editor so you can tweak thresholds, audio, and Ollama settings on the fly.
  - **"Quit"**: Cleanly shuts down the app and releases background process locks.
- **Immediate CLI Trigger**: Test or trigger the duck on-demand from the command line (e.g. `python main.py reddit 6 hours`).
- **Single Standalone `.exe`**: Portable, self-contained executable built with PyInstaller — no Python installation required for end users.

---

## 🚀 Quick Start

### Option A: Run the Standalone Executable

1. Make sure [ActivityWatch](https://activitywatch.net/) is running in the background.
2. (Optional) Run [Ollama](https://ollama.com/) locally (`ollama run gemma2:2b`) for dynamic AI roasts.
3. Run `dist/aw-touchgrass.exe`:
   - It will run in the background with an icon in your system tray.
   - Right-click the tray icon and select **"Change Stuff"** to adjust your preferences, or **"Quit"** to exit.

### Option B: Run from Source

#### Prerequisites
- Windows 10/11
- Python 3.10+
- ActivityWatch running locally (port 5600)

```powershell
# 1. Clone or navigate to the repository
cd d:\hacktober_fest\aw_touchgrass

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the background monitor
python.exe main.py
```

---

## ⚡ Command Line Usage (Immediate Triggers)

You can trigger the screaming duck immediately with custom apps and time criteria without waiting for ActivityWatch limits:

```powershell
# Positional arguments:
python.exe main.py reddit 6 hours
python.exe main.py reddit "6 hours"
python.exe main.py reddit 6h
python.exe main.py reddit 360m
python.exe main.py reddit 6          # Numbers <= 24 default to hours

# Using flags:
python.exe main.py --app chrome --hours 3
python.exe main.py --app discord --minutes 90

# Using the standalone executable:
.\dist\aw-touchgrass.exe reddit 6 hours
```

---

## ⚙️ Configuration (`config.json`)

Click **"Change Stuff"** in the system tray menu or open `config.json` directly. Changes take effect on the next polling cycle without restarting:

```json
{
  "ollama_endpoint": "http://localhost:11434/api/generate",
  "ollama_model": "gemma2:2b",
  "audio_file": "assets/quack.wav",
  "max_session_minutes": 120,
  "default_app_limit_minutes": 60,
  "app_limits": {
    "chrome": 45,
    "reddit": 30
  }
}
```

| Setting | Type | Description |
| :--- | :--- | :--- |
| `ollama_endpoint` | string | URL for the local Ollama HTTP generation endpoint. |
| `ollama_model` | string | Model name for generating roasts (e.g. `gemma2:2b`, `mistral`). |
| `audio_file` | string | Path to sound file played when the duck pops up (`.wav`). |
| `max_session_minutes` | number | Continuous screen time limit (in minutes) before triggering. |
| `default_app_limit_minutes` | number | Default threshold (in minutes) for any single application. |
| `app_limits` | object | Per-application thresholds in minutes (overrides default limit). |

---

## 🛠️ Building the Standalone `.exe`

To package TouchGrass Duck into a single `.exe` file:

```powershell
.\.venv\Scripts\pyinstaller.exe ratiobot.spec --noconfirm
```

The output will be created at:
```
dist/aw-touchgrass.exe
```

---

## 🧪 Running Tests

To run the full unit test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## 📂 Project Structure

```
aw_touchgrass/
├── assets/
│   └── quack.wav          # Quack sound effect
├── dist/
│   └── aw-touchgrass.exe  # Standalone compiled executable
├── tests/
│   └── test_core.py       # Unit test suite
├── config.json            # User configuration (thresholds, Ollama, audio)
├── gemma_api.py           # Ollama roast generation module
├── main.py                # Main polling loop & CLI argument parser
├── mascot.png             # Duck mascot sprite
├── overlay.py             # Tkinter screaming duck animated overlay
├── ratiobot.spec          # PyInstaller build specification
├── requirements.txt       # Project Python dependencies
├── tracker.py             # ActivityWatch telemetry client
├── tray.py                # System tray icon & "Change Stuff" handler
└── README.md              # Project documentation
```
