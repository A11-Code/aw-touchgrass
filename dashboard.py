"""RatioBot settings dashboard."""

from __future__ import annotations

import json
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import database
from main import ALL_APPLICATIONS
import tracker

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


class RatioBotDashboard:
    """Dark Fluent-style editor for RatioBot's persisted settings."""

    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self.config_path = config_path
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.root = tk.Tk()
        self.root.title("RatioBot Settings")
        self.root.configure(bg="#121212")
        self.root.geometry("680x560")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.status_label = None
        self.progressbar = None
        self.upload_button = None
        self._build()

    def _build(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Dark.TCombobox",
            fieldbackground="#202020",
            background="#2ecc71",
            foreground="#cecece",
        )
        style.configure(
            "Dark.TNotebook",
            background="#121212",
            borderwidth=0,
        )
        style.configure(
            "Dark.TNotebook.Tab",
            background="#202020",
            foreground="#cecece",
            padding=(16, 8),
        )

        tk.Label(
            self.root, text="RatioBot Dashboard", bg="#121212", fg="#cecece",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w", padx=28, pady=(24, 18))
        self.strikes_label = tk.Label(
            self.root,
            text=f"Strikes: {int(self.config.get('strikes', 0))}/3",
            bg="#121212",
            fg="#e74c3c" if int(self.config.get("strikes", 0)) >= 3 else "#cecece",
            font=("Segoe UI", 12, "bold"),
        )
        self.strikes_label.pack(anchor="w", padx=28, pady=(0, 12))
        self._refresh_strikes()
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=24, pady=(0, 10))
        settings_tab = tk.Frame(notebook, bg="#121212")
        history_tab = tk.Frame(notebook, bg="#121212")
        notebook.add(settings_tab, text="Settings")
        notebook.add(history_tab, text="History & Logs")

        frame = tk.Frame(settings_tab, bg="#1e1e1e", padx=20, pady=18)
        frame.pack(fill="x", padx=8, pady=10)

        self.apps = ttk.Combobox(
            frame,
            values=[ALL_APPLICATIONS, *tracker.get_recent_apps()],
            state="readonly",
            style="Dark.TCombobox",
        )
        self.apps.pack(fill="x", pady=(0, 10))
        self.apps.current(0)
        self.apps.bind("<<ComboboxSelected>>", self._load_selected_limit)

        self.limit_entry = self._entry(
            frame,
            "Daily app limit (minutes)",
            str(self.config.get("app_limits", {}).get(ALL_APPLICATIONS, 120)),
        )
        self._button(frame, "Add/Update Rule", self._update_rule).pack(fill="x", pady=(4, 14))
        self.session_entry = self._entry(
            frame,
            "Maximum continuous session (minutes)",
            str(self.config.get("max_session_minutes", 240)),
        )
        self.openrouter_key_entry = self._entry(
            frame,
            "OpenRouter API Key",
            str(self.config.get("openrouter_key", "")),
        )

        audio_row = tk.Frame(frame, bg="#121212")
        audio_row.pack(fill="x", pady=14)
        self.audio_label = tk.Label(
            audio_row, text=self.config.get("audio_file", "assets/quack.wav"),
            bg="#121212", fg="#cecece", anchor="w",
        )
        self.audio_label.pack(side="left", fill="x", expand=True)
        self._button(audio_row, "Choose WAV", self._choose_audio).pack(side="right")
        self._button(settings_tab, "Save Settings", self._save, large=True).pack(
            fill="x", padx=28, pady=(18, 24)
        )
        proof_card = tk.Frame(settings_tab, bg="#1e1e1e", padx=20, pady=16)
        proof_card.pack(fill="x", padx=8, pady=(0, 10))
        tk.Label(
            proof_card,
            text="Grass proof",
            bg="#1e1e1e",
            fg="#cecece",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")
        self.upload_button = self._button(
            proof_card, "Upload Grass Proof", self._upload_proof
        )
        self.upload_button.pack(fill="x", pady=(8, 4))
        self.progressbar = ttk.Progressbar(
            proof_card, mode="indeterminate", length=300
        )
        self.status_label = tk.Label(
            proof_card,
            text="Ready for a photo.",
            bg="#1e1e1e",
            fg="#8f9aa3",
            font=("Segoe UI", 9),
        )
        self.status_label.pack(anchor="w", pady=(6, 0))
        self._build_history(history_tab)

    def _build_history(self, parent: tk.Frame) -> None:
        columns = ("timestamp", "event", "app", "minutes", "strikes", "resolved")
        style = ttk.Style(self.root)
        style.configure(
            "History.Treeview",
            background="#1e1e1e",
            fieldbackground="#1e1e1e",
            foreground="#cecece",
            rowheight=30,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "History.Treeview.Heading",
            background="#2b2b2b",
            foreground="#cecece",
            font=("Segoe UI", 9, "bold"),
        )
        self.logs = ttk.Treeview(
            parent, columns=columns, show="headings", style="History.Treeview"
        )
        headings = {
            "timestamp": "Timestamp",
            "event": "Event",
            "app": "Trigger",
            "minutes": "Minutes",
            "strikes": "Strikes",
            "resolved": "Resolved",
        }
        for column, heading in headings.items():
            self.logs.heading(column, text=heading)
            self.logs.column(column, width=110 if column != "timestamp" else 155)
        self.logs.pack(fill="both", expand=True, padx=8, pady=8)
        for log in database.get_recent_logs(10):
            self.logs.insert(
                "",
                "end",
                values=(
                    log["timestamp"][:19].replace("T", " "),
                    log.get("event_type", "warning").replace("_", " ").title(),
                    log["trigger_app"],
                    f"{log['active_minutes']:.1f}",
                    log["strike_count"],
                    "Yes" if log["resolved"] else "No",
                ),
            )

    def _refresh_strikes(self) -> None:
        """Keep the dashboard indicator current while it remains open."""
        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
            strikes = int(config.get("strikes", 0))
            self.strikes_label.config(
                text=f"Strikes: {strikes}/3",
                fg="#e74c3c" if strikes >= 3 else "#cecece",
            )
            self.root.after(1000, self._refresh_strikes)
        except (OSError, json.JSONDecodeError, tk.TclError):
            return

    def _entry(self, parent: tk.Widget, label: str, value: str) -> tk.Entry:
        tk.Label(parent, text=label, bg="#121212", fg="#cecece",
                 font=("Segoe UI", 10)).pack(anchor="w")
        entry = tk.Entry(parent, bg="#202020", fg="#cecece", insertbackground="#cecece",
                         relief="flat")
        entry.insert(0, value)
        entry.pack(fill="x", pady=(4, 10), ipady=6)
        return entry

    def _button(self, parent: tk.Widget, text: str, command, large: bool = False) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command, bg="#2ecc71", fg="#121212",
            activebackground="#27ae60", relief="flat", bd=0,
            font=("Segoe UI", 11 if large else 9, "bold"),
            cursor="hand2", padx=10, pady=8 if large else 4,
        )

    def _load_selected_limit(self, _event=None) -> None:
        app = self.apps.get()
        self.limit_entry.delete(0, tk.END)
        self.limit_entry.insert(0, str(self.config["app_limits"].get(app, 120)))

    def _update_rule(self) -> None:
        app = self.apps.get().strip()
        if not app:
            messagebox.showwarning("Select an app", "Choose an application first.")
            return
        try:
            limit = int(self.limit_entry.get())
            if limit <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid limit", "Enter a positive whole number.")
            return
        self.config.setdefault("app_limits", {})[app] = limit

    def _choose_audio(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose quack sound", filetypes=[("WAV audio", "*.wav")]
        )
        if selected:
            self.config["audio_file"] = selected
            self.audio_label.config(text=selected)

    def _upload_proof(self) -> None:
        selected = filedialog.askopenfilename(
            title="Upload Grass Proof",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp")],
            parent=self.root,
        )
        if not selected:
            return
        self.progressbar.pack(fill="x", pady=(4, 0))
        self.progressbar.start(10)
        self.status_label.config(
            text="Analyzing metadata and pixels... (This may take a minute)",
            fg="#3498db",
        )
        self.upload_button.config(state=tk.DISABLED)
        threading.Thread(
            target=self.process_image,
            args=(selected,),
            daemon=True,
        ).start()

    def process_image(self, filepath: str) -> None:
        """Verify a selected image off the Tkinter thread."""
        from vision_api import verify_image

        try:
            result = verify_image(Path(filepath))
            error = None
        except (OSError, RuntimeError, ValueError) as caught:
            result = None
            error = caught
        try:
            self.root.after(0, self._complete_image_upload, result, error)
        except tk.TclError:
            # The user may have closed the dashboard while verification ran.
            return

    def _complete_image_upload(self, result, error) -> None:
        """Apply worker results safely on Tkinter's main thread."""
        if self.progressbar is not None:
            self.progressbar.stop()
            self.progressbar.pack_forget()
        self.upload_button.config(state=tk.NORMAL)
        if error is not None:
            self.status_label.config(
                text=f"Verification failed: {error}", fg="#e74c3c"
            )
            database.insert_log(
                "Grass proof failed",
                0,
                self._current_strikes(),
                event_type="proof_failed",
                resolved=True,
            )
        else:
            accepted = bool(result.accepted)
            event_type = "proof_accepted" if accepted else "proof_rejected"
            database.insert_log(
                "Grass proof accepted" if accepted else "Grass proof rejected",
                0,
                self._current_strikes(),
                event_type=event_type,
                resolved=True,
            )
            if accepted:
                self._reset_strikes()
                self.status_label.config(
                    text="Proof accepted — strikes reset to 0/3.",
                    fg="#2ecc71",
                )
            else:
                self.status_label.config(
                    text=f"Proof rejected: {result.reason}", fg="#e74c3c"
                )
        self._refresh_history()

    def _current_strikes(self) -> int:
        return int(json.loads(self.config_path.read_text(encoding="utf-8")).get("strikes", 0))

    def _reset_strikes(self) -> None:
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        config["strikes"] = 0
        self.config_path.write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )
        database.resolve_logs()

    def _refresh_history(self) -> None:
        """Refresh history after a proof event without reopening the dashboard."""
        for item in self.logs.get_children():
            self.logs.delete(item)
        for log in database.get_recent_logs(10):
            self.logs.insert(
                "",
                "end",
                values=(
                    log["timestamp"][:19].replace("T", " "),
                    log.get("event_type", "warning").replace("_", " ").title(),
                    log["trigger_app"],
                    f"{log['active_minutes']:.1f}",
                    log["strike_count"],
                    "Yes" if log["resolved"] else "No",
                ),
            )

    def _save(self) -> None:
        try:
            session_limit = int(self.session_entry.get())
            if session_limit <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid session limit", "Enter a positive whole number.")
            return
        self.config["max_session_minutes"] = session_limit
        self.config["openrouter_key"] = self.openrouter_key_entry.get().strip()
        self.config_path.write_text(json.dumps(self.config, indent=2) + "\n", encoding="utf-8")
        self.root.destroy()

    def show(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    RatioBotDashboard().show()
