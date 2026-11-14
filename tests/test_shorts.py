import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

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

    def test_generate_script_falls_back_to_gemini_when_claude_is_limited(self):
        from unittest import mock

        cuts = [{"line": f"대사 {i}", "emphasis": [], "visual": {"type": "none"}} for i in range(8)]
        gemini_script = {"title": "제미나이", "question": "", "cover": "c", "summary": "", "tips": [], "caution": "", "hashtags": [], "cuts": cuts}

        def limited(*args, **kwargs):
            raise RuntimeError("You've hit your 5-hour limit")

        def fake_gemini(system, prompt, schema):
            if system is shorts.FACTCHECK_SYSTEM_PROMPT:
                return {"script": {**gemini_script, "title": "제미나이 검증"}, "changes": []}
            return gemini_script

        with mock.patch.object(shorts, "fetch_source_text", return_value="원문"), \
                mock.patch.object(shorts, "claude_json", side_effect=limited), \
                mock.patch.object(shorts, "gemini_json", side_effect=fake_gemini) as gemini:
            script = shorts.generate_script({"title": "t", "link": "l"})

        # Gemini로 쓰고, Claude 팩트체크가 막혀 Gemini로 팩트체크까지 한다
        self.assertEqual(script["title"], "제미나이 검증")
        self.assertEqual(gemini.call_count, 2)

    def test_speech_coverage_detects_cut_off_narration(self):
        text = "에이전트가 어제 한 실수 또 하죠 검색만 쓰면 53%였는데요 위키를 더하니 최대 61%예요"
        full = [{"text": word} for word in text.split()]
        cut = full[:5]

        self.assertGreater(shorts.speech_coverage(text, full), 0.95)
        self.assertLess(shorts.speech_coverage(text, cut), 0.5)

    def test_page_text_keeps_article_body_only(self):
        html = (
            "<html><body><nav>메뉴</nav><article><h1>제목</h1><p>본문 <b>굵게</b> 이어짐</p>"
            "<script>x()</script><li>항목</li></article><footer>꼬리말</footer></body></html>"
        )
        self.assertEqual(shorts.page_text(html), "제목\n본문 굵게 이어짐\n항목")

    def test_build_script_prompt_includes_source_and_angle(self):
        article = {"title": "t", "one_line": "o", "key_points": ["k"], "company": "c", "link": "l"}
        prompt = shorts.build_script_prompt(article, "원문 내용", "숫자 중심")

        self.assertIn("<<<원문\n원문 내용\n원문>>>", prompt)
        self.assertIn("이번 대본의 각도: 숫자 중심", prompt)
        self.assertNotIn("원문>>>", shorts.build_script_prompt(article))

    def test_generate_script_picks_judged_candidate_and_falls_back(self):
        from unittest import mock

        def fake_script(tag):
            cuts = [{"line": f"{tag} 대사 {i}", "emphasis": [], "visual": {"type": "none"}} for i in range(8)]
            return {"title": tag, "question": "", "cover": tag, "summary": "", "tips": [], "caution": "", "hashtags": [], "cuts": cuts}

        calls = []

        def fake_claude(system, prompt, schema, model=None):
            calls.append(system)
            if system is shorts.JUDGE_SYSTEM_PROMPT:
                return {"scores": [], "best": 1, "reason": "두 번째가 정확함"}
            if system is shorts.FACTCHECK_SYSTEM_PROMPT:
                raise RuntimeError("사용량 한도")
            return fake_script("후보" + str(len(calls)))

        def bad_gemini(system, prompt, schema):
            return {"script": {**fake_script("짧음"), "cuts": fake_script("짧음")["cuts"][:2]}, "changes": []}

        with mock.patch.object(shorts, "fetch_source_text", return_value="원문"), \
                mock.patch.object(shorts, "claude_json", side_effect=fake_claude), \
                mock.patch.object(shorts, "gemini_json", side_effect=bad_gemini):
            with self.assertRaises(shorts.FactCheckFailed):
                shorts.generate_script({"title": "t", "link": "l"})

        # 후보 3개 + 심사 + (실패한) Claude 검증 = 5번 호출. Gemini 검증도 컷 2개라 실패 → 업로드 안 함
        self.assertEqual(len(calls), 5)

    def test_main_skips_article_when_factcheck_fails(self):
        from unittest import mock

        articles = [{"title": f"기사{i}", "link": f"https://a/{i}", "issue_date": "2026-11-14"} for i in range(3)]
        picked = []

        def fake_pick(issues, used):
            article = next(a for a in articles if a["link"] not in used)
            picked.append(article["link"])
            return article

        saved = {}
        with mock.patch("sys.argv", ["shorts.py", "--date", "2026-11-14"]), \
                mock.patch.object(shorts, "load_json", return_value=[]), \
                mock.patch.object(shorts, "load_issue", return_value={}), \
                mock.patch.object(shorts, "pick_article", side_effect=fake_pick), \
                mock.patch.object(shorts, "generate_script", side_effect=shorts.FactCheckFailed("컷 수가 이상합니다: 2")), \
                mock.patch.object(shorts, "notify_slack") as slack, \
                mock.patch.object(shorts, "save_json", side_effect=lambda path, data: saved.update({path: list(data)})), \
                mock.patch.object(shorts, "synthesize_narration") as tts, \
                mock.patch("os.makedirs"):
            shorts.main()

        # 기사 2개를 시도하고 둘 다 건너뜀: 영상 제작·업로드 없음, 다음 실행에서 다시 고르지 않게 기록
        self.assertEqual(picked, ["https://a/0", "https://a/1"])
        tts.assert_not_called()
        self.assertEqual(slack.call_count, 2)
        history = saved[shorts.SHORTS_HISTORY_FILE]
        self.assertEqual([entry["skipped"] for entry in history], ["factcheck", "factcheck"])
        self.assertTrue(all("video_id" not in entry for entry in history))

    def test_script_style_and_prompt(self):
        from unittest import mock

        cuts = [{"line": f"대사 {i}", "emphasis": [], "visual": {"type": "none"}} for i in range(8)]
        script = {"title": "t", "question": "", "cover": "c", "summary": "", "tips": [], "caution": "", "hashtags": [], "cuts": cuts}

        # 대본에 style이 없거나 이상하면 news
        self.assertEqual(shorts.validate_script({**script, "style": "weird"})["style"], "news")
        self.assertEqual(shorts.validate_script({**script, "style": "explain"})["style"], "explain")

        with mock.patch.object(shorts, "SHORTS_STYLE", "auto"):
            self.assertEqual(shorts.script_style({"style": "explain"}), "explain")
            self.assertEqual(shorts.script_style({}), "news")
            self.assertIn("화면 스타일 (style", shorts.script_system_prompt())
        with mock.patch.object(shorts, "SHORTS_STYLE", "explain"):
            self.assertEqual(shorts.script_style({"style": "news"}), "explain")
        with mock.patch.object(shorts, "SHORTS_STYLE", "classic"):
            self.assertEqual(shorts.script_style({"style": "news"}), "classic")
            self.assertNotIn("화면 스타일 (style", shorts.script_system_prompt())

    def test_code_visual_highlight_is_kept_only_in_range(self):
        code = "fn a() {\n  errdefer free(x);\n}"
        self.assertEqual(shorts.validate_visual({"type": "code", "code": code, "highlight": 2})["highlight"], 2)
        self.assertNotIn("highlight", shorts.validate_visual({"type": "code", "code": code, "highlight": 0}))
        self.assertNotIn("highlight", shorts.validate_visual({"type": "code", "code": code, "highlight": 9}))
        long_code = "\n".join(f"line {i}" for i in range(12))
        self.assertEqual(len(shorts.validate_visual({"type": "code", "code": long_code})["code"].split("\n")), 8)

    def test_fill_empty_cuts_uses_spoken_emphasis_only(self):
        cuts = [{"line": "대사" * (i + 1), "emphasis": [f"단어{i}"] if i % 2 else [], "visual": {"type": "none"}} for i in range(10)]
        cuts[0]["visual"] = {"type": "hook"}
        shorts.fill_empty_cuts(cuts, limit=3)
        empty = [c for c in cuts if c["visual"]["type"] in ("none", "hook")]
        # 강조 단어가 있는 컷(1,3,5,7)만 바뀐다. 마지막 2컷(8,9)과 첫 컷은 그대로
        self.assertEqual([i for i, c in enumerate(cuts) if c["visual"]["type"] == "keywords"], [1, 3, 5, 7])
        self.assertEqual(cuts[7]["visual"]["items"], ["단어7"])
        self.assertEqual(len(empty), 6)
        self.assertEqual(cuts[9]["visual"]["type"], "none")

    def test_youtube_safe_metadata(self):
        self.assertEqual(shorts.youtube_safe("A -> B, <폴더> 접근"), "A → B, ‹폴더› 접근")
        self.assertEqual(shorts.cut_bytes("가나다", 7), "가나")
        self.assertEqual(len(shorts.cut_bytes("가" * 3000, 5000).encode("utf-8")), 4998)
        cuts = [{"line": f"대사 {i}", "emphasis": [], "visual": {"type": "none"}} for i in range(8)]
        script = {"title": "t", "question": "", "summary": "a->b <x>", "tips": [], "caution": "", "hashtags": [], "cuts": cuts}
        description = shorts.build_description(script, {"link": "https://x"})
        self.assertNotIn("<", description)
        self.assertNotIn(">", description)

    def test_validate_visual_new_motion_types(self):
        diagram = {"type": "diagram", "nodes": [{"label": "사용자", "icon": "person"}, {"label": "서버", "icon": "server"}], "focus": 1}
        self.assertEqual(shorts.validate_visual(diagram), diagram)
        self.assertEqual(shorts.validate_visual({"type": "diagram", "nodes": [{"label": "하나", "icon": "server"}]}), {"type": "none"})

        pair = {"type": "beforeafter", "before": {"title": "외부", "value": "$3", "icon": "cloud"}, "after": {"title": "자체", "value": "$0.3", "icon": "server"}}
        self.assertEqual(shorts.validate_visual(pair)["type"], "beforeafter")
        self.assertEqual(shorts.validate_visual({**pair, "after": {"title": "자체", "value": "", "icon": "server"}}), {"type": "none"})

        self.assertEqual(shorts.validate_visual({"type": "scale", "count": 56, "icon": "gpu", "value": "B200 56개"})["type"], "scale")
        self.assertEqual(shorts.validate_visual({"type": "scale", "count": 1, "value": "1개"}), {"type": "none"})
        self.assertEqual(shorts.validate_visual({"type": "quote", "quote": "토큰 제한을 **없앴다**"})["type"], "quote")
        self.assertEqual(shorts.validate_visual({"type": "quote", "quote": "짧음"}), {"type": "none"})

    def test_speakable_numbers_drops_trailing_decimal_zeros(self):
        self.assertEqual(shorts.speakable_numbers("100만 토큰당 / 0.30달러예요."), "100만 토큰당 / 0.3달러예요.")
        self.assertEqual(shorts.speakable_numbers("2.0배, 1.50%, 10.25초"), "2배, 1.5%, 10.25초")
        self.assertEqual(shorts.speakable_numbers("1,000~10,000달러, 버전 3.10"), "1,000~10,000달러, 버전 3.1")

    def test_drop_meta_talk_removes_out_of_script_remarks(self):
        script = {
            "caution": "GPU 비용은 기사에 없으니 직접 따져보세요.",
            "summary": "요약",
            "tips": ["단가 계산하기", "원문엔 안 나와요"],
            "cuts": [{"line": "솔직히 / GPU 값은 / 기사에 없어요."}, {"line": "B200 / 56개예요."}],
        }
        cleaned = shorts.drop_meta_talk(script)

        self.assertEqual([cut["line"] for cut in cleaned["cuts"]], ["B200 / 56개예요."])
        self.assertEqual(cleaned["caution"], "")
        self.assertEqual(cleaned["summary"], "요약")
        self.assertEqual(cleaned["tips"], ["단가 계산하기"])

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

    def test_pick_scene3d_desk3d_for_agent_token_coding_topics(self):
        def script(cover, *lines):
            return {"cover": cover, "cuts": [{"line": line} for line in lines]}

        # 제목에 주제어가 있으면 3D 책상 장면
        self.assertEqual(shorts.pick_scene3d(script("코드 에이전트 토큰\n77% 절감", "주석만 지웠어요")), "desk3d")
        self.assertEqual(shorts.pick_scene3d(script("Claude Code 새 기능", "써 봤어요")), "desk3d")
        # 대사에 두 번 이상 나와도 3D
        self.assertEqual(shorts.pick_scene3d(script("확 줄었다", "토큰을 덜 써요", "토큰 / 절반이요")), "desk3d")
        # 한 번 스치는 정도, 관계없는 주제는 기본 배경
        self.assertEqual(shorts.pick_scene3d(script("새 폰 색깔", "에이전트도 돌린대요")), None)
        self.assertEqual(shorts.pick_scene3d(script("idea 공유 기능 정책", "slideshow 정리")), None)

    def test_pick_scene3d_picks_topic_scene(self):
        def script(cover, *lines):
            return {"cover": cover, "cuts": [{"line": line} for line in lines]}

        with mock.patch.object(shorts, "scene3d_ready", return_value=True):
            # 장면마다 제목 주제어 하나로 고른다
            self.assertEqual(shorts.pick_scene3d(script("확장에 백도어 발견", "지우세요")), "vault3d")
            self.assertEqual(shorts.pick_scene3d(script("DMARC 없는 메일 거부", "레코드 한 줄")), "vault3d")
            self.assertEqual(shorts.pick_scene3d(script("LLM 비용 77% 절감", "모델을 섞었어요")), "coins3d")
            self.assertEqual(shorts.pick_scene3d(script("EC2 용량 미리 확인", "안 뜰 수 있어요")), "server3d")
            self.assertEqual(shorts.pick_scene3d(script("RAM 70%↓ 재구축", "가벼워졌어요")), "server3d")
            self.assertEqual(shorts.pick_scene3d(script("MaxxBench 점수 추락", "74%가 53%로")), "lab3d")
            self.assertEqual(shorts.pick_scene3d(script("가중치 0.016%만 고쳤다", "그런데요")), "lab3d")
            self.assertEqual(shorts.pick_scene3d(script("Postgres 인덱스 하나로", "쿼리가 빨라졌어요")), "data3d")
            self.assertEqual(shorts.pick_scene3d(script("Chrome에 JPEG XL 지원", "브라우저가 바뀝니다")), "web3d")
            self.assertEqual(shorts.pick_scene3d(script("핵심 오픈소스 23개 중 11개, 1~2명이 운영", "메인테이너가 지쳐요")), "repo3d")
            self.assertEqual(shorts.pick_scene3d(script("Claude Opus 5.5 출시", "새 모델이 나왔어요")), "launch3d")
            # 넓은 말(출시·공개)은 더 구체적인 장면에 진다, '퇴출시킨'은 출시가 아니다
            self.assertEqual(shorts.pick_scene3d(script("DuckDB 2.0 출시")), "data3d")
            self.assertEqual(shorts.pick_scene3d(script("Tor 출구 노드 300개를 퇴출시킨 과정")), None)
            self.assertEqual(shorts.pick_scene3d(script("Epic 대 Apple 소송, 호주 법원 판결")), "law3d")
            self.assertEqual(shorts.pick_scene3d(script("DeepX 2세대 AI 칩 테이프아웃", "5W로 돌아요")), "chip3d")
            self.assertEqual(shorts.pick_scene3d(script("Firebase SDK로 iOS 앱이 충돌")), "phone3d")
            self.assertEqual(shorts.pick_scene3d(script("AI 코딩으로 병목이 된 CI", "배포가 밀려요")), "deploy3d")
            # '하는 법'은 법이 아니고, '스크롤백'은 롤백이 아니고, 'Copilot app'은 모바일 앱이 아니다
            self.assertEqual(shorts.pick_scene3d(script("Git 작업 큐로 푸는 법")), "repo3d")
            self.assertEqual(shorts.pick_scene3d(script("Ghostty 1.4.0 스크롤백 압축")), None)
            self.assertEqual(shorts.pick_scene3d(script("Copilot 앱에서 세션 이어 하기")), "desk3d")
            self.assertEqual(shorts.pick_scene3d(script("Qwen-Image-2.1, 소형 이미지 생성 모델")), "media3d")
            self.assertEqual(shorts.pick_scene3d(script("Kagi Search, 가입 없이 무료 검색")), "search3d")
            self.assertEqual(shorts.pick_scene3d(script("Anthropic, 나스닥 상장 신청")), "invest3d")
            self.assertEqual(shorts.pick_scene3d(script("Linux 커널 스케줄링 개선")), "terminal3d")
            # '[영상]'은 발표 영상 표시, '인수인계'는 인수가 아니다
            self.assertEqual(shorts.pick_scene3d(script("Rails World 2026 개막 기조연설 [영상]")), None)
            self.assertEqual(shorts.pick_scene3d(script("AI 챗 간 인수인계 확장")), None)
            self.assertEqual(shorts.pick_scene3d(script("텔레그램 채팅 봇 공개")), "chat3d")
            self.assertEqual(shorts.pick_scene3d(script("1시간 오디오를 13초에 전사")), "voice3d")
            self.assertEqual(shorts.pick_scene3d(script("GPT-6 Astra, 실제 자동차를 운전")), "robot3d")
            # AI 일반(ai3d)은 다른 장면이 하나도 안 맞을 때만
            self.assertEqual(shorts.pick_scene3d(script("LLM이 소프트웨어 정형 검증을 가능하게")), "ai3d")
            self.assertEqual(shorts.pick_scene3d(script("OpenAI는 자체 LLM으로 칩을 어떻게 설계했나")), "chip3d")
            self.assertEqual(shorts.pick_scene3d(script("Rust 컴파일러 속도를 높이는 방법")), "lang3d")
            self.assertEqual(shorts.pick_scene3d(script("AI 시대 주니어 개발자의 역할")), "work3d")
            self.assertEqual(shorts.pick_scene3d(script("PS2 게임을 재컴파일하기")), "game3d")
            self.assertEqual(shorts.pick_scene3d(script("Terence Tao: 수학 2.0")), "math3d")
            self.assertEqual(shorts.pick_scene3d(script("Let's Encrypt 인증서 검증 지점 추가")), "vault3d")
            self.assertEqual(shorts.pick_scene3d(script("FreeDNS - 무료 DNS 호스팅")), "server3d")
            # '언어 모델'은 프로그래밍 언어가 아니다 → AI 일반
            self.assertEqual(shorts.pick_scene3d(script("gzip도 언어 모델이 될 수 있을까?")), "ai3d")
            # 대사에 두 번 이상 나오면 제목에 없어도 고른다, 한 번은 아니다
            self.assertEqual(shorts.pick_scene3d(script("이거 아세요?", "백도어가 있었어요", "공급망 공격이죠")), "vault3d")
            self.assertEqual(shorts.pick_scene3d(script("이거 아세요?", "서버 한 대로요")), None)
            # 여러 장면이 걸리면 가장 많이 맞는 장면
            self.assertEqual(shorts.pick_scene3d(script("AI 에이전트 비용, 토큰값만 보면 손해인 이유?")), "coins3d")
            self.assertEqual(shorts.pick_scene3d(script("코딩 에이전트 TODO 주석 방해, 토큰 77% 낭비")), "desk3d")
            self.assertEqual(shorts.pick_scene3d(script("에이전트 메모리, 질문당 2만 토큰 절약")), "desk3d")
            # 점수가 같으면 더 구체적인 장면 (책상보다 보안)
            self.assertEqual(shorts.pick_scene3d(script("확장 지워도 백도어가 남는다고? Cursor 사고")), "vault3d")

    def test_pick_scene3d_past_titles(self):
        """지난 영상 제목만으로 고른 장면 (대사가 더해지면 바뀔 수 있다). 엉뚱한 장면이 고르지 않는지 확인."""
        expected = {
            "확장 지워도 백도어가 남는다고? Cursor 사고": "vault3d",
            "GitBook이 AI 에이전트에 뚫렸다고? 토큰 점검하세요": "vault3d",
            "Claude Code가 내 이메일을 외부 사이트에 보낸다고?": "vault3d",
            "TUI Amazon Bedrock 위협 모델링 자동화, 컨텍스트 효율 94%": "vault3d",
            "Outlook.com DMARC 없는 도메인 메일 거부, 레코드 한 줄로 해결": "vault3d",
            "AI 사용료가 직원 보수보다 커졌다고?": "coins3d",
            "AI 에이전트 비용, 토큰값만 보면 손해인 이유?": "coins3d",
            "AI 비용 90% 줄인 Revolut, 대체 뭘 했길래?": "coins3d",
            "Jev·Opus 하이브리드 워크플로, LLM 비용 77% 절감": "coins3d",
            "Gemini Omni 1.2 Flash, 최대 15초 영상·API 30% 인하": "coins3d",
            "스케일업했는데 서버가 안 뜬다면? EC2 용량 미리 확인": "server3d",
            "Entire 분산 Git 네트워크 공개, 최대 25배 성능": "server3d",
            "Discord Rust GPUI 재구축, 1GB 대비 RAM 약 70%↓": "server3d",
            "학습 없이 가중치 0.016%만 고쳤더니 성능이 올랐다?": "lab3d",
            "GPT-6 Astra 안전 연구 성능 40% 낮아, 몰래 봐주기?": "lab3d",
            "MaxxBench, DeepSWE 약 74% 모델이 53.4%로 추락": "lab3d",
            "AI가 코드 짜는데 프레임워크가 왜 중요할까?": "desk3d",
            "AI 에이전트가 틀린 답 내놓는 진짜 이유?": "desk3d",
            "MCP, AI가 도구를 직접 호출하는 게 아니라고?": "desk3d",
            "코딩 에이전트 TODO 주석 방해, 토큰 77% 낭비": "desk3d",
            "Anthropic 에이전트 메모리, 드리밍으로 질문당 약 2만 토큰 절약": "desk3d",
            "Claude Code·Codex 두뇌 과부하, Git 작업 큐로 푸는 법": "desk3d",
            "AI한테 SQL 대신 지표만 쥐여주면 생기는 일?": "data3d",
            "Stripe 에이전트 연동, SQL 없이 매출 분석·투자자 슬라이드까지": "data3d",
            "내 사이트에 AI 비서가 몰려오는데, 보고 계세요?": "web3d",
            "LLM 확장형 웹 앱, 샌드박스·권한 객체로 안전하게": "web3d",
            "SQLite 오픈소스 외부 기여 금지, AI 시대 유지보수 전략": "repo3d",
            "Replit microVM 샌드박스 재구축, 커널 공유 끊었다": "terminal3d",
            "worklog-system 주간보고 자동화, Slack·Jira·AI 연동 후기": "work3d",
            "뱅크샐러드 망분리 n8n AX, 인당 매일 30분~1시간 절약": "work3d",
            "Zed Delta 공개 베타, PR 끄고 33명이 570건 반영": "launch3d",
            "광고를 AI한테 물어보게 만든 당근, 어떻게 했을까?": None,
        }
        with mock.patch.object(shorts, "scene3d_ready", return_value=True):
            for title, scene in expected.items():
                with self.subTest(title=title):
                    self.assertEqual(shorts.pick_scene3d({"cover": title, "cuts": []}), scene)

    def test_pick_scene3d_skips_scene_without_file(self):
        script = {"cover": "MaxxBench 점수 추락", "cuts": []}

        with mock.patch.object(shorts, "scene3d_ready", side_effect=lambda scene: scene != "lab3d"):
            self.assertEqual(shorts.pick_scene3d(script), None)

    def test_scene3d_files_exist_and_match_remotion(self):
        # Blender 스크립트가 있는 장면은 루프 파일도 함께 있어야 하고(책상 장면은 늘),
        # Remotion 쪽 배경 목록(schema.ts, Background.tsx)과 이름이 같아야 한다
        video = Path(__file__).resolve().parent.parent / "video"
        self.assertTrue(shorts.scene3d_ready("desk3d"))
        for scene, filename in shorts.SCENE3D_FILES.items():
            script = video / "assets3d" / "scripts" / filename.replace("_loop.webm", ".py")
            if script.exists():
                with self.subTest(scene=scene):
                    self.assertTrue(shorts.scene3d_ready(scene), filename)
        root = video / "src"
        schema = (root / "schema.ts").read_text(encoding="utf-8")
        background = (root / "Background.tsx").read_text(encoding="utf-8")
        for scene, filename in shorts.SCENE3D_FILES.items():
            self.assertIn(f'"{scene}"', schema)
            self.assertIn(f'{scene}: "assets3d/{filename}"', background)

    def test_scene3d_goes_to_a_cut_not_the_backdrop(self):
        def cut(kind="none", **extra):
            return {"line": "대사", "visual": {"type": kind, **extra}}

        script = {"cover": "확장에 백도어 발견", "cuts": [cut("hook"), cut("number", value="3"), cut(), cut(), cut(), cut("question")]}
        script["cuts"][3]["line"] = "확장을 지워도 백도어는 남아 있었어요"

        # 배역 이름표 파일이 없는 장면 (예전 방식: 자동으로 장면만 띄운다)
        with mock.patch.object(shorts, "scene3d_ready", return_value=True), mock.patch.object(shorts, "scene3d_anchors", return_value={}):
            # 기본은 배경에 깔지 않는다
            self.assertEqual(shorts.pick_backdrop(script), "glow")
            # 자막만 있는 컷 중 대사가 가장 긴 컷에 장면을 띄운다 (끝 쪽 컷은 제외)
            shorts.add_scene3d_cut(script)
            self.assertEqual(script["cuts"][3]["visual"], {"type": "scene3d", "scene": "vault3d"})
            self.assertEqual(script["cuts"][2]["visual"]["type"], "none")

            # 대본이 이미 썼으면 그대로 두되, 붙어 있는 컷 연달아와 세 번째부터는 지운다
            written = {"cover": "x", "cuts": [cut("hook"), cut("scene3d", scene="coins3d"), cut("scene3d", scene="lab3d"),
                                              cut("scene3d", scene="deploy3d"), cut(), cut("scene3d", scene="web3d"), cut()]}
            shorts.add_scene3d_cut(written)
            self.assertEqual(written["cuts"][1]["visual"]["scene"], "coins3d")
            self.assertEqual(written["cuts"][2]["visual"], {"type": "none"})
            self.assertEqual(written["cuts"][3]["visual"]["scene"], "deploy3d")
            self.assertEqual(written["cuts"][5]["visual"], {"type": "none"})

            # 주제가 맞지 않으면 넣지 않는다
            plain = {"cover": "광고를 AI한테 물어보게 만든 당근", "cuts": [cut("hook"), cut(), cut(), cut()]}
            shorts.add_scene3d_cut(plain)
            self.assertNotIn("scene3d", [c["visual"]["type"] for c in plain["cuts"]])

    def test_scene3d_with_anchors_is_never_auto_inserted(self):
        # 배역 이름표가 있는 장면은 대본이 쓴 beats가 있어야 한다 → 자동 삽입(beats 없음)은 하지 않는다
        def cut(kind="none"):
            return {"line": "확장을 지워도 백도어는 남아 있었어요", "visual": {"type": kind}}

        script = {"cover": "확장에 백도어 발견", "cuts": [cut("hook"), cut(), cut(), cut(), cut("question")]}
        with mock.patch.object(shorts, "scene3d_ready", return_value=True),                 mock.patch.object(shorts, "scene3d_anchors", return_value={"red": "빨간 꼬마"}):
            shorts.add_scene3d_cut(script)
        self.assertNotIn("scene3d", [c["visual"]["type"] for c in script["cuts"]])

    def test_validate_visual_scene3d_beats(self):
        anchors = {"red": "빨간 꼬마", "door": "금고 문", "lock": "자물쇠"}
        with mock.patch.object(shorts, "scene3d_ready", return_value=True),                 mock.patch.object(shorts, "scene3d_anchors", return_value=anchors):
            visual = shorts.validate_visual({
                "type": "scene3d", "scene": "vault3d", "label": "백도어",
                "beats": [
                    {"target": "red", "label": " 공격자 "},
                    {"target": "moon", "label": "없는 배역"},
                    {"target": "door", "label": "열두 글자를 훌쩍 넘는 아주 긴 이름표"},
                    {"target": "red", "label": "같은 대상 두 번"},
                    {"target": "lock", "label": "원격 접속"},
                ],
            })
            self.assertEqual(visual["beats"], [{"target": "red", "label": "공격자"}, {"target": "lock", "label": "원격 접속"}])
            # 배역 이야기가 있으면 장면 위 문구는 뺀다
            self.assertNotIn("label", visual)
            # 쓸 수 있는 배역이 없으면 꼬마만 돌아다니는 그림이 되므로 넣지 않는다
            self.assertEqual(shorts.validate_visual({"type": "scene3d", "scene": "vault3d"}), {"type": "none"})
            self.assertEqual(shorts.validate_visual({"type": "scene3d", "scene": "vault3d", "beats": [{"target": "x", "label": "y"}]}), {"type": "none"})

        # 이름표 파일이 없는 장면은 예전처럼 장면만 (beats는 버린다)
        with mock.patch.object(shorts, "scene3d_ready", return_value=True),                 mock.patch.object(shorts, "scene3d_anchors", return_value={}):
            visual = shorts.validate_visual({"type": "scene3d", "scene": "coins3d", "beats": [{"target": "a", "label": "b"}]})
            self.assertEqual(visual, {"type": "scene3d", "scene": "coins3d"})

    def test_vault3d_anchor_file_lists_roles(self):
        from unittest import mock

        # 저장소에 들어 있는 금고 장면 이름표: 사물과 꼬마 4색
        anchors = shorts.scene3d_anchors("vault3d")
        for key in ("door", "shield", "lock", "red", "blue", "yellow", "white"):
            self.assertIn(key, anchors)
        # 3D 배역은 예전 화면(classic)에서만 대본 요청에 붙는다
        with mock.patch.object(shorts, "SHORTS_STYLE", "classic"):
            prompt = shorts.build_script_prompt({"title": "Cursor 확장에 백도어", "one_line": "악성 코드", "key_points": [], "topics": []})
        self.assertIn("3D 장면 배역", prompt)
        self.assertIn("- vault3d", prompt)
        self.assertIn("  - door:", prompt)

    def test_every_scene3d_has_anchor_roles(self):
        # 25개 장면 모두 배역 이름표 파일이 있어야 한다 (꼬마만 돌아다니는 장면이 남지 않게)
        for scene in shorts.SCENE3D_FILES:
            anchors = shorts.scene3d_anchors(scene)
            self.assertGreaterEqual(len(anchors), 4, scene)
            self.assertTrue(all(desc.strip() for desc in anchors.values()), scene)

    def test_validate_visual_scene3d_needs_known_scene(self):
        with mock.patch.object(shorts, "scene3d_ready", return_value=True), mock.patch.object(shorts, "scene3d_anchors", return_value={}):
            self.assertEqual(shorts.validate_visual({"type": "scene3d", "scene": "server3d"})["scene"], "server3d")
            self.assertEqual(shorts.validate_visual({"type": "scene3d", "scene": "moon3d"}), {"type": "none"})
            self.assertEqual(shorts.validate_visual({"type": "scene3d"}), {"type": "none"})

    def test_pick_backdrop_respects_explicit_setting_and_off_switch(self):
        script = {"cover": "에이전트 토큰 절감", "cuts": [{"line": "에이전트"}]}
        original = (shorts.SHORTS_BACKDROP, shorts.DESK3D_AUTO)

        try:
            shorts.SHORTS_BACKDROP, shorts.DESK3D_AUTO = "type", True
            self.assertEqual(shorts.pick_backdrop(script), "type")
            shorts.SHORTS_BACKDROP, shorts.DESK3D_AUTO = "glow", False
            self.assertEqual(shorts.pick_backdrop(script), "glow")
        finally:
            shorts.SHORTS_BACKDROP, shorts.DESK3D_AUTO = original


    def test_next_publish_slot_takes_earliest_free_slot(self):
        kst = shorts.KST
        original = shorts.PUBLISH_SLOTS

        try:
            shorts.PUBLISH_SLOTS = [7, 8, 12, 13, 17, 18]
            now = datetime(2026, 11, 11, 4, 0, tzinfo=kst)
            self.assertEqual(shorts.next_publish_slot([], now), datetime(2026, 11, 11, 7, tzinfo=kst))

            # 이미 예약된 시각은 건너뛴다
            history = [{"publish_at": datetime(2026, 11, 11, 7, tzinfo=kst).isoformat()}]
            self.assertEqual(shorts.next_publish_slot(history, now), datetime(2026, 11, 11, 8, tzinfo=kst))

            # 늦게 시작해 7시가 20분도 안 남았으면 다음 시각
            late = datetime(2026, 11, 11, 6, 50, tzinfo=kst)
            self.assertEqual(shorts.next_publish_slot([], late), datetime(2026, 11, 11, 8, tzinfo=kst))

            # 오늘 시각을 다 썼으면 내일 첫 시각
            evening = datetime(2026, 11, 11, 18, 30, tzinfo=kst)
            self.assertEqual(shorts.next_publish_slot([], evening), datetime(2026, 11, 12, 7, tzinfo=kst))

            shorts.PUBLISH_SLOTS = []
            self.assertIsNone(shorts.next_publish_slot([], now))
        finally:
            shorts.PUBLISH_SLOTS = original

if __name__ == "__main__":
    unittest.main()
