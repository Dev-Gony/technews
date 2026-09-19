import unittest

import slack_feedback


class SlackFeedbackTest(unittest.TestCase):
    def test_reaction_counts_map_supported_feedback(self):
        message = {
            "reactions": [
                {
                    "name": "+1",
                    "count": 2,
                },
                {
                    "name": "-1",
                    "count": 1,
                },
                {
                    "name": "fire",
                    "count": 3,
                },
                {
                    "name": "see_no_evil",
                    "count": 4,
                },
                {
                    "name": "eyes",
                    "count": 99,
                },
            ]
        }

        self.assertEqual(
            slack_feedback._reaction_counts(
                message
            ),
            {
                "helpful": 2,
                "not_helpful": 1,
                "more_like_this": 3,
                "less_like_this": 4,
            },
        )

    def test_feedback_key_prefers_article_link(self):
        item = {
            "ts": "123.456",
            "article": {
                "link": "https://example.com/a",
            },
        }

        self.assertEqual(
            slack_feedback._feedback_key(
                item
            ),
            "https://example.com/a",
        )


if __name__ == "__main__":
    unittest.main()
