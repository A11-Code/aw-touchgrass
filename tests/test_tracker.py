import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import tracker


class TrackerTests(unittest.TestCase):
    def test_get_top_app_aggregates_events(self):
        now = datetime.now(timezone.utc).isoformat()
        responses = [
            self._response({"bucket-1": {"name": "aw-watcher-window"}}),
            self._response(
                [
                    {"timestamp": now, "duration": 120, "data": {"app": "Editor"}},
                    {"timestamp": now, "duration": 60, "data": {"app": "Browser"}},
                    {"timestamp": now, "duration": 60, "data": {"app": "Editor"}},
                ]
            ),
        ]

        with patch("tracker.requests.get", side_effect=responses):
            self.assertEqual(tracker.get_top_app(), ("Editor", 3.0))

    def test_get_top_app_returns_empty_result_when_bucket_is_missing(self):
        with patch(
            "tracker.requests.get",
            return_value=self._response({"other": {"name": "aw-watcher-afk"}}),
        ):
            self.assertEqual(tracker.get_top_app(), (None, 0.0))

    @staticmethod
    def _response(payload):
        response = Mock()
        response.json.return_value = payload
        return response


if __name__ == "__main__":
    unittest.main()
