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

    def test_build_digest_message_is_compact_html(self):
        items = [
            {
                "article": {
                    "title": "MCP Example",
                    "company": "Example Tech",
                    "link": "https://example.com/mcp?x=1&y=2",
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

        self.assertIn("<b>MCP Tech Digest</b>", message)
        self.assertIn("지금 볼 만한 기사 1개", message)
        self.assertIn("<b>1. MCP Example</b>", message)
        self.assertIn("💡 Agent 도구 연결에 활용 가능", message)
        self.assertIn("🛠 도구 경계를 작게 설계", message)
        self.assertIn("원문 보기 ↗", message)
        self.assertIn("x=1&amp;y=2", message)
        self.assertNotIn("링크: https://", message)

    def test_build_digest_message_escapes_html(self):
        items = [
            {
                "article": {
                    "title": "RAG < MCP",
                    "company": "A&B Tech",
                    "link": "https://example.com/?a=1&b=2",
                },
                "score": 14,
                "reason": "관련 있음",
                "summary": {
                    "one_line": "A < B 구조",
                    "why_it_matters": "안전한 표시",
                    "takeaway": "HTML escape 적용",
                },
            }
        ]

        message = telegram_digest.build_digest_message(
            "MCP & RAG",
            items,
        )

        self.assertIn("MCP &amp; RAG", message)
        self.assertIn("RAG &lt; MCP", message)
        self.assertIn("A&amp;B Tech", message)


if __name__ == "__main__":
    unittest.main()
