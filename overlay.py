"""Thread-confined Tkinter intervention overlay — duck screams at you."""

from __future__ import annotations

from pathlib import Path
import logging
import tkinter as tk
import winsound

from PIL import Image, ImageTk

LOGGER = logging.getLogger(__name__)


class DuckOverlay:
    """A transparent, always-on-top duck overlay with slide animation."""

    TRANSPARENT_COLOR = "#000001"
    WINDOW_WIDTH = 460
    WINDOW_HEIGHT = 220
    MASCOT_SIZE = 130
    ANIMATION_STEP = 18
    ANIMATION_DELAY_MS = 10

    def __init__(
        self,
        roast: str,
        audio_file: str = "assets/quack.wav",
        asset_path: Path | None = None,
    ) -> None:
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=self.TRANSPARENT_COLOR)
        self.root.wm_attributes("-transparentcolor", self.TRANSPARENT_COLOR)

        self.roast = roast
        self.audio_file = audio_file
        self.asset_path = asset_path or Path(__file__).resolve().parent / "mascot.png"
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.window_w = self.WINDOW_WIDTH
        self.window_h = self.WINDOW_HEIGHT
        self.target_x = max(0, self.screen_width - self.window_w - 24)
        self.target_y = max(0, self.screen_height - self.window_h - 48)
        self.current_y = self.screen_height + 50
        self._slide_in_sound_played = False
        self.root.geometry(
            f"{self.window_w}x{self.window_h}+{self.target_x}+{self.current_y}"
        )

        self.canvas = tk.Canvas(
            self.root,
            width=self.window_w,
            height=self.window_h,
            bg=self.TRANSPARENT_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack()
        self._draw_content()

    def _draw_rounded_rect(
        self,
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        **kwargs: object,
    ) -> int:
        """Draw a smooth rounded rectangle and return its canvas item ID."""
        radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2 - radius,
            x1, y1 + radius,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_content(self) -> None:
        """Draw the duck mascot, speech bubble, and dismiss button."""
        roast_text = f"*QUACK* {self.roast}"
        text_id = self.canvas.create_text(
            130,
            40,
            text=roast_text,
            font=("Segoe UI", 10, "bold"),
            fill="#111111",
            width=280,
            anchor="nw",
        )
        self.root.update_idletasks()
        bbox = self.canvas.bbox(text_id)
        if bbox is None:
            raise RuntimeError("Unable to measure the overlay roast text.")

        x1, y1, x2, y2 = bbox
        bubble_x1, bubble_y1 = x1 - 20, y1 - 20
        bubble_x2, bubble_y2 = x2 + 20, y2 + 20
        bubble_id = self._draw_rounded_rect(
            self.canvas,
            bubble_x1,
            bubble_y1,
            bubble_x2,
            bubble_y2,
            radius=18,
            fill="#fbf3a3",
            outline="#1f2937",
            width=3,
        )
        self.canvas.tag_lower(bubble_id, text_id)

        # Speech bubble tail pointing to the duck
        tail_y = (bubble_y1 + bubble_y2) / 2
        self.canvas.create_polygon(
            bubble_x1,
            tail_y - 14,
            bubble_x1,
            tail_y + 14,
            bubble_x1 - 28,
            tail_y,
            fill="#fbf3a3",
            outline="#1f2937",
        )

        # Duck mascot image
        mascot_y = 0
        try:
            image = Image.open(self.asset_path).convert("RGBA")
            image = image.resize(
                (self.MASCOT_SIZE, self.MASCOT_SIZE),
                Image.Resampling.LANCZOS,
            )
            self.mascot_image = ImageTk.PhotoImage(image)
            mascot_y = max(self.MASCOT_SIZE / 2, (bubble_y1 + bubble_y2) / 2)
            self.canvas.create_image(65, mascot_y, image=self.mascot_image)
        except (FileNotFoundError, OSError):
            LOGGER.warning("mascot.png not found. Rendering text only.")
            self.mascot_image = None

        # Close / dismiss button
        close_button = tk.Button(
            self.root,
            text="×",
            command=self.dismiss,
            font=("Segoe UI", 16, "bold"),
            bg="#2b2b2b",
            fg="#cecece",
            activebackground="#e74c3c",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
        )
        self.canvas.create_window(
            self.window_w - 28,
            24,
            window=close_button,
            width=32,
            height=32,
        )

        # Resize window to fit content
        mascot_bottom = mascot_y + self.MASCOT_SIZE / 2 if self.mascot_image else 0
        self.window_h = int(max(bubble_y2 + 25, mascot_bottom + 15, 70))
        self.window_w = int(max(self.WINDOW_WIDTH, bubble_x2 + 30))
        self.target_x = max(0, self.screen_width - self.window_w - 24)
        self.target_y = max(0, self.screen_height - self.window_h - 48)
        self.canvas.configure(width=self.window_w, height=self.window_h)
        self.root.geometry(
            f"{self.window_w}x{self.window_h}+{self.target_x}+{self.current_y}"
        )

    def slide_in(self) -> None:
        """Animate from below the screen to the position above the taskbar."""
        if not self._slide_in_sound_played:
            audio_path = Path(self.audio_file)
            if not audio_path.is_absolute():
                audio_path = Path(__file__).resolve().parent / audio_path
            try:
                winsound.PlaySound(
                    str(audio_path.resolve()),
                    winsound.SND_FILENAME | winsound.SND_ASYNC,
                )
            except Exception:
                LOGGER.warning("Could not play quack sound from %s.", audio_path)
            self._slide_in_sound_played = True

        if self.current_y <= self.target_y:
            self.current_y = self.target_y
            self.root.geometry(f"+{self.target_x}+{self.current_y}")
            return
        self.current_y = max(self.target_y, self.current_y - self.ANIMATION_STEP)
        self.root.geometry(f"+{self.target_x}+{self.current_y}")
        self.root.after(self.ANIMATION_DELAY_MS, self.slide_in)

    def slide_out(self) -> None:
        """Animate downward and destroy the window after it leaves the screen."""
        if self.current_y >= self.screen_height + 50:
            self.root.destroy()
            return
        self.current_y += self.ANIMATION_STEP
        self.root.geometry(f"+{self.target_x}+{self.current_y}")
        self.root.after(self.ANIMATION_DELAY_MS, self.slide_out)

    def dismiss(self) -> None:
        """Close the overlay with slide-out animation."""
        self.slide_out()

    def show(self) -> None:
        """Start the animation and enter Tkinter's event loop."""
        self.slide_in()
        self.root.mainloop()
