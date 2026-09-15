import unittest
from unittest.mock import patch

import telegram_digest


class TelegramDigestHelperTest(unittest.TestCase):
    def test_query_tokens_are_normalized(self):
        self.assertEqual(
            telegram_digest._query_tokens("AI Agent AI"),
            ["ai", "agent"],
        )

    @patch(
        "telegram_digest.technews.get_prefilter_text",
        return_value="MCP 서버를 연결하는 방법",
    )
    def test_heuristic_score_matches_preview(
        self,
        _mock_preview,
    ):
        article = {
            "title": "Agent Tooling",
        }

        score = telegram_digest._heuristic_score(
            article,
            "MCP",
        )

        self.assertGreater(score, 0)

    def test_empty_query_returns_usage_message(self):
        self.assertIn(
            "/digest MCP",
            telegram_digest.create_on_demand_digest(""),
        )

    def test_build_digest_message(self):
        items = [
            {
                "article": {
                    "title": "MCP Example",
                    "company": "Example Tech",
                    "link": "https://example.com/mcp",
                },
                "score": 13,
                "reason": "MCP와 직접 관련 있음",
                "summary": {
                    "one_line": "MCP 도구 연결 사례",
                    "why_it_matters": "Agent 도구 연결에 활용 가능",
                    "takeaway": "도구 경계를 작게 설계",
                },
            }
        ]

        message = telegram_digest.build_digest_message(
            "MCP",
            items,
        )

        self.assertIn("MCP — 온디맨드 Tech Digest", message)
        self.assertIn("MCP Example", message)
        self.assertIn("https://example.com/mcp", message)


if __name__ == "__main__":
    unittest.main()
