# Task: Update UI to use a Single Static Mascot
Please update the Tkinter overlay logic in `overlay.py` to use a single mascot image instead of a randomized sticker directory.

## Implementation Details
1. **Asset Path:** The system should look for a single file at `assets/mascot.png`.
2. **Image Processing:** Use the `PIL` (Pillow) library to open `assets/mascot.png`. Resize the image to 100x100 pixels using `Image.Resampling.LANCZOS` so it fits cleanly in the bottom-right Tkinter canvas next to the speech bubble.
3. **Cleanup:** Remove any previous logic involving `os.listdir`, `random.choice`, or the `assets/stickers/` directory.
4. **Error Handling:** If `assets/mascot.png` is missing, catch the `FileNotFoundError`, print a clear warning to the console ("Warning: assets/mascot.png not found. Rendering text only."), and continue rendering the Tkinter window and speech bubble without the image.