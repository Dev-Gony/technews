import json
import os
import tempfile
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
                },
            }
        ]

        message = telegram_digest.build_digest_message(
            "MCP",
            items,
        )

        self.assertIn("<b>MCP Tech Digest</b>", message)
        self.assertIn("오늘 볼 만한 기사 1개", message)
        self.assertIn("<b>1. MCP Example</b>", message)
        self.assertIn("MCP 도구 연결 사례", message)
        self.assertIn("💡 Agent 도구 연결에 활용 가능", message)
        self.assertIn("원문 보기 ↗", message)
        self.assertIn("1번 더 자세히", message)
        self.assertIn("x=1&amp;y=2", message)
        self.assertNotIn("🛠", message)
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

    def test_parse_followup_selection(self):
        self.assertEqual(
            telegram_digest.parse_followup_selection("1번 더 자세히"),
            1,
        )
        self.assertEqual(
            telegram_digest.parse_followup_selection("2번 설명해줘"),
            2,
        )
        self.assertIsNone(
            telegram_digest.parse_followup_selection("MCP 뉴스 찾아줘"),
        )

    def test_digest_state_round_trip(self):
        items = [
            {
                "article": {
                    "title": "MCP Example",
                    "company": "Example Tech",
                    "link": "https://example.com/mcp",
                    "summary": "summary",
                    "rss_content": "content",
                    "source_kind": "direct",
                },
                "score": 13,
                "reason": "관련 있음",
                "summary": {"one_line": "요약"},
            }
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "state.json")
            telegram_digest.save_digest_state("MCP", items, path)
            state = telegram_digest.load_digest_state(path)

        self.assertEqual(state["query"], "MCP")
        self.assertEqual(state["items"][0]["score"], 13)
        self.assertEqual(
            state["items"][0]["article"]["title"],
            "MCP Example",
        )

    @patch(
        "telegram_digest.technews.call_gemini",
        return_value=json.dumps(
            {
                "summary": "상세 요약",
                "key_points": ["포인트 1", "포인트 2"],
                "takeaway": "실무 적용 포인트",
            },
            ensure_ascii=False,
        ),
    )
    @patch(
        "telegram_digest.technews.get_article_content",
        return_value="기사 본문",
    )
    def test_create_followup_detail(
        self,
        _mock_content,
        _mock_gemini,
    ):
        state = {
            "query": "MCP",
            "items": [
                {
                    "article": {
                        "title": "MCP Example",
                        "company": "Example Tech",
                        "link": "https://example.com/mcp",
                        "summary": "",
                        "rss_content": "",
                        "source_kind": "direct",
                    },
                    "score": 13,
                    "reason": "관련 있음",
                    "summary": {},
                }
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "state.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump(state, file, ensure_ascii=False)

            message = telegram_digest.create_followup_detail(1, path)

        self.assertIn("1번 상세 분석", message)
        self.assertIn("상세 요약", message)
        self.assertIn("포인트 1", message)
        self.assertIn("실무 적용 포인트", message)


if __name__ == "__main__":
    unittest.main()
