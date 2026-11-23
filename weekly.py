"""주간 모음 영상: 그 주에 올린 쇼츠 중 시청자 점수가 높은 것 최대 7개를 순위로 묶은 16:9 영상.

11/23 채널 방향 재설정. 잘 되는 IT 채널(조코딩 "AI뉴스" 등)은 뉴스 전달을 주 1회 긴 영상으로 한다.
대본은 매일 쇼츠에서 이미 팩트체크를 마친 것(shorts_history.json의 script)을 그대로 다시 쓴다 → 새 사실이 들어갈 일이 없고 Claude도 안 쓴다.

화면: WeeklyPanel(1920x1080, 오른쪽에 순위 목록·지금 순위 강조) 위 왼쪽 자리에 그 순위의 쇼츠(9:16)를 얹는다.
순서: 인트로(목소리 한 줄) → N위 … 1위. 설명란에 챕터(시각)와 각 쇼츠 링크·원문 링크.
"""

import argparse
import json
import os
import shutil
import subprocess
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import shorts

KST = ZoneInfo("Asia/Seoul")
WEEKLY_HISTORY_FILE = "config/weekly_history.json"
OUTPUT_DIR = "runtime/weekly"
WEEKLY_MAX = int(os.environ.get("WEEKLY_MAX", "7"))
WEEKLY_MIN = int(os.environ.get("WEEKLY_MIN", "3"))
PUBLISH_HOUR = int(os.environ.get("WEEKLY_PUBLISH_HOUR", "11"))  # 일요일 오전 11시 공개
SLOT = {"x": 90, "y": 0, "width": 608, "height": 1080}  # 쇼츠를 얹을 자리 (Weekly.tsx와 같은 값)


def entry_day(entry):
    """그 쇼츠가 공개된(예정) 날짜. 없으면 기사 날짜."""
    stamp = entry.get("publish_at")

    if stamp:
        return datetime.fromisoformat(stamp).astimezone(KST).date()

    return datetime.strptime(entry["date"], "%Y-%m-%d").date()


def week_entries(history, end):
    """end 날짜까지 7일 동안 공개된 쇼츠 중 대본이 저장된 것."""
    start = end - timedelta(days=6)
    return [entry for entry in history if entry.get("video_id") and entry.get("script") and start <= entry_day(entry) <= end]


def choose(entries):
    """시청자 점수 높은 순 최대 WEEKLY_MAX개 → 1위부터 순위를 매긴다. 돌려주는 값은 순위 큰 것(N위)부터 (카운트다운)."""
    ranked = sorted(entries, key=lambda entry: (entry.get("pick_score") or 0, entry.get("publish_at") or entry["date"]), reverse=True)
    picked = [{**entry, "rank": index + 1} for index, entry in enumerate(ranked[:WEEKLY_MAX])]
    return list(reversed(picked))


def timestamp(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}" if seconds < 3600 else f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def chapters(intro_seconds, items):
    """YouTube 챕터: 00:00부터, 3개 이상, 각 10초 이상. 인트로는 10초보다 짧아 첫 순위 챕터에 합친다."""
    lines = []
    at = intro_seconds

    for index, item in enumerate(items):
        lines.append(f"{timestamp(0 if index == 0 else at)} {item['rank']}위 {item['script']['title']}")
        at += item["seconds"]

    return lines


def build_description(heading, items, chapter_lines):
    lines = [f"{heading}. 친구한테 보내고 싶은 IT 소식만 모았어요.", "", *chapter_lines, "", "이번 주 쇼츠"]

    for item in sorted(items, key=lambda item: item["rank"]):
        lines.append(f"{item['rank']}위 {item['script']['title']} https://youtu.be/{item['video_id']}")

    lines += ["", "원문"]

    for item in sorted(items, key=lambda item: item["rank"]):
        lines.append(f"{item['rank']}위 {item['link']}")

    lines += ["", "매일 저녁 6시 쇼츠, 일요일 오전 11시 주간 정리.", "이 영상의 대본과 음성은 AI로 생성되었습니다.", "#IT뉴스 #AI뉴스 #주간IT"]
    return "\n".join(lines)


def restore_images(script, folder):
    """쇼츠 때 받은 원문 이미지를 다시 받는다 (파일은 실행이 끝나면 사라져서 주소만 남아 있다). 못 받으면 그 컷은 자막만."""
    images = []
    os.makedirs(folder, exist_ok=True)

    for image in script.get("images") or []:
        path = os.path.join(folder, f"{image['id']}.png")

        try:
            if shorts.download_image(image["url"], path):
                images.append({**image, "file": os.path.abspath(path)})
        except Exception as error:
            print(f"이미지를 다시 받지 못했습니다: {image['url']} ({error})")

    return {**script, "images": images}


def run(command, **kwargs):
    subprocess.run(command, check=True, capture_output=True, timeout=kwargs.pop("timeout", 1800), **kwargs)


def render_still(composition, props, work_dir, output_path):
    props_path = os.path.abspath(os.path.join(work_dir, f"{composition}_{os.path.basename(output_path)}.json"))
    shorts.save_json(props_path, props)
    run([shutil.which("npx"), "remotion", "still", "src/index.ts", composition, os.path.abspath(output_path), f"--props={props_path}", "--log=error"],
        cwd=shorts.VIDEO_PROJECT_DIR, timeout=600)
    return output_path


ENCODE = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def still_clip(image, audio, output_path, pad=0.6):
    """그림 한 장 + 목소리 → 클립 (인트로)."""
    run([shorts.ffmpeg_exe(), "-y", "-loop", "1", "-i", image, "-i", audio, "-af", f"apad=pad_dur={pad}", "-shortest", *ENCODE, output_path])
    return output_path


def panel_clip(panel, short_video, output_path):
    """순위 바탕 그림 왼쪽 자리에 쇼츠를 얹는다."""
    overlay = f"[1:v]scale={SLOT['width']}:{SLOT['height']},setsar=1[v];[0:v][v]overlay={SLOT['x']}:{SLOT['y']}:shortest=1[o]"
    run([shorts.ffmpeg_exe(), "-y", "-loop", "1", "-i", panel, "-i", short_video, "-filter_complex", overlay,
         "-map", "[o]", "-map", "1:a", *ENCODE, output_path])
    return output_path


def concat(clips, output_path):
    listing = output_path + ".txt"

    with open(listing, "w", encoding="utf-8") as file:
        for clip in clips:
            file.write(f"file '{os.path.abspath(clip)}'\n")

    run([shorts.ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", "-movflags", "+faststart", output_path])
    return output_path


def next_sunday_publish(now):
    days = (6 - now.weekday()) % 7
    publish = (now + timedelta(days=days)).replace(hour=PUBLISH_HOUR, minute=0, second=0, microsecond=0)
    return publish if publish > now + timedelta(minutes=30) else publish + timedelta(days=7)


def upload(video_path, thumbnail, heading, description, publish_at):
    metadata = {
        "snippet": {
            "title": shorts.youtube_safe(heading)[:100],
            "description": shorts.cut_bytes(shorts.youtube_safe(description), 5000),
            "tags": ["IT뉴스", "AI뉴스", "주간IT", "테크뉴스"],
            "categoryId": "28",
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {"privacyStatus": shorts.UPLOAD_PRIVACY, "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True},
    }

    if publish_at and shorts.UPLOAD_PRIVACY == "public":
        metadata["status"]["privacyStatus"] = "private"
        metadata["status"]["publishAt"] = publish_at.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

    video_id, privacy = shorts.youtube_upload_file(video_path, metadata)
    problem = shorts.set_youtube_thumbnail(video_id, thumbnail)
    return video_id, privacy, problem


def parse_args():
    parser = argparse.ArgumentParser(description="주간 모음 영상")
    parser.add_argument("--date", default=shorts.today_kst(), help="주의 마지막 날 (YYYY-MM-DD, 기본 오늘)")
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--history", default=shorts.SHORTS_HISTORY_FILE, help="쇼츠 기록 파일 (시험용으로 바꿀 수 있음)")
    return parser.parse_args()


def main():
    args = parse_args()
    end = datetime.strptime(args.date, "%Y-%m-%d").date()
    weekly_history = shorts.load_json(WEEKLY_HISTORY_FILE, [])

    if any(entry.get("week_end") == args.date and entry.get("video_id") for entry in weekly_history) and not args.no_upload:
        print(f"{args.date} 주간 영상은 이미 올렸습니다.")
        return

    items = choose(week_entries(shorts.load_json(args.history, []), end))

    if len(items) < WEEKLY_MIN:
        print(f"이번 주 대본이 저장된 쇼츠가 {len(items)}개뿐이라 주간 영상을 만들지 않습니다 (기준 {WEEKLY_MIN}개).")
        return

    start = end - timedelta(days=6)
    count = len(items)
    heading = f"이번 주 IT 소식 TOP {count}"
    week_range = f"{start.month}/{start.day} ~ {end.month}/{end.day}"
    work_dir = os.path.join(OUTPUT_DIR, args.date)
    os.makedirs(work_dir, exist_ok=True)
    rows = [{"rank": item["rank"], "title": item["script"]["title"], "series": item.get("series") or ""} for item in items]
    panel = {"mode": "panel", "heading": heading, "range": week_range, "items": rows, "slot": SLOT}
    print(f"{heading} ({week_range}): " + " / ".join(f"{item['rank']}위 {item['script']['title']}" for item in items))

    clips = []
    voice = shorts.GEMINI_TTS_VOICES[0]

    # 인트로: 순위 목록 전체 + 목소리 한 줄
    intro_text = f"이번 주 친구한테 보내고 싶은 IT 소식, {count}개 골라 왔어요. {count}위부터 갈게요."
    intro_audio = os.path.join(work_dir, "intro.mp3")
    shorts.gemini_tts(intro_text, intro_audio, voice)
    intro_png = render_still("WeeklyPanel", {**panel, "current": None}, work_dir, os.path.join(work_dir, "intro.png"))
    clips.append(still_clip(intro_png, intro_audio, os.path.join(work_dir, "00_intro.mp4")))
    intro_seconds = shorts.audio_duration(clips[0])

    for item in items:
        item_dir = os.path.join(work_dir, f"rank{item['rank']}")
        os.makedirs(item_dir, exist_ok=True)
        script = restore_images(item["script"], os.path.join(item_dir, "images"))
        narration, cut_words, _ = shorts.synthesize_narration(script["cuts"], item_dir, voice)
        short_video = shorts.build_video(script, narration, cut_words, item.get("source_label") or "", item_dir, os.path.join(item_dir, "short.mp4"))
        panel_png = render_still("WeeklyPanel", {**panel, "current": item["rank"]}, work_dir, os.path.join(item_dir, "panel.png"))
        clip = panel_clip(panel_png, short_video, os.path.join(work_dir, f"{len(clips):02d}_rank{item['rank']}.mp4"))
        item["seconds"] = shorts.audio_duration(clip)
        clips.append(clip)
        print(f"{item['rank']}위 완료 ({item['seconds']:.1f}초)")

    video = concat(clips, os.path.join(work_dir, "weekly.mp4"))
    thumbnail = render_still("WeeklyThumb", {**panel, "mode": "thumb", "current": None, "cover": f"이번 주\nIT 소식 TOP {count}"},
                             work_dir, os.path.join(work_dir, "thumbnail.png"))
    chapter_lines = chapters(intro_seconds, items)
    description = build_description(heading, items, chapter_lines)
    title = f"{heading} ({week_range}) | " + items[-1]["script"]["title"]
    shorts.save_json(os.path.join(work_dir, "weekly.json"), {"title": title, "description": description, "items": [
        {"rank": item["rank"], "video_id": item["video_id"], "title": item["script"]["title"], "seconds": item["seconds"]} for item in items]})
    print(f"주간 영상 완성: {video}\n{title}\n{description}")

    if args.no_upload:
        print("업로드 없이 끝냅니다 (--no-upload).")
        return

    publish_at = next_sunday_publish(datetime.now(KST))
    video_id, privacy, problem = upload(video, thumbnail, title, description, publish_at)
    note = f"\n썸네일 적용 실패: {problem}" if problem else ""
    print(f"업로드 완료 (예약 공개 {publish_at:%m/%d %H:%M} KST, 상태 {privacy}): https://youtu.be/{video_id}{note}")
    shorts.notify_slack(f"[{shorts.CHANNEL_NAME}] 주간 영상 예약 공개 ({publish_at:%m/%d %H:%M} KST)\n*{title}*\nhttps://youtu.be/{video_id}{note}")
    weekly_history.append({"week_end": args.date, "video_id": video_id, "title": title, "publish_at": publish_at.isoformat(),
                           "items": [item["video_id"] for item in items]})
    shorts.save_json(WEEKLY_HISTORY_FILE, weekly_history)


if __name__ == "__main__":
    main()
