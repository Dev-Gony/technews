import unittest

import main


class SlackNewsActionTest(unittest.TestCase):
    def test_high_actionability_renders_action(self):
        summary = main.format_article_summary(
            {
                "one_line": "핵심 요약",
                "key_points": ["포인트 1"],
                "concepts": ["MCP"],
                "recommended_for": "개발자",
                "actionability": 5,
                "action": {
                    "type": "code_improvement",
                    "title": "JSON 응답 처리 로직을 구조화 출력으로 바꿔본다.",
                    "steps": [
                        "현재 fallback 지점을 찾는다.",
                        "구조화 출력 방식으로 작은 실험을 한다.",
                    ],
                    "effort": "30~60분",
                },
            }
        )

        self.assertIn("⚡ [직접 해볼 것]", summary)
        self.assertIn("유형: 코드 개선", summary)
        self.assertIn("예상 작업량: 30~60분", summary)
        self.assertIn("현재 fallback 지점을 찾는다.", summary)

    def test_low_actionability_hides_action(self):
        summary = main.format_article_summary(
            {
                "one_line": "개념 소개 기사",
                "key_points": ["포인트 1"],
                "concepts": ["AI"],
                "recommended_for": "입문자",
                "actionability": 2,
                "action": {
                    "type": "study",
                    "title": "공부해본다.",
                    "steps": ["문서를 읽는다."],
                    "effort": "15~30분",
                },
            }
        )

        self.assertNotIn("⚡ [직접 해볼 것]", summary)
        self.assertNotIn("공부해본다.", summary)


    def test_detail_prompt_renders_nested_action_json(self):
        prompt = main.build_detail_prompt(
            [
                {
                    "article": {
                        "company": "Example Tech",
                        "title": "Structured Output",
                        "pub_date": "2026-09-19",
                        "selection_score": 14,
                        "selection_reason": "실무 적용 가치가 높음",
                    },
                    "content": "본문",
                }
            ]
        )

        self.assertIn(
            '"action": {',
            prompt,
        )
        self.assertIn(
            '"type": "experiment"',
            prompt,
        )
        self.assertIn(
            '"effort": "30~60분"',
            prompt,
        )

    def test_invalid_actionability_is_safe(self):
        summary = main.format_article_summary(
            {
                "one_line": "요약",
                "key_points": [],
                "concepts": [],
                "recommended_for": "",
                "actionability": "invalid",
                "action": "invalid",
            }
        )

        self.assertIn("[한줄 요약]", summary)
        self.assertNotIn("⚡ [직접 해볼 것]", summary)


if __name__ == "__main__":
    unittest.main()
