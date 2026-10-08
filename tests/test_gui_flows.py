"""Tests for dashboard, overlay, and tray helper components."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from database import initialize_database, get_recent_logs
from vision_api import VerificationResult


class GuiFlowsTestCase(unittest.TestCase):
    def test_dashboard_image_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_path = temp_path / "ratiobot.sqlite3"
            config_path = temp_path / "config.json"
            config_path.write_text(json.dumps({"strikes": 2}))
            initialize_database(db_path)

            from dashboard import RatioBotDashboard

            with patch("tkinter.Tk") as mock_tk:
                mock_root = MagicMock()
                mock_tk.return_value = mock_root

                dashboard = RatioBotDashboard(config_path=config_path)
                dashboard.status_label = MagicMock()
                dashboard.progressbar = MagicMock()
                dashboard.upload_button = MagicMock()
                dashboard.logs = MagicMock()

                # Test accepted proof flow
                result = VerificationResult(accepted=True, suspicious=False, reason="Accepted")
                with patch("dashboard.database.DATABASE_PATH", db_path):
                    dashboard._complete_image_upload(result, None)

                updated_config = json.loads(config_path.read_text())
                self.assertEqual(updated_config["strikes"], 0)

    def test_tray_launch_helper(self) -> None:
        from tray import _launch

        with patch("subprocess.Popen") as mock_popen:
            _launch("dashboard.py")
            mock_popen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
