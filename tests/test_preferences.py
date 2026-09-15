import json
import os
import tempfile
import unittest

from preferences import (
    DEFAULT_PREFERENCES,
    load_user_preferences,
    validate_preferences,
)


class UserPreferencesTest(unittest.TestCase):
    def test_valid_preferences_are_loaded(self):
        preferences = validate_preferences(
            {
                "profile_name": "test",
                "interests": ["MCP", "Python"],
                "avoid_topics": ["모바일 루머"],
                "scoring": {
                    "detailed_threshold": 12,
                    "brief_threshold": 8,
                },
                "delivery": {
                    "daily_digest": True,
                    "language": "ko",
                },
            }
        )

        self.assertEqual(preferences["profile_name"], "test")
        self.assertEqual(preferences["interests"], ["MCP", "Python"])
        self.assertEqual(preferences["avoid_topics"], ["모바일 루머"])
        self.assertEqual(preferences["scoring"]["detailed_threshold"], 12)
        self.assertEqual(preferences["scoring"]["brief_threshold"], 8)

    def test_missing_file_uses_defaults(self):
        preferences = load_user_preferences(
            "path/that/does/not/exist.json"
        )

        self.assertEqual(
            preferences["interests"],
            DEFAULT_PREFERENCES["interests"],
        )

    def test_invalid_json_uses_defaults(self):
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
        ) as file:
            file.write("{invalid json")
            path = file.name

        try:
            preferences = load_user_preferences(path)
        finally:
            os.remove(path)

        self.assertEqual(
            preferences["scoring"],
            DEFAULT_PREFERENCES["scoring"],
        )

    def test_invalid_threshold_order_uses_default_scoring(self):
        preferences = validate_preferences(
            {
                "scoring": {
                    "detailed_threshold": 8,
                    "brief_threshold": 12,
                }
            }
        )

        self.assertEqual(
            preferences["scoring"],
            DEFAULT_PREFERENCES["scoring"],
        )

    def test_unsupported_language_falls_back_to_korean(self):
        preferences = validate_preferences(
            {
                "delivery": {
                    "daily_digest": True,
                    "language": "en",
                }
            }
        )

        self.assertEqual(
            preferences["delivery"]["language"],
            "ko",
        )


if __name__ == "__main__":
    unittest.main()
