import json
import os
import tempfile
import unittest

from preferences import DEFAULT_PREFERENCES
from telegram_bot import (
    handle_preference_command,
    parse_command,
)


class TelegramCommandTest(unittest.TestCase):
    def test_parse_command_with_argument(self):
        command, argument = parse_command(
            "/add FinOps"
        )

        self.assertEqual(command, "/add")
        self.assertEqual(argument, "FinOps")

    def test_parse_command_with_bot_suffix(self):
        command, argument = parse_command(
            "/add@my_bot MCP"
        )

        self.assertEqual(command, "/add")
        self.assertEqual(argument, "MCP")

    def test_non_command_text(self):
        command, argument = parse_command(
            "MCP 추가해줘"
        )

        self.assertEqual(command, "")
        self.assertEqual(argument, "")


class TelegramPreferenceMutationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(
            self.temp_dir.name,
            "user_preferences.json",
        )

        preferences = json.loads(
            json.dumps(
                DEFAULT_PREFERENCES,
                ensure_ascii=False,
            )
        )

        with open(
            self.path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                preferences,
                file,
                ensure_ascii=False,
                indent=2,
            )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _load_file(self):
        with open(
            self.path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def test_add_interest(self):
        response, changed = handle_preference_command(
            "/add FinOps",
            self.path,
        )

        preferences = self._load_file()

        self.assertTrue(changed)
        self.assertIn("FinOps", preferences["interests"])
        self.assertIn("추가했습니다", response)

    def test_duplicate_interest_is_case_insensitive(self):
        response, changed = handle_preference_command(
            "/add python",
            self.path,
        )

        self.assertFalse(changed)
        self.assertIn("이미 등록된", response)

    def test_remove_interest(self):
        response, changed = handle_preference_command(
            "/remove SQL",
            self.path,
        )

        preferences = self._load_file()

        self.assertTrue(changed)
        self.assertNotIn("SQL", preferences["interests"])
        self.assertIn("삭제했습니다", response)

    def test_interests_does_not_change_file(self):
        response, changed = handle_preference_command(
            "/interests",
            self.path,
        )

        self.assertFalse(changed)
        self.assertIn("AI Agent", response)
        self.assertIn("상세 브리핑 기준", response)

    def test_unknown_command(self):
        response, changed = handle_preference_command(
            "/unknown",
            self.path,
        )

        self.assertFalse(changed)
        self.assertIn("지원하지 않는", response)


if __name__ == "__main__":
    unittest.main()
