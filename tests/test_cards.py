import unittest

import cards


def make_content(slides):
    return {"section": "AI · 비용", "slides": slides, "caption": "훅 한 줄", "hashtags": ["#AI 비용", "LLM", " "]}


class CardsTest(unittest.TestCase):
    def test_validate_cards_cleans_text_and_drops_empty_slides(self):
        content = cards.validate_cards(
            make_content(
                [
                    {"type": "cover", "title": "첫 줄\\n둘째 줄", "body": " 설명 "},
                    {"type": "story", "title": "무슨 일", "items": ["사실 1", " ", "사실 2"]},
                    {"type": "number"},
                    {"type": "checklist", "title": "써먹기", "items": ["확인하기"]},
                    {"type": "outro", "title": "질문?"},
                ]
            )
        )

        self.assertEqual([slide["type"] for slide in content["slides"]], ["cover", "story", "checklist", "outro"])
        self.assertEqual(content["slides"][0]["title"], "첫 줄\n둘째 줄")
        self.assertEqual(content["slides"][0]["body"], "설명")
        self.assertEqual(content["slides"][1]["items"], ["사실 1", "사실 2"])
        self.assertEqual(content["hashtags"], ["AI비용", "LLM"])

    def test_validate_cards_requires_cover_first_and_outro_last(self):
        with self.assertRaises(ValueError):
            cards.validate_cards(
                make_content(
                    [
                        {"type": "story", "title": "a"},
                        {"type": "story", "title": "b"},
                        {"type": "checklist", "title": "c"},
                        {"type": "outro", "title": "d"},
                    ]
                )
            )

        with self.assertRaises(ValueError):
            cards.validate_cards(
                make_content(
                    [
                        {"type": "cover", "title": "a"},
                        {"type": "story", "title": "b"},
                        {"type": "checklist", "title": "c"},
                        {"type": "caution", "title": "d"},
                    ]
                )
            )

    def test_build_caption_adds_link_and_hashtags(self):
        content = {"caption": "Revolut이 비용을 줄였다.", "hashtags": ["AI", "LLM"]}
        article = {"link": "https://news.hada.io/topic?id=1", "company": "GeekNews"}
        caption = cards.build_caption(content, article)

        self.assertTrue(caption.startswith("Revolut이 비용을 줄였다."))
        self.assertIn("원문(GeekNews): https://news.hada.io/topic?id=1", caption)
        self.assertTrue(caption.endswith("#AI #LLM"))
        self.assertLessEqual(len(caption), 2200)


if __name__ == "__main__":
    unittest.main()
