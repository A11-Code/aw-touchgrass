"""Grass-proof creation date verification for RatioBot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import ExifTags, Image

LOGGER = logging.getLogger(__name__)
PROOFS_DIR = Path(__file__).resolve().parent / "proofs"


@dataclass(frozen=True)
class VerificationResult:
    accepted: bool
    suspicious: bool
    reason: str


def _metadata_time(image: Image.Image) -> datetime | None:
    """Read DateTimeOriginal or DateTime EXIF tags and return a naive local datetime."""
    exif = image.getexif()
    if not exif:
        return None
    for tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        for tag_id, value in exif.items():
            if ExifTags.TAGS.get(tag_id) == tag_name:
                raw_str = str(value).strip()
                for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S%z"):
                    try:
                        parsed = datetime.strptime(raw_str, fmt)
                        if parsed.tzinfo is not None:
                            parsed = parsed.astimezone().replace(tzinfo=None)
                        return parsed
                    except ValueError:
                        continue
                LOGGER.warning("Invalid EXIF date value for %s: %r", tag_name, value)
    return None


def save_proof_image(image_path: Path, proofs_dir: Path = PROOFS_DIR) -> Path:
    """Preserve a copy of the proof image in the proofs/ directory."""
    proofs_dir.mkdir(parents=True, exist_ok=True)
    timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = proofs_dir / f"proof_{timestamp_prefix}_{image_path.name}"
    dest_path.write_bytes(image_path.read_bytes())
    return dest_path


def cleanup_old_proofs(retention_days: int = 30, proofs_dir: Path = PROOFS_DIR) -> int:
    """Remove proof files older than retention_days from the proofs directory."""
    if not proofs_dir.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed_count = 0
    for proof_file in proofs_dir.glob("proof_*"):
        if proof_file.is_file():
            mtime = datetime.fromtimestamp(proof_file.stat().st_mtime)
            if mtime < cutoff:
                try:
                    proof_file.unlink()
                    removed_count += 1
                except OSError as exc:
                    LOGGER.warning("Failed to delete expired proof %s: %s", proof_file, exc)
    return removed_count


def verify_image(image_path: Path, preserve_proof: bool = True) -> VerificationResult:
    """Verify whether an image was created/taken today."""
    has_metadata = False
    captured_at = None

    try:
        with Image.open(image_path) as image:
            captured_at = _metadata_time(image)
            has_metadata = captured_at is not None
    except Exception as exc:
        LOGGER.warning("Unable to open image for EXIF inspection: %s", exc)

    if captured_at is None:
        try:
            captured_at = datetime.fromtimestamp(image_path.stat().st_mtime)
        except OSError as exc:
            LOGGER.error("Failed to read file modification time: %s", exc)
            return VerificationResult(False, False, "Unable to determine image creation date.")

    today = datetime.now().date()
    if captured_at.date() != today:
        return VerificationResult(
            False,
            False,
            f"The photo was taken on {captured_at.date()}, not today ({today}).",
        )

    if preserve_proof:
        try:
            save_proof_image(image_path)
        except OSError as exc:
            LOGGER.warning("Unable to archive proof copy: %s", exc)

    return VerificationResult(
        True,
        not has_metadata,
        "The proof was accepted (created today).",
    )


def run_upload_flow(parent: tk.Misc | None = None) -> VerificationResult | None:
    """Open a file picker, verify the selection, and show the result overlay."""
    dialog_root = parent
    owns_root = dialog_root is None
    if owns_root:
        dialog_root = tk.Tk()
        dialog_root.withdraw()
    selected = filedialog.askopenfilename(
        title="Upload Grass Proof",
        filetypes=[("Images", "*.jpg *.jpeg *.png *.webp")],
        parent=dialog_root,
    )
    if owns_root and dialog_root is not None:
        dialog_root.destroy()
    if not selected:
        return None

    try:
        result = verify_image(Path(selected))
    except (OSError, RuntimeError, ValueError) as error:
        LOGGER.exception("Grass proof verification failed.")
        from database import insert_log

        insert_log(
            "Grass proof failed",
            0,
            _current_strikes(),
            event_type="proof_failed",
            resolved=True,
        )
        if parent is not None:
            messagebox.showerror("Verification failed", str(error), parent=parent)
        return VerificationResult(False, False, str(error))

    from database import insert_log

    insert_log(
        "Grass proof accepted" if result.accepted else "Grass proof rejected",
        0,
        _current_strikes(),
        event_type="proof_accepted" if result.accepted else "proof_rejected",
        resolved=True,
    )
    if result.accepted:
        from overlay import RagebaitClippy

        RagebaitClippy("Grass proof received.").show_success(result.suspicious)
        if parent is not None:
            messagebox.showinfo(
                "Grass proof accepted",
                "Proof accepted. Your strikes have been reset to 0/3.",
                parent=parent,
            )
    elif parent is not None:
        messagebox.showwarning("Proof rejected", result.reason, parent=parent)
    return result


def _current_strikes() -> int:
    """Read the current strike count for proof audit events."""
    config_path = Path(__file__).resolve().parent / "config.json"
    try:
        return int(json.loads(config_path.read_text(encoding="utf-8")).get("strikes", 0))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        LOGGER.exception("Unable to read current strikes for proof event.")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_upload_flow()
