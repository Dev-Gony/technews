"""GONY DAILY 기사로 인스타그램 카드뉴스(1080x1350 PNG 여러 장)를 만든다.

흐름: 기사 선택 → Claude 카드 문구 → Remotion Cards 컴포지션 → 장별 PNG + 본문(캡션)
게시(인스타그램·스레드)는 계정 연결 후 붙인다.
"""

import os
import re
import glob
import shutil
import argparse
import subprocess
import urllib.parse
from datetime import datetime

import shorts


CHANNEL_HANDLE = os.environ.get("CARDS_HANDLE", "@itgony")
CARDS_HISTORY_FILE = "config/cards_history.json"
OUTPUT_DIR = "runtime/cards"

SLIDE_TYPES = ["cover", "story", "number", "flow", "checklist", "caution", "outro"]


CARDS_SYSTEM_PROMPT = """너는 기술 뉴스 신문 "GONY DAILY"의 인스타그램 카드뉴스 편집자다.
독자: 개발자·직장인. 피드를 넘기다 표지를 보고 멈춘 뒤, 끝까지 넘겨서 "저장"하게 만드는 게 목표다.

문체: 신문 기사처럼 짧고 단정한 평서문("~했다", "~다"). 한 문장은 25자 안팎. 군더더기·감탄사 금지.
숫자, 회사명, 결과는 반드시 주어진 기사에 있는 것만 쓴다. 없는 사실을 지어내지 않는다.

카드 구성 (6~8장, 순서 유지):
1. cover: 표지. label에 분야 2단어(예: "AI · 비용"), title에 2줄 헤드라인(줄 사이 \\n, 줄당 12자 이내),
   핵심 숫자나 단어 하나를 **이렇게** 감싸 강조. body에 무엇을 다루는지 2줄.
2. story: "무슨 일이 있었나". title 2줄, items에 사실 3개(각 30자 이내).
3. number: 기사에 인상적인 숫자가 있을 때만. value에 숫자+단위(8자 이내), title에 무엇의 숫자인지, body에 한 줄 설명.
4. flow: 원리나 과정이 있을 때만. title 한 줄, items에 2~4단계(각 16자 이내).
5. checklist: "바로 써먹는 법". title 한 줄, items에 독자가 오늘 해볼 행동 2~3개(명령어·설정이 있으면 그대로).
6. caution: 비용·보안·개인정보 주의점이 있을 때만. title 한 줄, body 2문장 이내.
7. outro: 마지막 장. label "여러분 생각은?", title에 독자에게 던지는 질문 2~3줄, body에 저장을 권하는 한 줄.
number, flow, caution은 기사에 재료가 없으면 빼도 된다. cover, story, checklist, outro는 꼭 넣는다.

caption: 인스타그램 본문. 첫 줄은 표지보다 구체적인 훅 한 문장, 이어서 핵심 3줄 요약(각 줄 앞에 "▪"). 원문 링크와 해시태그는 넣지 않는다(자동으로 붙는다).
hashtags: # 없이 8~12개. 한국어 위주, 개발자들이 실제로 검색할 만한 것."""


CARDS_SCHEMA = {
    "type": "object",
    "properties": {
        "section": {"type": "string"},
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": SLIDE_TYPES},
                    "label": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "value": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["type"],
                "additionalProperties": False,
            },
        },
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["section", "slides", "caption", "hashtags"],
    "additionalProperties": False,
}


def validate_cards(content):
    slides = content.get("slides") or []

    for slide in slides:
        for key in ("title", "body"):
            if slide.get(key):
                # 모델이 줄바꿈을 글자 그대로 "\n"으로 쓰는 경우가 있다.
                slide[key] = slide[key].replace("\\n", "\n").strip()

        slide["items"] = [item.strip() for item in slide.get("items") or [] if item.strip()]

    # 재료가 없는 장은 뺀다.
    slides = [
        slide
        for slide in slides
        if slide.get("title") or slide.get("value") or slide.get("body") or slide.get("items")
    ]

    if not slides or slides[0]["type"] != "cover":
        raise ValueError("첫 장이 표지(cover)가 아닙니다.")

    if slides[-1]["type"] != "outro":
        raise ValueError("마지막 장이 outro가 아닙니다.")

    if not 4 <= len(slides) <= 10:
        raise ValueError(f"카드 장 수가 이상합니다: {len(slides)}")

    content["slides"] = slides
    content["hashtags"] = [
        tag.strip().lstrip("#").replace(" ", "")
        for tag in content.get("hashtags") or []
        if tag.strip()
    ]

    return content


def generate_cards(article):
    content = shorts.claude_json(CARDS_SYSTEM_PROMPT, shorts.build_script_prompt(article), CARDS_SCHEMA)

    return validate_cards(content)


def build_caption(content, article):
    hashtags = " ".join(f"#{tag}" for tag in content["hashtags"])

    source = article.get("company") or urllib.parse.urlsplit(article["link"]).netloc

    return (
        f"{content['caption'].strip()}\n\n"
        "💾 저장해두고 필요할 때 다시 보세요\n"
        f"🔗 원문({source}): {article['link']}\n\n"
        f"{hashtags}"
    )[:2200]


def build_props(content, article):
    date = datetime.strptime(article["issue_date"], "%Y-%m-%d").strftime("%Y.%m.%d")

    return {
        "masthead": "GONY DAILY",
        "date": date,
        "section": content["section"],
        "handle": CHANNEL_HANDLE,
        "source": f"출처: {article.get('company') or urllib.parse.urlsplit(article['link']).netloc}",
        "slides": content["slides"],
    }


def render_cards(props, work_dir):
    """Remotion Cards 컴포지션을 장별 PNG로 렌더링한다. 돌려주는 값: PNG 경로 목록(순서대로)."""
    npx = shutil.which("npx")

    if not npx:
        raise RuntimeError("Node.js(npx)가 없습니다. video/ 폴더에서 npm ci를 먼저 실행하세요.")

    props_path = os.path.abspath(os.path.join(work_dir, "props.json"))
    frames_dir = os.path.abspath(os.path.join(work_dir, "frames"))
    shorts.save_json(props_path, props)
    shutil.rmtree(frames_dir, ignore_errors=True)

    result = subprocess.run(
        [
            npx, "remotion", "render", "src/index.ts", "Cards", frames_dir,
            "--sequence", "--image-format=png", f"--props={props_path}", "--log=error",
        ],
        cwd=shorts.VIDEO_PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=900,
    )

    if result.returncode != 0:
        raise RuntimeError(f"카드 렌더링 실패: {(result.stderr or result.stdout).strip()[-2000:]}")

    frames = sorted(
        glob.glob(os.path.join(frames_dir, "*.png")),
        key=lambda path: int(re.findall(r"\d+", os.path.basename(path))[-1]),
    )
    paths = []

    for index, frame in enumerate(frames, start=1):
        path = os.path.join(work_dir, f"card-{index:02d}.png")
        shutil.move(frame, path)
        paths.append(path)

    shutil.rmtree(frames_dir, ignore_errors=True)

    return paths


def parse_args():
    parser = argparse.ArgumentParser(description="GONY DAILY 기사로 인스타그램 카드뉴스 만들기")
    parser.add_argument("--date", default=shorts.today_kst(), help="이슈 날짜 (기본: 오늘, KST)")
    parser.add_argument("--link", help="이 기사로 만들기 (기본: 아직 안 만든 기사 중 자동 선택)")

    return parser.parse_args()


def main():
    args = parse_args()

    history = shorts.load_json(CARDS_HISTORY_FILE, [])
    issues = [(date, shorts.load_issue(date)) for date in shorts.recent_issue_dates(args.date)]

    if args.link:
        article = next(
            (
                {**article, "issue_date": date}
                for date, issue in issues
                for article in shorts.issue_articles(issue)
                if article["link"] == args.link
            ),
            None,
        )
    else:
        article = shorts.pick_article(issues, {entry["link"] for entry in history})

    if not article:
        print("카드뉴스로 만들 기사가 없습니다.")
        return

    print(f"선택한 기사: [{article['issue_date']}] {article['title']}")

    slug = re.sub(r"[^0-9A-Za-z]+", "-", urllib.parse.urlsplit(article["link"]).path + urllib.parse.urlsplit(article["link"]).query)
    work_dir = os.path.join(OUTPUT_DIR, f"{article['issue_date']}_{slug.strip('-')[-24:]}")
    os.makedirs(work_dir, exist_ok=True)

    content = generate_cards(article)
    shorts.save_json(os.path.join(work_dir, "content.json"), content)
    print(f"카드 문구 생성 완료: {len(content['slides'])}장")

    paths = render_cards(build_props(content, article), work_dir)

    with open(os.path.join(work_dir, "caption.txt"), "w", encoding="utf-8") as file:
        file.write(build_caption(content, article))

    print(f"카드 렌더링 완료: {work_dir} ({len(paths)}장)")


if __name__ == "__main__":
    main()
