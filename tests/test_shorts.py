import unittest

import shorts


def make_article(title, score, link, topics=None, rank=1):
    return {
        "title": title,
        "one_line": "",
        "topics": topics or [],
        "key_points": ["포인트"],
        "link": link,
        "selection_score": score,
        "editorial_rank": rank,
    }


class ShortsTest(unittest.TestCase):
    def test_is_ai_article_matches_keywords(self):
        self.assertTrue(
            shorts.is_ai_article(
                make_article("GPT-6 Astra, 가중치 수정", 10, "a")
            )
        )
        self.assertTrue(
            shorts.is_ai_article(
                make_article("무언가", 10, "a", topics=["AI Agentic Workflow"])
            )
        )
        self.assertTrue(
            shorts.is_ai_article(
                make_article("사내 에이전트 도입기", 10, "a")
            )
        )

    def test_is_ai_article_ignores_partial_words(self):
        # "ai"가 다른 영단어 안에 들어 있는 경우는 AI 기사가 아니다.
        self.assertFalse(
            shorts.is_ai_article(
                make_article("Kafka email retries in Lambda", 10, "a", topics=["Event Source Mapping"])
            )
        )

    def test_pick_article_prefers_score_and_skips_used(self):
        issue = {
            "top_stories": [
                make_article("AWS DR 가이드", 15, "dr"),
                make_article("LLM 가중치 수정", 14, "llm"),
            ],
            "more_detailed": [
                make_article("Claude 사용량 급증", 14, "claude", rank=2),
            ],
            "brief_articles": [
                {"title": "AI 단신", "link": "brief", "key_points": None},
            ],
        }

        picked = shorts.pick_article(issue, used_links=set())
        self.assertEqual(picked["link"], "llm")

        picked = shorts.pick_article(issue, used_links={"llm"})
        self.assertEqual(picked["link"], "claude")

        self.assertIsNone(
            shorts.pick_article(issue, used_links={"llm", "claude"})
        )

    def test_validate_script_cleans_hashtags(self):
        script = shorts.validate_script(
            {
                "title": "t",
                "description": "d",
                "hashtags": ["#AI 뉴스", "LLM", " "],
                "scenes": [{"headline": "h", "narration": "n"}] * 4,
            }
        )
        self.assertEqual(script["hashtags"], ["AI뉴스", "LLM"])

    def test_validate_script_rejects_too_few_scenes(self):
        with self.assertRaises(ValueError):
            shorts.validate_script(
                {
                    "title": "t",
                    "description": "d",
                    "hashtags": [],
                    "scenes": [{"headline": "h", "narration": "n"}],
                }
            )

    def test_validate_visual_falls_back_when_empty(self):
        self.assertEqual(shorts.validate_visual(None), {"type": "none"})
        self.assertEqual(shorts.validate_visual({"type": "number", "value": "많이"}), {"type": "none"})
        self.assertEqual(shorts.validate_visual({"type": "flow", "items": ["하나"]}), {"type": "none"})
        self.assertEqual(shorts.validate_visual({"type": "unknown"}), {"type": "none"})

        number = {"type": "number", "value": "0.016%", "label": "수정 비율"}
        self.assertEqual(shorts.validate_visual(number), number)

    def test_align_words_keeps_punctuation_from_script(self):
        boundaries = [
            {"text": "성능이", "startMs": 0, "endMs": 400},
            {"text": "올랐습니다", "startMs": 400, "endMs": 900},
        ]
        words = shorts.align_words("성능이 올랐습니다.", boundaries, 1000)

        self.assertEqual([w["text"] for w in words], ["성능이", "올랐습니다."])
        self.assertEqual(words[1]["startMs"], 400)

    def test_align_words_estimates_without_boundaries(self):
        words = shorts.align_words("가나 다라마바", [], 600)

        self.assertEqual([w["text"] for w in words], ["가나", "다라마바"])
        self.assertAlmostEqual(words[0]["endMs"], 200)
        self.assertAlmostEqual(words[1]["endMs"], 600)

    def test_normalize_oauth_token_removes_wrapping_and_noise(self):
        token = "sk-ant-oat01-" + "Ab_9-" * 10

        self.assertEqual(shorts.normalize_oauth_token(f"  {token}\n"), token)
        self.assertEqual(
            shorts.normalize_oauth_token(token[:20] + "\n" + token[20:]),
            token,
        )
        self.assertEqual(
            shorts.normalize_oauth_token(f"Your OAuth token:\n{token}\nStore this token securely."),
            token,
        )
        # 줄바꿈 자리가 공백으로 바뀐 채 복사된 경우 (setup-token 출력을 그대로 붙여넣음)
        pasted = (
            " ✓ Long-lived authentication token\n created successfully!\n\n"
            " Your OAuth token (valid for 1 year):\n\n"
            f" {token[:25]} {token[25:45]} {token[45:]}\n\n"
            " Store this token securely. You won't be able to see it again.\n"
        )
        self.assertEqual(shorts.normalize_oauth_token(pasted), token)
        self.assertEqual(shorts.normalize_oauth_token(None), "")

    def test_describe_oauth_token_hides_value(self):
        token = "sk-ant-oat01-secretvalue"
        description = shorts.describe_oauth_token(token)

        self.assertNotIn("secretvalue", description)
        self.assertIn(str(len(token)), description)
        self.assertEqual(shorts.describe_oauth_token(""), "토큰 없음")


if __name__ == "__main__":
    unittest.main()
