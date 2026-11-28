"""AI 대결 쇼츠: 같은 문제를 Claude와 Gemini에게 실제로 던지고, 받은 답을 그대로 나란히 보여 준다.

11/28 조사(국내 IT 채널 상위 100곳): 뉴스형 AI 쇼츠는 구독자 대비 조회수가 가장 낮고,
"GPT vs 심심이 끝말잇기 대결"(타임리스, 쇼츠 중앙값이 구독자의 1.9배)처럼 AI를 직접 시켜 본 영상이 잘 퍼진다.

사실 규칙: 화면·대사의 답은 두 AI가 실제로 한 답 그대로다 (지어내지 않는다). 승패는 정답이 있는 문제만 코드가 채점하고,
정답이 없는 문제는 시청자에게 댓글로 묻는다. 문제 목록은 config/battles.json, 기록은 shorts_history.json에 link "battle:<id>".
"""

import argparse
import os
import re
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

import shorts

BATTLES_FILE = "config/battles.json"
OUTPUT_DIR = "runtime/battle"
ANSWER_MAX = 70  # 답 하나가 이보다 길면 잘라서 "…" (읽는 데 7초 안쪽)
CLAUDE_LABEL = "Claude"
GEMINI_LABEL = "Gemini"

ANSWER_SYSTEM = (
    "너는 쇼츠 영상에 나오는 AI 대결 참가자다. 한국어로 답한다. 반드시 70자 이내, 한두 문장.\n"
    "이모지·마크다운·따옴표 꾸밈 없이 답만 쓴다. 문제에서 숫자로만 답하라고 하면 숫자만 쓴다."
)
ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


def clean_answer(text):
    text = re.sub(r"[*_`#>]+", "", text or "")
    text = re.sub(r"[\U0001F000-\U0001FAFF☀-➿]", "", text)
    text = re.sub(r"\s+", " ", text).strip().strip('"“”').strip()

    if len(text) > ANSWER_MAX:
        text = text[:ANSWER_MAX].rstrip() + "…"

    return text


def ask_both(prompt):
    """같은 문제를 두 AI에게. 돌려주는 값: {"Claude": 답, "Gemini": 답}. 하나라도 못 받으면 예외."""
    claude = shorts.claude_json(ANSWER_SYSTEM, prompt, ANSWER_SCHEMA, model=shorts.CANDIDATE_MODEL)["answer"]
    # 짧은 답이라 오래 기다릴 필요가 없다 (응답이 안 오면 60초 만에 다시 시도)
    gemini = shorts.gemini_json(ANSWER_SYSTEM, prompt, ANSWER_SCHEMA, timeout=60)["answer"]
    return {CLAUDE_LABEL: clean_answer(claude), GEMINI_LABEL: clean_answer(gemini)}


def first_number(text):
    match = re.search(r"-?\d+(?:\.\d+)?", (text or "").replace(",", ""))
    return float(match.group()) if match else None


def grade(check, answers):
    """정답이 있는 문제만 채점. 돌려주는 값: (정답 문자열, {이름: 맞았나}). 채점할 수 없으면 (None, {})."""
    if not check:
        return None, {}

    if check["type"] == "count":
        truth = float(check["text"].count(check["char"]))
    elif check["type"] == "number":
        truth = float(check["value"])
    else:
        return None, {}

    shown = f"{truth:g}"
    return shown, {name: first_number(answer) == truth for name, answer in answers.items()}


def chunk_line(text, words=3):
    """자막 끊기: 어절 3개씩 " / "로."""
    parts = text.split()
    return " / ".join(" ".join(parts[index:index + words]) for index in range(0, len(parts), words))


def build_script(battle, answers):
    truth, result = grade(battle.get("check"), answers)
    claude, gemini = answers[CLAUDE_LABEL], answers[GEMINI_LABEL]
    cuts = [
        {"line": f"AI 두 개한테 / {battle['hook']} / 시켜 봤어요.", "emphasis": [], "heading": "", "section": "",
         "visual": {"type": "hook"}},
        {"line": "같은 문제를 / 클로드와 제미나이에게 / 똑같이 줬어요.", "emphasis": [], "heading": "같은 문제,\n두 AI",
         "section": "대결", "visual": {"type": "scene3d", "scene": "chat3d",
                                      "beats": [{"target": "white", "label": "Claude"}, {"target": "blue", "label": "Gemini"},
                                                {"target": "typing", "label": "생각 중"}]}},
        # 대사는 짧게(커버 문구), 화면 카드에는 두 AI에게 준 문제 원문 그대로
        {"line": f"문제는요, / {chunk_line(battle['cover'].replace(chr(10), ' '))}", "emphasis": [], "heading": "오늘의 문제", "section": "문제",
         "visual": {"type": "quote", "quote": battle["prompt"], "label": "같은 문제를 그대로 줬어요"}},
        {"line": f"먼저 클로드. / {chunk_line(claude)}", "emphasis": [], "heading": "클로드의 답", "section": "Claude",
         "visual": {"type": "chat", "label": CLAUDE_LABEL, "value": f"Claude {shorts.CANDIDATE_MODEL.title()}", "quote": claude}},
        {"line": f"제미나이는요, / {chunk_line(gemini)}", "emphasis": [], "heading": "제미나이의 답", "section": "Gemini",
         "visual": {"type": "chat", "label": GEMINI_LABEL, "value": shorts.GEMINI_SCRIPT_MODEL, "quote": gemini}},
    ]

    if truth is not None:
        winners = [name for name, ok in result.items() if ok]
        verdict = "둘 다 맞혔어요." if len(winners) == 2 else "둘 다 틀렸어요." if not winners else f"{'클로드' if winners[0] == CLAUDE_LABEL else '제미나이'} 승!"
        cuts.append({"line": f"정답은 / {truth}. / {verdict}", "emphasis": [truth], "heading": f"정답 {truth}", "section": "채점",
                     # 숫자가 0부터 올라가는 카드는 중간에 틀린 숫자가 보여서, 정답은 처음부터 그대로 보이는 카드로
                     "visual": {"type": "keywords", "items": [f"정답 {truth}"]}})
        cuts.append({"line": "여러분은 / 바로 맞히셨나요? / 댓글로 알려 주세요.", "emphasis": [], "heading": "여러분은\n맞혔나요?",
                     "section": "정리", "visual": {"type": "none"}})
    else:
        cuts.append({"line": "여러분이 보기엔 / 누가 이겼나요? / 댓글로 골라 주세요.", "emphasis": [], "heading": "누가\n이겼나요?",
                     "section": "투표", "visual": {"type": "none"}})

    script = {
        "title": battle["title"],
        "question": battle["prompt"][:30],
        "cover": battle["cover"],
        "summary": f"같은 문제를 Claude({shorts.CANDIDATE_MODEL})와 Gemini({shorts.GEMINI_SCRIPT_MODEL})에게 그대로 주고 받은 답을 그대로 보여 줍니다.",
        "tips": [],
        "caution": "",
        "hashtags": ["AI대결", "Claude", "Gemini", "AI", "챗봇"],
        "cuts": cuts,
    }
    script = shorts.validate_script(script)
    script["series"] = "AI 대결"
    return script, {"truth": truth, "result": result}


def build_description(script, battle, answers, grading):
    lines = [
        f"문제: {battle['prompt']}",
        "",
        f"Claude ({shorts.CANDIDATE_MODEL}): {answers[CLAUDE_LABEL]}",
        f"Gemini ({shorts.GEMINI_SCRIPT_MODEL}): {answers[GEMINI_LABEL]}",
    ]

    if grading["truth"] is not None:
        lines += ["", f"정답: {grading['truth']}"]

    lines += ["", "두 AI에게 같은 문제를 그대로 주고, 받은 답을 고치지 않고 보여 줍니다.", "누가 이겼는지 댓글로 알려 주세요!", "",
              "이 영상의 음성은 AI로 생성되었습니다.", "#shorts #AI대결 #Claude #Gemini #AI"]
    return shorts.youtube_safe("\n".join(lines))


def pick_battle(battles, history, wanted=None):
    used = {entry.get("link") for entry in history}

    if wanted:
        return next((battle for battle in battles if battle["id"] == wanted), None)

    return next((battle for battle in battles if f"battle:{battle['id']}" not in used), None)


def parse_args():
    parser = argparse.ArgumentParser(description="AI 대결 쇼츠")
    parser.add_argument("--id", help="이 문제로 만들기 (시험용)")
    parser.add_argument("--no-upload", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    history = shorts.load_json(shorts.SHORTS_HISTORY_FILE, [])
    battle = pick_battle(shorts.load_json(BATTLES_FILE, []), history, args.id)

    if not battle:
        print("새 AI 대결 문제가 없습니다. config/battles.json에 문제를 더 넣어 주세요.")
        shorts.notify_slack(f"[{shorts.CHANNEL_NAME}] AI 대결 문제가 다 떨어졌습니다 (config/battles.json)")
        return

    work_dir = os.path.join(OUTPUT_DIR, f"{shorts.today_kst()}_{battle['id']}")
    os.makedirs(work_dir, exist_ok=True)
    print(f"AI 대결: {battle['id']} — {battle['prompt']}")

    answers = ask_both(battle["prompt"])
    print(f"Claude: {answers[CLAUDE_LABEL]}\nGemini: {answers[GEMINI_LABEL]}")
    script, grading = build_script(battle, answers)
    shorts.save_json(os.path.join(work_dir, "answers.json"), {"battle": battle, "answers": answers, "grading": grading})
    shorts.save_json(os.path.join(work_dir, "script.json"), script)

    voice = shorts.GEMINI_TTS_VOICES[0]
    narration, cut_words, voice = shorts.synthesize_narration(script["cuts"], work_dir, voice)
    source_label = "AI 대결 · 실제 답 그대로"
    video = shorts.build_video(script, narration, cut_words, source_label, work_dir, os.path.join(work_dir, "short.mp4"))
    description = build_description(script, battle, answers, grading)
    report = shorts.probe_video(video)
    problems = shorts.find_video_problems(report, [("제목", script["title"]), ("설명란", description),
                                                   ("자막", " ".join(cut["line"] for cut in script["cuts"]))])
    print(f"영상 완성: {video} ({report.get('duration', 0):.1f}초)")

    if problems:
        print("검수 실패:\n- " + "\n- ".join(problems))

    if args.no_upload:
        print("--no-upload: 업로드를 건너뜁니다.")
        return

    if problems:
        shorts.notify_slack(f"[{shorts.CHANNEL_NAME}] AI 대결 업로드 보류 (검수 실패)\n*{script['title']}*\n" + "\n".join(problems))
        raise SystemExit("검수 실패로 업로드하지 않았습니다.")

    publish_at = shorts.next_publish_slot(history) if shorts.UPLOAD_PRIVACY == "public" else None
    metadata = {
        "snippet": {"title": shorts.youtube_safe(script["title"])[:100], "description": shorts.cut_bytes(description, 5000),
                    "tags": script["hashtags"], "categoryId": "28", "defaultLanguage": "ko", "defaultAudioLanguage": "ko"},
        "status": {"privacyStatus": shorts.UPLOAD_PRIVACY, "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True},
    }

    if publish_at:
        metadata["status"]["privacyStatus"] = "private"
        metadata["status"]["publishAt"] = publish_at.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

    video_id, privacy = shorts.youtube_upload_file(video, metadata)
    note = ""

    if shorts.THUMBNAIL_ENABLED:
        try:
            problem = shorts.set_youtube_thumbnail(video_id, shorts.render_thumbnail(script, work_dir))
        except Exception as error:
            problem = str(error)
        note = "" if problem is None else f"\n썸네일 적용 실패: {problem}"

    when = f"예약 공개 {publish_at:%m/%d %H:%M} KST" if publish_at else privacy
    print(f"업로드 완료 ({when}): https://youtu.be/{video_id}{note}")
    shorts.notify_slack(f"[{shorts.CHANNEL_NAME}] AI 대결 쇼츠 ({when})\n*{script['title']}*\nhttps://youtu.be/{video_id}{note}")
    history.append({
        "date": shorts.today_kst(),
        "link": f"battle:{battle['id']}",
        "title": script["title"],
        "video_id": video_id,
        "voice": voice,
        "series": "AI 대결",
        **({"publish_at": publish_at.isoformat()} if publish_at else {}),
    })
    shorts.save_json(shorts.SHORTS_HISTORY_FILE, history)


if __name__ == "__main__":
    main()
