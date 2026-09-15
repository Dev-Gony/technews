import unittest
from unittest import mock

import telegram_sync


class TelegramSyncTest(unittest.TestCase):
    @mock.patch.object(
        telegram_sync.telegram_bot,
        "process_message",
    )
    @mock.patch.object(
        telegram_sync.telegram_bot,
        "save_offset",
    )
    @mock.patch.object(
        telegram_sync.telegram_bot,
        "get_updates",
    )
    @mock.patch.object(
        telegram_sync.telegram_bot,
        "load_offset",
    )
    def test_process_pending_updates(
        self,
        mock_load_offset,
        mock_get_updates,
        mock_save_offset,
        mock_process_message,
    ):
        original_token = (
            telegram_sync.telegram_bot.TELEGRAM_BOT_TOKEN
        )

        telegram_sync.telegram_bot.TELEGRAM_BOT_TOKEN = (
            "test-token"
        )

        try:
            mock_load_offset.return_value = 10
            mock_get_updates.return_value = [
                {
                    "update_id": 10,
                    "message": {
                        "chat": {"id": 1},
                        "text": "/interests",
                    },
                },
                {
                    "update_id": 11,
                    "message": {
                        "chat": {"id": 1},
                        "text": "/add FinOps",
                    },
                },
            ]

            processed = (
                telegram_sync.process_pending_updates()
            )

            self.assertEqual(processed, 2)
            mock_get_updates.assert_called_once_with(10)
            self.assertEqual(
                mock_save_offset.call_args_list,
                [
                    mock.call(11),
                    mock.call(12),
                ],
            )
            self.assertEqual(
                mock_process_message.call_count,
                2,
            )

        finally:
            telegram_sync.telegram_bot.TELEGRAM_BOT_TOKEN = (
                original_token
            )

    def test_missing_token_fails_fast(self):
        original_token = (
            telegram_sync.telegram_bot.TELEGRAM_BOT_TOKEN
        )

        telegram_sync.telegram_bot.TELEGRAM_BOT_TOKEN = ""

        try:
            with self.assertRaises(RuntimeError):
                telegram_sync.process_pending_updates()

        finally:
            telegram_sync.telegram_bot.TELEGRAM_BOT_TOKEN = (
                original_token
            )


if __name__ == "__main__":
    unittest.main()
