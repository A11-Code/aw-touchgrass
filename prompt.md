# Project Overview
Build `aw-touchgrass`, a Python-based desktop application that monitors a user's screen time via the local ActivityWatch REST API and generates toxic, meme-based "touch grass" interventions. It must first attempt to use a local Ollama instance for text generation and fall back to the Hugging Face Serverless Inference API if Ollama is unavailable.

## Tech Stack & Rules
* **Language:** Python 3
* **Environment Variables:** Use `python-dotenv` to load `HF_TOKEN`.
* **ActivityWatch Telemetry:** Use the `requests` library to query `http://localhost:5600/api/0/buckets`. Find the bucket containing `aw-watcher-window` and fetch the last 2 hours of events. Aggregate the total duration in seconds for each application and identify the top application.
* **LLM Integration (Ollama with HF Fallback):** 
  * Primary: Attempt to generate the roast using a local Ollama instance by sending a POST request to `http://localhost:11434/api/generate` using the `gemma2` model.
  * Fallback: Catch connection errors or timeouts. If Ollama fails or is unreachable, initialize `huggingface_hub.InferenceClient` via: `client = InferenceClient(token=os.getenv("HF_TOKEN"), model="google/gemma-2-9b-it")` and use it to generate the text.
  * In both cases, the output must be a 2-sentence toxic Gen-Z roast based on the user's top application.
* **UI (Windows Desktop Overlay):** Use Python's built-in `tkinter`. 
  * Configure the window to be frameless (`overrideredirect(True)`).
  * Pin it to the top (`-topmost`, True).
  * Make the background transparent using `-transparentcolor` with a hex code like `#000001`.
  * Place it in the bottom-right corner of the screen.
  * The overlay should feature a randomly selected image from `assets/stickers/*.png` and a Tkinter Canvas drawing a comic speech bubble containing the LLM-generated roast.
  * Add a button labeled "Submit Grass Proof" that closes the Tkinter window when clicked.

## Implementation Steps
Please generate the following files:
1. `tracker.py`: Contains a function `get_top_app(hours=2)` that securely queries localhost:5600 using `requests` and returns the name of the most-used app and its active minutes.
2. `gemma_api.py`: Contains a function `generate_roast(app_name, minutes)`. This function must first try to POST to `http://localhost:11434/api/generate`. If it throws a `requests.exceptions.ConnectionError`, it should log the failure and fall back to using `InferenceClient`.
3. `overlay.py`: Contains the `RagebaitClippy` Tkinter class to render the transparent UI and display a random sticker from `assets/stickers/`.
4. `main.py`: The entry point that runs a `while True` loop, checking `tracker.py` every 60 seconds. If a single app exceeds 120 minutes, it calls `gemma_api.py` and spawns `overlay.py`.

Write production-ready, heavily commented code. Let's start with `tracker.py` and `gemma_api.py`.