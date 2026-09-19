import json
import os
import tempfile
import unittest

import main


class FeedbackLearningTest(unittest.TestCase):
    def test_feedback_weights_use_stronger_explicit_signals(self):
        payload = {
            "articles": {
                "a": {
                    "article": {
                        "topics": ["MCP", "RAG"],
                    },
                    "feedback": {
                        "helpful": 1,
                        "not_helpful": 0,
                        "more_like_this": 1,
                        "less_like_this": 0,
                    },
                },
                "b": {
                    "article": {
                        "topics": ["Hardware"],
                    },
                    "feedback": {
                        "helpful": 0,
                        "not_helpful": 1,
                        "more_like_this": 0,
                        "less_like_this": 1,
                    },
                },
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(
                directory,
                "feedback.json",
            )

            with open(
                path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    payload,
                    file,
                )

            weights = (
                main.load_feedback_topic_weights(
                    path
                )
            )

        self.assertEqual(
            weights["mcp"],
            1.0,
        )
        self.assertEqual(
            weights["rag"],
            1.0,
        )
        self.assertEqual(
            weights["hardware"],
            -1.0,
        )

    def test_positive_topic_match_adds_one_relevance_point(self):
        article = {
            "title": "MCP server production patterns",
            "summary": "",
            "rss_content": "",
        }

        bias = main.get_feedback_relevance_bias(
            article,
            {
                "mcp": 2.0,
            },
        )

        self.assertEqual(
            bias,
            1,
        )

    def test_negative_topic_match_removes_one_relevance_point(self):
        article = {
            "title": "Hardware accelerator overview",
            "summary": "",
            "rss_content": "",
        }

        bias = main.get_feedback_relevance_bias(
            article,
            {
                "hardware": -2.0,
            },
        )

        self.assertEqual(
            bias,
            -1,
        )

    def test_unmatched_feedback_does_not_change_relevance(self):
        article = {
            "title": "Python automation",
            "summary": "",
            "rss_content": "",
        }

        bias = main.get_feedback_relevance_bias(
            article,
            {
                "mcp": 2.0,
            },
        )

        self.assertEqual(
            bias,
            0,
        )

    def test_feedback_context_is_readable(self):
        context = (
            main.format_feedback_learning_context(
                {
                    "mcp": 1.0,
                    "hardware": -1.0,
                }
            )
        )

        self.assertIn(
            "mcp",
            context,
        )
        self.assertIn(
            "hardware",
            context,
        )


if __name__ == "__main__":
    unittest.main()
