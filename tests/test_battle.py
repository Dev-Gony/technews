import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import battle  # noqa: E402
import shorts  # noqa: E402


class BattleTest(unittest.TestCase):
    def test_grade_only_checkable_questions(self):
        check = {"type": "count", "text": "strawberry", "char": "r"}
        truth, result = battle.grade(check, {"Claude": "3", "Gemini": "2개입니다"})
        self.assertEqual(truth, "3")
        self.assertEqual(result, {"Claude": True, "Gemini": False})
        self.assertEqual(battle.grade({"type": "number", "value": 9.9}, {"Claude": "9.9", "Gemini": "9.11"})[1], {"Claude": True, "Gemini": False})
        self.assertEqual(battle.grade(None, {"Claude": "아무 답"}), (None, {}))

    def test_clean_answer_strips_markdown_emoji_and_long_text(self):
        self.assertEqual(battle.clean_answer('**"냥냥펀치 😺"**'), "냥냥펀치")
        self.assertTrue(battle.clean_answer("가" * 100).endswith("…"))
        self.assertEqual(len(battle.clean_answer("가" * 100)), battle.ANSWER_MAX + 1)

    def test_script_shows_real_answers_and_asks_viewers(self):
        item = {"id": "x", "hook": "아재개그 대결을", "cover": "AI 아재개그\n대결", "title": "AI 아재개그 대결", "prompt": "고양이로 아재개그 하나만 해 줘."}
        answers = {"Claude": "고양이가 좋아하는 차는 냥차래요.", "Gemini": "고양이가 화나면 냥냥펀치를 날린대요."}
        script, grading = battle.build_script(item, answers)
        chats = [cut["visual"] for cut in script["cuts"] if cut["visual"]["type"] == "chat"]
        # 답은 고치지 않고 그대로 화면에
        self.assertEqual([chat["quote"] for chat in chats], [answers["Claude"], answers["Gemini"]])
        self.assertIsNone(grading["truth"])
        self.assertIn("댓글", script["cuts"][-1]["line"])
        self.assertEqual(script["series"], "AI 대결")

        checked = {**item, "check": {"type": "count", "text": "banana", "char": "a"}}
        script, grading = battle.build_script(checked, {"Claude": "3", "Gemini": "2"})
        self.assertEqual(grading["truth"], "3")
        self.assertTrue(any("클로드 승" in cut["line"] for cut in script["cuts"]))

    def test_pick_unused_battle(self):
        items = [{"id": "a"}, {"id": "b"}]
        self.assertEqual(battle.pick_battle(items, [{"link": "battle:a"}])["id"], "b")
        self.assertIsNone(battle.pick_battle(items, [{"link": "battle:a"}, {"link": "battle:b"}]))
        self.assertEqual(battle.pick_battle(items, [], "a")["id"], "a")

    def test_battle_list_is_valid(self):
        items = shorts.load_json(battle.BATTLES_FILE, [])
        self.assertGreaterEqual(len(items), 30)
        self.assertEqual(len({item["id"] for item in items}), len(items))
        for item in items:
            self.assertTrue(all(item.get(key) for key in ("id", "hook", "cover", "title", "prompt")), item)
            self.assertLessEqual(len(item["title"]), 40, item)


if __name__ == "__main__":
    unittest.main()
