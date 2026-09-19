import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import trend_radar


class TrendRadarTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(
            2026,
            9,
            19,
            12,
            0,
            tzinfo=ZoneInfo(
                "Asia/Seoul"
            ),
        )

    def test_split_windows(self):
        articles = [
            {
                "recorded_at":
                    (
                        self.now
                        - timedelta(days=2)
                    ).isoformat(),
                "topics": ["MCP"],
            },
            {
                "recorded_at":
                    (
                        self.now
                        - timedelta(days=9)
                    ).isoformat(),
                "topics": ["MCP"],
            },
        ]

        current, previous = (
            trend_radar.split_windows(
                articles,
                self.now,
            )
        )

        self.assertEqual(
            len(current),
            1,
        )
        self.assertEqual(
            len(previous),
            1,
        )

    def test_find_rising_topics_requires_real_increase(self):
        current = [
            {
                "topics": [
                    "MCP",
                ],
            },
            {
                "topics": [
                    "MCP",
                ],
            },
            {
                "topics": [
                    "RAG",
                ],
            },
        ]

        previous = [
            {
                "topics": [
                    "MCP",
                ],
            },
        ]

        rows = (
            trend_radar.find_rising_topics(
                current,
                previous,
            )
        )

        self.assertEqual(
            len(rows),
            1,
        )
        self.assertEqual(
            rows[0]["topic"],
            "MCP",
        )
        self.assertEqual(
            rows[0]["delta"],
            1,
        )

    def test_no_rising_topics_message_is_honest(self):
        message = (
            trend_radar.build_radar_message(
                [],
                "",
                1,
                0,
                now=self.now,
            )
        )

        self.assertIn(
            "아직 없습니다",
            message,
        )


if __name__ == "__main__":
    unittest.main()
