import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import os
import re
from html import unescape


RSS_URL = "https://dev.gmarket.com/rss"

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-3.1-flash-lite"

MAX_CONTENT_LENGTH = 12000

SENT_ARTICLES_FILE = "sent_articles.json"


def load_sent_articles():
    if not os.path.exists(SENT_ARTICLES_FILE):
        return []

    try:
        with open(SENT_ARTICLES_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except Exception as error:
        print("sent_articles.json 읽기 실패:", error)
        return []


def save_sent_articles(sent_articles):
    with open(SENT_ARTICLES_FILE, "w", encoding="utf-8") as file:
        json.dump(
            sent_articles,
            file,
            ensure_ascii=False,
            indent=2
        )


def get_latest_article():
    request = urllib.request.Request(
        RSS_URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        rss_data = response.read()

    root = ET.fromstring(rss_data)

    item = root.find("./channel/item")

    if item is None:
        raise RuntimeError("RSS에서 게시글을 찾지 못했습니다.")

    title = item.findtext("title", default="제목 없음")
    link = item.findtext("link", default="")
    pub_date = item.findtext("pubDate", default="")
    description = item.findtext("description", default="")

    return {
        "title": title.strip(),
        "link": link.strip(),
        "pub_date": pub_date.strip(),
        "description": description.strip(),
    }


def clean_html(text):
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

    text = unescape(text)

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
            "User-Agent": "Mozilla/5.0"
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:
            html = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        cleaned = clean_html(html)

        if len(cleaned) > MAX_CONTENT_LENGTH:
            cleaned = cleaned[:MAX_CONTENT_LENGTH]

        return cleaned

    except Exception as error:
        print("본문 가져오기 실패:", error)

        fallback = clean_html(
            article["description"]
        )

        return fallback[:MAX_CONTENT_LENGTH]


def summarize_with_gemini(article, content):
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY Secret이 설정되어 있지 않습니다."
        )

    prompt = f"""
너는 개발자를 위한 기술 블로그 브리핑 편집자다.

아래 기술 블로그 글을 읽고 한국어로 쉽게 정리해라.

회사:
G마켓

제목:
{article["title"]}

게시일:
{article["pub_date"]}

본문:
{content}

다음 형식을 반드시 지켜라.

[한눈에 보기]
이 글이 무엇에 관한 글인지 2~3문장으로 설명.

[핵심 내용]
- 중요한 내용 3~5개
- 어떤 문제를 해결하려 했는지
- 어떤 기술이나 방법을 사용했는지

[알아둬야 할 것]
- 개발자가 이 글에서 알아두면 좋은 개념
- 실제 프로젝트에 적용할 때 주의할 점
- 추가로 공부하면 좋은 내용

[난이도]
초급 / 중급 / 고급 중 하나

[추천 대상]
어떤 개발자에게 도움이 되는 글인지 한 줄

규칙:
- 본문에 없는 사실을 만들어내지 않는다.
- 어려운 용어는 가능한 한 쉽게 설명한다.
- 지나치게 길게 쓰지 않는다.
- 원문 URL은 요약에 포함하지 않는다.
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
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

    data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]

    except (KeyError, IndexError):
        print("Gemini 응답:")
        print(result)

        raise RuntimeError(
            "Gemini 응답을 해석하지 못했습니다."
        )


def send_to_slack(article, summary):
    if not SLACK_WEBHOOK_URL:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL Secret이 설정되어 있지 않습니다."
        )

    message_text = (
        "📰 *오늘의 기술 블로그 테스트*\n\n"
        f"*회사*\nG마켓\n\n"
        f"*제목*\n{article['title']}\n\n"
        f"{summary}\n\n"
        f"*원문*\n{article['link']}"
    )

    message = {
        "text": message_text
    }

    data = json.dumps(message).encode("utf-8")

    request = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:
        result = response.read().decode("utf-8")

    if result != "ok":
        raise RuntimeError(
            f"Slack 전송 실패: {result}"
        )


def main():
    print("1. 이미 보낸 게시글 목록 불러오기")

    sent_articles = load_sent_articles()

    print(
        "현재까지 보낸 글 수:",
        len(sent_articles)
    )

    print("2. G마켓 최신 게시글 확인")

    article = get_latest_article()

    print(
        "최신 게시글:",
        article["title"]
    )

    article_url = article["link"]

    if article_url in sent_articles:
        print("이미 보낸 게시글입니다.")
        print("Slack 전송을 생략합니다.")
        return

    print("새로운 게시글입니다.")

    print("3. 게시글 본문 가져오기")

    content = get_article_content(article)

    print(
        "본문 길이:",
        len(content)
    )

    print("4. Gemini 요약 요청")

    summary = summarize_with_gemini(
        article,
        content
    )

    print("Gemini 요약 완료")

    print("5. Slack 전송")

    send_to_slack(
        article,
        summary
    )

    print("Slack 전송 완료")

    print("6. 보낸 게시글 기록")

    sent_articles.append(article_url)

    save_sent_articles(sent_articles)

    print(
        "현재까지 보낸 글 수:",
        len(sent_articles)
    )


if __name__ == "__main__":
    main()
