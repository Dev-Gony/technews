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

    @mock.patch.object(
        telegram_sync.telegram_bot,
        "send_message",
    )
    @mock.patch.object(
        telegram_sync,
        "create_on_demand_digest",
        return_value="<b>digest result</b>",
    )
    def test_digest_command_is_routed(
        self,
        mock_digest,
        mock_send_message,
    ):
        original_chat_id = (
            telegram_sync.telegram_bot.TELEGRAM_ALLOWED_CHAT_ID
        )

        telegram_sync.telegram_bot.TELEGRAM_ALLOWED_CHAT_ID = "123"

        try:
            handled = telegram_sync._process_digest_message(
                {
                    "chat": {"id": 123},
                    "text": "/digest MCP",
                }
            )

            self.assertTrue(handled)
            mock_digest.assert_called_once_with("MCP")
            self.assertEqual(
                mock_send_message.call_count,
                2,
            )
            self.assertEqual(
                mock_send_message.call_args_list[-1],
                mock.call(
                    123,
                    "<b>digest result</b>",
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                ),
            )

        finally:
            telegram_sync.telegram_bot.TELEGRAM_ALLOWED_CHAT_ID = (
                original_chat_id
            )

    @mock.patch.object(
        telegram_sync.telegram_bot,
        "send_message",
    )
    @mock.patch.object(
        telegram_sync,
        "create_followup_detail",
        return_value="<b>detail result</b>",
    )
    def test_followup_message_is_routed(
        self,
        mock_detail,
        mock_send_message,
    ):
        original_chat_id = (
            telegram_sync.telegram_bot.TELEGRAM_ALLOWED_CHAT_ID
        )

        telegram_sync.telegram_bot.TELEGRAM_ALLOWED_CHAT_ID = "123"

        try:
            handled = telegram_sync._process_digest_message(
                {
                    "chat": {"id": 123},
                    "text": "2번 더 자세히",
                }
            )

            self.assertTrue(handled)
            mock_detail.assert_called_once_with(2)
            self.assertEqual(mock_send_message.call_count, 2)
            self.assertEqual(
                mock_send_message.call_args_list[-1],
                mock.call(
                    123,
                    "<b>detail result</b>",
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                ),
            )

        finally:
            telegram_sync.telegram_bot.TELEGRAM_ALLOWED_CHAT_ID = (
                original_chat_id
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
