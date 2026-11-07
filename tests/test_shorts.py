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

        issues = [("2026-11-03", issue)]

        # 주요 기사(top_stories) 안에서 AI 기사가 먼저
        picked = shorts.pick_article(issues, used_links=set())
        self.assertEqual(picked["link"], "llm")
        self.assertEqual(picked["issue_date"], "2026-11-03")

        # 주요 기사는 AI가 아니어도 나머지 상세 기사보다 먼저
        picked = shorts.pick_article(issues, used_links={"llm"})
        self.assertEqual(picked["link"], "dr")

        picked = shorts.pick_article(issues, used_links={"llm", "dr"})
        self.assertEqual(picked["link"], "claude")

        self.assertIsNone(shorts.pick_article(issues, used_links={"llm", "claude", "dr"}))

    def test_pick_article_uses_today_before_older_issues(self):
        # 전날 기사가 AI·고득점이어도 오늘 기사를 먼저 쓴다.
        older = {"top_stories": [make_article("LLM 대형 소식", 15, "old")]}
        newer = {"more_detailed": [make_article("DB 마이그레이션 사례", 9, "new")]}
        issues = [("2026-11-03", newer), ("2026-11-02", older)]

        self.assertEqual(shorts.pick_article(issues, used_links=set())["link"], "new")
        self.assertEqual(shorts.pick_article(issues, used_links={"new"})["link"], "old")

    def test_validate_script_cleans_hashtags(self):
        script = shorts.validate_script(
            {
                "title": "t",
                "description": "d",
                "hashtags": ["#AI 뉴스", "LLM", " "],
                "cuts": [{"line": "근데 진짜예요.", "emphasis": ["진짜예요.", "없는말"]} for _ in range(8)],
            }
        )
        self.assertEqual(script["hashtags"], ["AI뉴스", "LLM"])
        # 대사에 없는 강조 단어는 버리고, 그래픽이 없으면 none으로 채운다.
        self.assertEqual(script["cuts"][0]["emphasis"], ["진짜예요."])
        self.assertEqual(script["cuts"][0]["visual"], {"type": "none"})

    def test_validate_script_fixes_cover_and_tips(self):
        script = shorts.validate_script(
            {
                "title": "t",
                "cover": "첫 줄\\n둘째 줄",
                "summary": " 요약 ",
                "tips": [" 버전 확인 ", ""],
                "caution": "",
                "hashtags": [],
                "cuts": [{"line": "엔지니어 / 한 명당 / 병합 5배래요.", "emphasis": ["5배래요."]} for _ in range(8)],
            }
        )

        self.assertEqual(script["cover"], "첫 줄\n둘째 줄")
        self.assertEqual(script["tips"], ["버전 확인"])
        self.assertEqual(script["cuts"][0]["emphasis"], ["5배래요."])

    def test_spoken_line_and_caption_segments(self):
        cut = {"line": "엔지니어 / 한 명당 / 병합 5배래요."}

        self.assertEqual(shorts.spoken_line(cut), "엔지니어 한 명당 병합 5배래요.")
        self.assertEqual(shorts.caption_segments(cut), [1, 2, 2])
        self.assertIsNone(shorts.caption_segments({"line": "그냥 한 문장"}))

    def test_caption_chunks_follow_script_segments(self):
        words = [
            {"text": text, "startMs": i * 300, "endMs": i * 300 + 280}
            for i, text in enumerate(["엔지니어", "한", "명당", "병합", "5배래요."])
        ]
        chunks = shorts.caption_chunks(words, ["5배래요."], [1, 2, 2])

        self.assertEqual([c["text"] for c in chunks], ["엔지니어", "한 명당", "병합 5배래요"])
        self.assertEqual(chunks[1]["startMs"], 300)

        # 조각 표시가 단어 수와 안 맞으면 기존 방식으로 묶는다.
        fallback = shorts.caption_chunks(words, [], [1, 1])
        self.assertEqual([c["text"] for c in fallback], ["엔지니어 한", "명당 병합", "5배래요"])

    def test_build_description_includes_tips_and_recent_videos(self):
        script = {
            "title": "제목",
            "summary": "무슨 일인지 요약",
            "tips": ["버전 확인하기"],
            "caution": "토큰 과금 주의",
            "hashtags": ["AI"],
        }
        history = [{"title": "지난 영상", "video_id": "abc123"}]
        text = shorts.build_description(script, {"link": "https://example.com/a"}, history)

        self.assertIn("무슨 일인지 요약", text)
        self.assertIn("- 버전 확인하기", text)
        self.assertIn("토큰 과금 주의", text)
        self.assertIn("https://example.com/a", text)
        self.assertIn("https://youtu.be/abc123", text)
        self.assertIn("#shorts #AI", text)

    def test_build_description_starts_with_question_and_strips_invisible_chars(self):
        script = {
            "title": "제목",
            "question": "Revolut은 어떻게 AI 비용을 줄였나?",
            "summary": "요약​입니다",
            "hashtags": ["AI"],
        }
        text = shorts.build_description(script, {"link": "https://example.com/a"})

        self.assertTrue(text.startswith("Revolut은 어떻게 AI 비용을 줄였나?\n\n요약입니다"))
        self.assertNotIn("​", text)

    def test_pick_thumbnail_visual_prefers_metaphor_then_number(self):
        cuts = [{"visual": {"type": t}} for t in ["hook", "flow", "number", "metaphor", "keywords"]]
        self.assertEqual(shorts.pick_thumbnail_visual(cuts)["type"], "metaphor")

        no_metaphor = [cut for cut in cuts if cut["visual"]["type"] != "metaphor"]
        self.assertEqual(shorts.pick_thumbnail_visual(no_metaphor)["type"], "number")

        # 첫 컷(hook)만 있으면 그림 없이 제목만
        self.assertIsNone(shorts.pick_thumbnail_visual([{"visual": {"type": "hook"}}, {"visual": {"type": "none"}}]))

    def test_parse_probe_reads_ffmpeg_report(self):
        stderr = (
            "  Duration: 00:00:36.10, start: 0.000000, bitrate: 925 kb/s\n"
            "  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), "
            "1080x1920, 790 kb/s, 30 fps, 30 tbr, 15360 tbn (default)\n"
            "  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, stereo, fltp, 128 kb/s\n"
            "[silencedetect @ 0x1] silence_end: 12.5 | silence_duration: 3.1\n"
            "[Parsed_volumedetect_1 @ 0x2] mean_volume: -17.6 dB\n"
            "[Parsed_volumedetect_1 @ 0x2] max_volume: -1.8 dB\n"
        )
        report = shorts.parse_probe(stderr)

        self.assertEqual((report["width"], report["height"], report["fps"]), (1080, 1920, 30.0))
        self.assertAlmostEqual(report["duration"], 36.1)
        self.assertTrue(report["has_audio"])
        self.assertEqual((report["mean_volume"], report["max_volume"]), (-17.6, -1.8))
        self.assertEqual(report["silences"], [3.1])

    def test_find_video_problems(self):
        good = {"width": 1080, "height": 1920, "fps": 30.0, "duration": 36.1, "has_audio": True,
                "max_volume": -1.8, "mean_volume": -17.6, "silences": []}
        self.assertEqual(shorts.find_video_problems(good, [("제목", "정상 제목")]), [])

        bad = {**good, "width": 1920, "height": 1080, "duration": 8.0, "max_volume": -0.1, "silences": [3.1]}
        problems = shorts.find_video_problems(bad, [("제목", "깨진�제목")])

        self.assertEqual(len(problems), 5)
        self.assertIn("소리 트랙이 없습니다", shorts.find_video_problems({**good, "has_audio": False}))

    def test_validate_script_rejects_too_few_cuts(self):
        with self.assertRaises(ValueError):
            shorts.validate_script(
                {
                    "title": "t",
                    "description": "d",
                    "hashtags": [],
                    "cuts": [{"line": "하나", "emphasis": []}] * 3,
                }
            )

    def test_clean_text_removes_broken_characters(self):
        cleaned = shorts.clean_text({"cuts": [{"line": "아예 �뺐어요", "emphasis": ["�"]}], "n": 3})

        self.assertEqual(cleaned["cuts"][0]["line"], "아예 뺐어요")
        self.assertEqual(cleaned["cuts"][0]["emphasis"], [""])
        self.assertEqual(cleaned["n"], 3)

    def test_pick_sfx_only_on_hook_and_first_metaphor(self):
        cuts = [{"visual": {"type": t}} for t in ["hook", "number", "metaphor", "flow", "metaphor", "keywords"]]
        sfx = shorts.pick_sfx(cuts, [0, 40, 90, 130, 170, 210])

        self.assertEqual([effect["src"] for effect in sfx], ["sfx/impact.wav", "sfx/whoosh1.wav"])
        self.assertEqual(sfx[1]["from"], 87)
        self.assertEqual(len(shorts.pick_sfx(cuts[:2], [0, 40])), 1)

    def test_validate_visual_falls_back_when_empty(self):
        self.assertEqual(shorts.validate_visual(None), {"type": "none"})
        self.assertEqual(shorts.validate_visual({"type": "number", "value": "많이"}), {"type": "none"})
        self.assertEqual(shorts.validate_visual({"type": "flow", "items": ["하나"]}), {"type": "none"})
        self.assertEqual(shorts.validate_visual({"type": "unknown"}), {"type": "none"})
        # 비유 건물은 층이 2개 이상이어야 그린다.
        one_room = {"type": "metaphor", "rooms": [{"place": "소장실", "actual": "GLM"}, {"place": " ", "actual": "x"}]}
        self.assertEqual(shorts.validate_visual(one_room), {"type": "none"})
        two_rooms = {"type": "metaphor", "rooms": [{"place": "소장실", "actual": "GLM"}, {"place": "현장", "actual": "B200"}]}
        self.assertEqual(shorts.validate_visual(two_rooms), two_rooms)
        # 기호만 있는 키워드 카드는 뺀다.
        keywords = shorts.validate_visual({"type": "keywords", "items": ["배달앱", "=", "vs", "외부 API"]})
        self.assertEqual(keywords["items"], ["배달앱", "외부 API"])

        number = {"type": "number", "value": "0.016%", "label": "수정 비율"}
        self.assertEqual(shorts.validate_visual(number), number)

    def test_drop_duplicate_label_removes_repeated_caption(self):
        narration = "여러분 팀의 AI 사용량은 어떤가요?"

        same = shorts.drop_duplicate_label({"type": "question", "label": "여러분 팀의 AI 사용량은 어떤가요?"}, narration)
        self.assertEqual(same, {"type": "question"})

        short = {"type": "question", "label": "우리 팀은 몇 배?"}
        self.assertEqual(shorts.drop_duplicate_label(short, narration), short)

        # 긴 문장 속 일부 단어만 겹치는 건 중복이 아니다.
        partial = {"type": "number", "value": "250배", "label": "AI 사용량"}
        self.assertEqual(shorts.drop_duplicate_label(partial, narration), partial)

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

    def test_align_to_script_matches_heard_words(self):
        text = "Claude Code 확장이요. 근데 악성코드가 있었어요."
        heard = [
            {"text": "클로드", "startMs": 0, "endMs": 400},
            {"text": "코드", "startMs": 400, "endMs": 600},
            {"text": "확장이요.", "startMs": 600, "endMs": 1200},
            {"text": "근데", "startMs": 1500, "endMs": 1700},
            {"text": "악성", "startMs": 1700, "endMs": 2000},
            {"text": "코드가", "startMs": 2000, "endMs": 2400},
            {"text": "있었어요.", "startMs": 2400, "endMs": 3000},
        ]
        words = shorts.align_to_script(text, heard, 3200)

        self.assertEqual([w["text"] for w in words], text.split())
        # 표기가 다른 영어 어절은 다음 어절 시작 전까지로 채운다.
        self.assertEqual(words[0]["startMs"], 0)
        self.assertLessEqual(words[1]["endMs"], words[2]["startMs"])
        self.assertEqual(words[3]["startMs"], 1500)
        self.assertEqual((words[4]["startMs"], words[4]["endMs"]), (1700, 2400))
        starts = [w["startMs"] for w in words]
        self.assertEqual(starts, sorted(starts))

    def test_caption_chunks_groups_short_pieces(self):
        words = [
            {"text": "심지어", "startMs": 0, "endMs": 300},
            {"text": "확장", "startMs": 300, "endMs": 500},
            {"text": "지워도", "startMs": 500, "endMs": 800},
            {"text": "안", "startMs": 800, "endMs": 900},
            {"text": "끝나요.", "startMs": 900, "endMs": 1300},
        ]
        chunks = shorts.caption_chunks(words, ["끝나요."])

        self.assertEqual([c["text"] for c in chunks], ["심지어 확장", "지워도 안", "끝나요"])
        self.assertEqual([c["emphasis"] for c in chunks], [False, False, True])
        self.assertEqual(chunks[1]["startMs"], 500)

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
