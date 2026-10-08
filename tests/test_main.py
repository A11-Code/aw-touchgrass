import unittest

from main import ALL_APPLICATIONS, _matching_limit


class ApplicationLimitTests(unittest.TestCase):
    def test_global_rule_applies_when_no_specific_rule_exists(self):
        self.assertEqual(
            _matching_limit("Firefox.exe", {ALL_APPLICATIONS: 90}),
            90.0,
        )

    def test_specific_rule_overrides_global_rule(self):
        self.assertEqual(
            _matching_limit(
                "Code.exe",
                {ALL_APPLICATIONS: 90, "Code": 120},
            ),
            120.0,
        )

    def test_unknown_app_without_global_rule_has_no_limit(self):
        self.assertIsNone(_matching_limit("Firefox.exe", {"Code": 120}))


if __name__ == "__main__":
    unittest.main()
