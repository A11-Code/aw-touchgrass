import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

import tracker
from gemma_api import generate_roast, _two_sentences


class TrackerTests(unittest.TestCase):
    def setUp(self):
        tracker.clear_cache()

    def test_get_top_app_aggregates_events(self):
        now = datetime.now(timezone.utc).isoformat()
        mock_client = Mock()
        mock_client.get_buckets.return_value = {"bucket-1": {"name": "aw-watcher-window"}}
        mock_client.get_events.return_value = [
            {"timestamp": now, "duration": 120, "data": {"app": "Editor"}},
            {"timestamp": now, "duration": 60, "data": {"app": "Browser"}},
            {"timestamp": now, "duration": 60, "data": {"app": "Editor"}},
        ]
        with patch("tracker.get_client", return_value=mock_client):
            self.assertEqual(tracker.get_top_app(), ("Editor", 3.0))

    def test_get_top_app_no_window_bucket(self):
        mock_client = Mock()
        mock_client.get_buckets.return_value = {"other": {"name": "aw-watcher-afk"}}
        with patch("tracker.get_client", return_value=mock_client):
            self.assertEqual(tracker.get_top_app(), (None, 0.0))

    def test_is_activitywatch_connected_true(self):
        mock_client = Mock()
        mock_client.get_buckets.return_value = {}
        with patch("tracker.get_client", return_value=mock_client):
            self.assertTrue(tracker.is_activitywatch_connected())

    def test_is_activitywatch_connected_false(self):
        mock_client = Mock()
        mock_client.get_buckets.side_effect = Exception("Connection refused")
        with patch("tracker.get_client", return_value=mock_client):
            self.assertFalse(tracker.is_activitywatch_connected())


class RoastTests(unittest.TestCase):
    def test_two_sentences_truncates(self):
        text = "First sentence. Second sentence. Third sentence."
        result = _two_sentences(text)
        self.assertEqual(result, "First sentence. Second sentence.")

    def test_generate_roast_empty_app_raises(self):
        with self.assertRaises(ValueError):
            generate_roast("", 10)

    def test_generate_roast_negative_minutes_raises(self):
        with self.assertRaises(ValueError):
            generate_roast("chrome", -1)

    @patch("gemma_api.requests.post", side_effect=Exception("timeout"))
    def test_generate_roast_ollama_down_returns_generic(self, _mock_post):
        result = generate_roast("chrome", 60)
        self.assertIn("chrome", result)
        self.assertIn("60", result)


class MainTests(unittest.TestCase):
    def test_matching_limit_specific_app(self):
        from main import _matching_limit
        limits = {"chrome": 60, "All applications": 120}
        self.assertEqual(_matching_limit("chrome.exe", limits), 60)

    def test_matching_limit_global_fallback(self):
        from main import _matching_limit
        limits = {"All applications": 120}
        self.assertEqual(_matching_limit("unknown", limits), 120)

    def test_matching_limit_no_match(self):
        from main import _matching_limit
        limits = {"chrome": 60}
        self.assertIsNone(_matching_limit("firefox", limits))

    def test_parse_duration_to_minutes(self):
        from main import parse_duration_to_minutes
        self.assertEqual(parse_duration_to_minutes("6 hours"), 360.0)
        self.assertEqual(parse_duration_to_minutes("6h"), 360.0)
        self.assertEqual(parse_duration_to_minutes("6 hrs"), 360.0)
        self.assertEqual(parse_duration_to_minutes("30 mins"), 30.0)
        self.assertEqual(parse_duration_to_minutes("45m"), 45.0)
        self.assertEqual(parse_duration_to_minutes("1h 30m"), 90.0)
        self.assertEqual(parse_duration_to_minutes("6"), 360.0)
        self.assertEqual(parse_duration_to_minutes("120"), 120.0)

    @patch("main.trigger_immediately")
    def test_main_cli_positional_app_and_duration(self, mock_trigger):
        from main import main
        main(["reddit", "6", "hours"])
        mock_trigger.assert_called_once_with("reddit", 360.0)

    @patch("main.trigger_immediately")
    def test_main_cli_named_flags(self, mock_trigger):
        from main import main
        main(["--app", "youtube", "--hours", "3"])
        mock_trigger.assert_called_once_with("youtube", 180.0)

    @patch("main.trigger_immediately")
    def test_main_cli_app_only_defaults_duration(self, mock_trigger):
        from main import main
        main(["twitter"])
        mock_trigger.assert_called_once_with("twitter", 120.0)

    @patch("main.run")
    def test_main_cli_no_args_runs_monitor(self, mock_run):
        from main import main
        main([])
        mock_run.assert_called_once()


    def test_matching_limit_default_limit_fallback(self):
        from main import _matching_limit
        limits = {"chrome": 60}
        self.assertEqual(_matching_limit("firefox", limits, default_limit=45), 45)


class TrayTests(unittest.TestCase):
    def test_ensure_config_exists_creates_defaults(self):
        import tempfile
        import json
        from pathlib import Path
        import tray

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_config = Path(temp_dir) / "config.json"
            with patch("tray.get_config_path", return_value=temp_config):
                created = tray.ensure_config_exists()
                self.assertTrue(created.exists())
                data = json.loads(created.read_text(encoding="utf-8"))
                self.assertIn("ollama_endpoint", data)
                self.assertIn("default_app_limit_minutes", data)
                self.assertIn("max_session_minutes", data)

    @patch("tray.os.startfile")
    def test_open_config_file_calls_startfile(self, mock_startfile):
        import tray
        with patch("tray.os.name", "nt"):
            tray.open_config_file()
            # It runs in a daemon thread, so let's allow thread to run
            import time
            time.sleep(0.05)
            mock_startfile.assert_called_once()

    def test_generate_roast_custom_endpoint_and_model(self):
        with patch("gemma_api.requests.post") as mock_post:
            mock_resp = Mock()
            mock_resp.json.return_value = {"response": "Bro you are cooked. Touch grass now."}
            mock_resp.raise_for_status = Mock()
            mock_post.return_value = mock_resp

            generate_roast(
                "game",
                120,
                ollama_url="http://custom:11434/api/generate",
                ollama_model="custom-model",
            )
            mock_post.assert_called_once()
            call_args, call_kwargs = mock_post.call_args
            self.assertEqual(call_args[0], "http://custom:11434/api/generate")
            self.assertEqual(call_kwargs["json"]["model"], "custom-model")


if __name__ == "__main__":
    unittest.main()


