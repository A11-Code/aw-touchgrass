import tkinter as tk
from PIL import Image, ImageTk
import os
import winsound

class AnimatedBubbleMockup:
    def __init__(self, roast_text="*QUACK* Bro has been on Reddit for 4 hours. You're actually cooked. Close the browser and go touch grass."):
        self.root = tk.Tk()
        
        # 1. Transparent & Frameless Window
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        
        TRANS_COLOR = "#000001"
        self.root.config(bg=TRANS_COLOR)
        self.root.wm_attributes("-transparentcolor", TRANS_COLOR)

        # 2. Dimensions & Screen Placement
        self.window_w, self.window_h = 440, 320
        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        
        # Target position (bottom right corner, just above taskbar)
        self.pos_x = self.screen_w - self.window_w - 30
        self.target_y = self.screen_h - self.window_h - 60
        
        # Starting position (completely off-screen at the bottom)
        self.current_y = self.screen_h + 50
        self.root.geometry(f"{self.window_w}x{self.window_h}+{self.pos_x}+{self.current_y}")

        self.canvas = tk.Canvas(
            self.root, 
            width=self.window_w, 
            height=self.window_h, 
            bg=TRANS_COLOR, 
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # 3. Draw Speech Bubble Body
        self.draw_rounded_bubble(
            self.canvas, 15, 10, self.window_w - 15, 160, 
            radius=20, fill="#FFFFFF", outline="#111111", width=3
        )

        # 4. Speech Bubble Tail
        tail_points = [190, 155, 230, 155, 210, 195]
        self.canvas.create_polygon(tail_points, fill="#FFFFFF", outline="#111111", width=3)
        self.canvas.create_line(192, 158, 228, 158, fill="#FFFFFF", width=5)

        # 5. Roast Text
        self.canvas.create_text(
            self.window_w // 2, 85,
            text=roast_text,
            font=("Comic Sans MS", 10, "bold"),
            fill="#111111",
            width=370,
            justify="center"
        )

        # 6. Rubber Duck Mascot
        mascot_path = "mascot.png"
        try:
            if os.path.exists(mascot_path):
                pil_img = Image.open(mascot_path).convert("RGBA")
                pil_img = pil_img.resize((110, 110), Image.Resampling.NEAREST)
                self.duck_photo = ImageTk.PhotoImage(pil_img)
                self.canvas.create_image(self.window_w // 2, 250, image=self.duck_photo)
            else:
                self.canvas.create_text(self.window_w // 2, 250, text="[Mascot Not Found]", fill="white")
        except Exception as e:
            print(f"Error loading mascot: {e}")

        # 7. Action Button
        self.dismiss_btn = tk.Button(
            self.root, 
            text="🌿 Submit Grass Proof", 
            font=("Segoe UI", 9, "bold"),
            bg="#2ecc71", 
            fg="#111111",
            activebackground="#27ae60",
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.slide_out
        )
        self.dismiss_btn.place(x=290, y=250, width=135, height=34)

    def draw_rounded_bubble(self, canvas, x1, y1, x2, y2, radius=25, **kwargs):
        """Draws a smooth rounded rectangle for the speech bubble."""
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1
        ]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def slide_in(self):
        """Animates the window sliding up from the bottom of the screen."""
        if self.current_y == self.screen_h + 50:
            try:
                winsound.PlaySound("quack.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"Audio error: {e}")

        if self.current_y > self.target_y:
            self.current_y -= 15
            self.root.geometry(f"{self.window_w}x{self.window_h}+{self.pos_x}+{self.current_y}")
            self.root.after(16, self.slide_in)

    def slide_out(self):
        """Animates the window sliding back down off-screen before closing."""
        if self.current_y < self.screen_h + 50:
            self.current_y += 15
            self.root.geometry(f"{self.window_w}x{self.window_h}+{self.pos_x}+{self.current_y}")
            self.root.after(16, self.slide_out)
        else:
            self.root.destroy()
            print("UI closed. Triggering verification...")

    def show(self):
        self.slide_in()
        self.root.mainloop()

if __name__ == "__main__":
    app = AnimatedBubbleMockup()
    app.show()