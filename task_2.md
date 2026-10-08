# Task: Add Slide-In/Slide-Out Animation and Duck Persona to Tkinter Overlay
Please update the `RagebaitClippy` class in `overlay.py` to animate the window sliding onto the screen from the bottom, and sliding back down when dismissed. 

## Implementation Details

1. **Slide-In Animation:**
   * When initialized, set the window's starting `Y` position to be completely off-screen at the bottom (`screen_height + 50`).
   * Create a method `slide_in(self)` that uses `self.root.after(10, self.slide_in)` to incrementally decrease the `Y` coordinate by 15-20 pixels per frame until it reaches the target position (hovering just above the taskbar).
   * Call `slide_in()` right before `self.root.mainloop()`.

2. **Slide-Out Animation:**
   * Instead of immediately calling `self.root.destroy()` when the "Submit Grass Proof" button is clicked, trigger a new method `slide_out(self)`.
   * `slide_out` should use `self.root.after()` to incrementally increase the `Y` coordinate until the window is fully off-screen again.
   * Once off-screen, call `self.root.destroy()` and open the camera/verification logic.

3. **The Duck Persona (Text Update):**
   * Prepend the text `"*QUACK* "` in bold to the beginning of whatever roast text is passed to the class. 
   * Update the placeholder test text at the bottom of the file to reflect the new target audience (Gamers/Engineers). Example test text: "*QUACK* Bro has been compiling Java and debugging Spring Boot for 4 hours but still has a NullPointerException. Your brain is cooked. Go touch real grass."

4. **Thread Safety:** Ensure the animation logic does not use `time.sleep()`, as that will freeze the Tkinter main thread. Rely strictly on `self.root.after()`.