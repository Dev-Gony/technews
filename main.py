import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import os
import re
from html import unescape


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-3.1-flash-lite"

MAX_CONTENT_LENGTH = 12000

SENT_ARTICLES_FILE = "sent_articles.json"


BLOGS = [
    {
        "name": "G마켓",
        "rss": "https://dev.gmarket.com/rss",
    },
    {
        "name": "네이버 플레이스",
        "rss": "https://medium.com/feed/naver-place-dev",
    },
    {
        "name": "쿠팡",
        "rss": "https://medium.com/feed/coupang-engineering",
    },
    {
        "name": "당근",
        "rss": "https://medium.com/feed/daangn",
    },
]


def load_sent_articles():
    if not os.path.exists(SENT_ARTICLES_FILE):
        return []

    try:
        with open(
            SENT_ARTICLES_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except Exception as error:
        print(
            "sent_articles.json 읽기 실패:",
            error
        )

        return []


def save_sent_articles(sent_articles):
    with open(
        SENT_ARTICLES_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            sent_articles,
            file,
            ensure_ascii=False,
            indent=2
        )


def download_rss(rss_url):
    request = urllib.request.Request(
        rss_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; TechNewsBot/1.0)"
            )
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return response.read()


def get_latest_article(blog):
    rss_data = download_rss(
        blog["rss"]
    )

    root = ET.fromstring(
        rss_data
    )

    item = root.find(
        "./channel/item"
    )

    if item is None:
        raise RuntimeError(
            "RSS에서 게시글을 찾지 못했습니다."
        )

    title = item.findtext(
        "title",
        default="제목 없음"
    )

    link = item.findtext(
        "link",
        default=""
    )

    pub_date = item.findtext(
        "pubDate",
        default=""
    )

    description = item.findtext(
        "description",
        default=""
    )

    return {
        "company": blog["name"],
        "title": title.strip(),
        "link": link.strip(),
        "pub_date": pub_date.strip(),
        "description": description.strip(),
    }


def clean_html(text):
    if not text:
        return ""

    text = re.sub(
        r"<script.*?</script>",
        " ",
        text,
        flags=re.S | re.I
    )

    text = re.sub(
        r"<style.*?</style>",
        " ",
        text,
        flags=re.S | re.I
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = unescape(
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def get_article_content(article):
    request = urllib.request.Request(
        article["link"],
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; TechNewsBot/1.0)"
            )
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            html = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        cleaned = clean_html(
            html
        )

        if len(cleaned) > MAX_CONTENT_LENGTH:
            cleaned = cleaned[
                :MAX_CONTENT_LENGTH
            ]

        return cleaned

    except Exception as error:
        print(
            "본문 가져오기 실패:",
            error
        )

        fallback = clean_html(
            article["description"]
        )

        return fallback[
            :MAX_CONTENT_LENGTH
        ]


def summarize_with_gemini(
    article,
    content
):
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY가 없습니다."
        )

    prompt = f"""
너는 개발자를 위한 기술 블로그 브리핑 편집자다.

아래 기술 블로그 글을 읽고 한국어로 쉽게 정리해라.

회사:
{article["company"]}

제목:
{article["title"]}

게시일:
{article["pub_date"]}

본문:
{content}

다음 형식을 반드시 지켜라.

[한눈에 보기]
이 글이 무엇에 관한 글인지
2~3문장으로 설명한다.

[핵심 내용]
- 중요한 내용 3~5개
- 어떤 문제를 해결하려 했는지
- 어떤 기술이나 방법을 사용했는지
- 결과가 있다면 어떤 결과가 있었는지

[알아둬야 할 것]
- 개발자가 이 글에서 알아두면 좋은 개념
- 실제 프로젝트에 적용할 때 주의할 점
- 추가로 공부하면 좋은 내용

[난이도]
초급 / 중급 / 고급 중 하나

[추천 대상]
어떤 개발자에게 도움이 되는 글인지
한 줄로 작성한다.

규칙:
- 본문에 없는 사실은 만들어내지 않는다.
- 확인되지 않은 수치나 결과를 추측하지 않는다.
- 어려운 기술 용어는 쉽게 설명한다.
- 너무 길게 작성하지 않는다.
- 원문 URL은 요약 내용에 포함하지 않는다.
- 본문이 불완전하면 그 사실을 밝힌다.
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
        f"?key={urllib.parse.quote(GEMINI_API_KEY)}"
    )

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    data = json.dumps(
        body
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:

        result = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    try:
        return (
            result["candidates"][0]
            ["content"]["parts"][0]
            ["text"]
        )

    except (
        KeyError,
        IndexError
    ):

        print(
            "Gemini 응답:",
            result
        )

        raise RuntimeError(
            "Gemini 응답을 해석하지 못했습니다."
        )


def send_to_slack(
    article,
    summary
):
    if not SLACK_WEBHOOK_URL:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL이 없습니다."
        )

    message_text = (
        "📰 *새 기술 블로그 글*\n\n"
        f"*회사*\n"
        f"{article['company']}\n\n"

        f"*제목*\n"
        f"{article['title']}\n\n"

        f"{summary}\n\n"

        f"*작성일*\n"
        f"{article['pub_date']}\n\n"

        f"*원문*\n"
        f"{article['link']}"
    )

    message = {
        "text": message_text
    }

    data = json.dumps(
        message
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        result = (
            response
            .read()
            .decode("utf-8")
        )

    if result != "ok":
        raise RuntimeError(
            f"Slack 전송 실패: {result}"
        )


def process_blog(
    blog,
    sent_articles
):
    print()
    print(
        "=" * 60
    )

    print(
        f"확인 중: {blog['name']}"
    )

    article = get_latest_article(
        blog
    )

    print(
        "최신 글:",
        article["title"]
    )

    article_url = (
        article["link"]
    )

    if not article_url:
        raise RuntimeError(
            "게시글 URL이 없습니다."
        )

    if article_url in sent_articles:
        print(
            "이미 보낸 글입니다."
        )

        return False

    print(
        "새 글 발견"
    )

    content = get_article_content(
        article
    )

    print(
        "본문 길이:",
        len(content)
    )

    if not content:
        print(
            "본문이 비어 있습니다."
        )

        content = (
            "본문을 충분히 가져오지 못했습니다."
        )

    print(
        "Gemini 요약 요청"
    )

    summary = summarize_with_gemini(
        article,
        content
    )

    print(
        "Gemini 요약 완료"
    )

    send_to_slack(
        article,
        summary
    )

    print(
        "Slack 전송 완료"
    )

    sent_articles.append(
        article_url
    )

    save_sent_articles(
        sent_articles
    )

    print(
        "발송 기록 저장 완료"
    )

    return True


def main():
    sent_articles = (
        load_sent_articles()
    )

    print(
        "================================"
    )

    print(
        "Tech News Bot 시작"
    )

    print(
        "등록 블로그:",
        len(BLOGS)
    )

    print(
        "기존 발송 기록:",
        len(sent_articles)
    )

    print(
        "================================"
    )

    success_count = 0
    new_count = 0
    error_count = 0

    for blog in BLOGS:

        try:
            was_new = process_blog(
                blog,
                sent_articles
            )

            success_count += 1

            if was_new:
                new_count += 1

        except Exception as error:

            error_count += 1

            print()
            print(
                f"[오류] {blog['name']}"
            )

            print(
                error
            )

            print(
                "이 블로그는 건너뛰고 "
                "다음 블로그를 확인합니다."
            )

    print()
    print(
        "================================"
    )

    print(
        "모든 블로그 확인 완료"
    )

    print(
        "정상 확인:",
        success_count
    )

    print(
        "새 글:",
        new_count
    )

    print(
        "오류:",
        error_count
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    main()
