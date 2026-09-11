import os
import json
import urllib.request
import urllib.parse
from html import unescape

import feedparser
from bs4 import BeautifulSoup


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-3.1-flash-lite"

SENT_ARTICLES_FILE = "sent_articles.json"

MAX_CONTENT_LENGTH = 12000
INITIALIZE_ONLY = True


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
        print("발송 기록 읽기 실패:", error)
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


def normalize_article_url(url):
    if not url:
        return ""

    parsed = urllib.parse.urlsplit(url)

    normalized = urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            ""
        )
    )

    return normalized.rstrip("/")


def clean_html(html_text):
    if not html_text:
        return ""

    soup = BeautifulSoup(
        html_text,
        "html.parser"
    )

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        separator="\n"
    )

    text = unescape(text)

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line:
            lines.append(line)

    cleaned = "\n".join(lines)

    return cleaned


def get_feed(blog):
    print(
        f"RSS 요청: {blog['rss']}"
    )

    feed = feedparser.parse(
        blog["rss"],
        agent=(
            "Mozilla/5.0 "
            "(compatible; TechNewsBot/1.0)"
        )
    )

    if not feed.entries:
        raise RuntimeError(
            "RSS에서 게시글을 찾지 못했습니다."
        )

    if getattr(
        feed,
        "bozo",
        False
    ):
        print(
            "RSS 경고:",
            getattr(
                feed,
                "bozo_exception",
                "알 수 없는 RSS 오류"
            )
        )

    return feed


def get_recent_articles(blog, limit=10):
    feed = get_feed(blog)

    articles = []

    for entry in feed.entries[:limit]:
        title = entry.get(
            "title",
            "제목 없음"
        )

        link = entry.get(
            "link",
            ""
        )

        normalized_url = normalize_article_url(
            link
        )

        pub_date = (
            entry.get("published")
            or entry.get("updated")
            or ""
        )

        summary = entry.get(
            "summary",
            ""
        )

        rss_content = ""

        if "content" in entry:
            try:
                contents = entry.get(
                    "content",
                    []
                )

                if contents:
                    rss_content = contents[0].get(
                        "value",
                        ""
                    )

            except Exception as error:
                print(
                    "RSS 본문 추출 실패:",
                    error
                )

        articles.append(
            {
                "company": blog["name"],
                "title": title.strip(),
                "link": normalized_url,
                "pub_date": pub_date.strip(),
                "summary": summary,
                "rss_content": rss_content,
            }
        )

    return articles


def get_content_from_rss(article):
    rss_content = article.get(
        "rss_content",
        ""
    )

    if rss_content:

        cleaned = clean_html(
            rss_content
        )

        if len(cleaned) >= 200:

            print(
                "RSS 안의 본문을 사용합니다."
            )

            return cleaned[
                :MAX_CONTENT_LENGTH
            ]

    summary = article.get(
        "summary",
        ""
    )

    if summary:

        cleaned_summary = clean_html(
            summary
        )

        if len(cleaned_summary) >= 200:

            print(
                "RSS 요약문을 사용합니다."
            )

            return cleaned_summary[
                :MAX_CONTENT_LENGTH
            ]

    return ""


def download_article_page(article):
    url = article["link"]

    if not url:
        return ""

    print(
        "원문 페이지에서 본문을 가져옵니다."
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": (
                "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
            ),
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

        content = clean_html(
            html
        )

        return content[
            :MAX_CONTENT_LENGTH
        ]

    except Exception as error:

        print(
            "본문 페이지 가져오기 실패:",
            error
        )

        return ""


def get_article_content(article):
    rss_content = get_content_from_rss(
        article
    )

    if rss_content:
        return rss_content

    page_content = download_article_page(
        article
    )

    if page_content:
        return page_content

    print(
        "본문을 충분히 가져오지 못했습니다."
    )

    return ""


def summarize_with_gemini(
    article,
    content
):
    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY가 없습니다."
        )

    if not content:

        raise RuntimeError(
            "요약할 본문이 없습니다."
        )

    prompt = f"""
너는 개발자를 위한 기술 블로그 브리핑 편집자다.

아래 글의 실제 내용을 바탕으로 한국어로 정리해라.

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
개발을 잘 모르는 사람도 이해할 수 있도록
2~3문장으로 설명한다.


[왜 이 글을 썼나]

작성자가 어떤 문제나 상황 때문에
이 기술 또는 방법을 고민했는지 설명한다.


[핵심 내용]

중요한 내용을 3~5개로 정리한다.

각 항목은 너무 짧은 단어만 쓰지 말고
왜 중요한지도 설명한다.


[사용한 기술 / 방법]

글에서 실제로 언급된 기술,
도구, 구조, 설계 방법 등이 있다면 정리한다.

기술이 없다면 억지로 만들지 않는다.


[결과]

글에서 실제 결과가 언급되어 있다면 정리한다.

성능 개선 수치나 결과가 본문에 없다면
추측하지 않는다.


[알아둬야 할 것]

이 글을 이해하거나
실제 프로젝트에 활용하기 위해
알아두면 좋은 개념을 쉽게 설명한다.


[추가로 공부하면 좋은 것]

이 글과 연결해서 공부하면 좋은 주제를
2~4개 추천한다.


[난이도]

초급 / 중급 / 고급 중 하나


[추천 대상]

어떤 개발자나 학습자에게
특히 도움이 되는 글인지 한 줄로 작성한다.


규칙:

- 본문에 없는 사실을 만들지 않는다.
- 수치와 결과를 추측하지 않는다.
- 제목만 보고 내용을 추측하지 않는다.
- 어려운 기술 용어는 쉽게 풀어서 설명한다.
- 한국어로 작성한다.
- 기술명과 제품명은 원래 이름을 유지한다.
- 광고성 문구는 무시한다.
- 웹페이지 메뉴와 관련 없는 문구는 무시한다.
- 원문 URL은 결과에 넣지 않는다.
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
        ],
        "generationConfig": {
            "temperature": 0.2
        }
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
        timeout=90
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
        "━━━━━━━━━━━━━━━━━━\n"
        "📰 *새 기술 블로그 글*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"🏢 *{article['company']}*\n\n"

        f"📌 *{article['title']}*\n\n"

        f"{summary}\n\n"

        f"📅 *게시일*\n"
        f"{article['pub_date']}\n\n"

        f"🔗 *원문*\n"
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

    articles = get_recent_articles(
        blog,
        limit=10
    )

    print(
        "RSS에서 확인한 글 수:",
        len(articles)
    )

    new_articles = []

    for article in articles:
        article_url = article["link"]

        if not article_url:
            continue

        if article_url not in sent_articles:
            new_articles.append(
                article
            )

    print(
        "새 글 수:",
        len(new_articles)
    )

    if not new_articles:
        print(
            "새 글이 없습니다."
        )

        return 0

        if INITIALIZE_ONLY:
        print(
            "초기화 모드입니다."
        )

        added_count = 0

        for article in new_articles:
            article_url = article["link"]

            if (
                article_url
                and article_url not in sent_articles
            ):
                sent_articles.append(
                    article_url
                )

                added_count += 1

        save_sent_articles(
            sent_articles
        )

        print(
            "기준점으로 등록한 글 수:",
            added_count
        )

        print(
            "Slack 전송은 하지 않습니다."
        )

        return 0

    new_articles.reverse()

    sent_count = 0

    for article in new_articles:

        print()
        print(
            "-" * 40
        )

        print(
            "처리할 글:",
            article["title"]
        )

        print(
            "URL:",
            article["link"]
        )

        content = get_article_content(
            article
        )

        print(
            "최종 본문 길이:",
            len(content)
        )

        if not content:
            print(
                "본문이 없어 이 글은 건너뜁니다."
            )

            continue

        print(
            "Gemini 요약 요청"
        )

        try:
            summary = summarize_with_gemini(
                article,
                content
            )

        except Exception as error:
            print(
                "Gemini 요약 실패:",
                repr(error)
            )

            continue

        print(
            "Gemini 요약 완료"
        )

        try:
            send_to_slack(
                article,
                summary
            )

        except Exception as error:
            print(
                "Slack 전송 실패:",
                repr(error)
            )

            continue

        print(
            "Slack 전송 완료"
        )

        sent_articles.append(
            article["link"]
        )

        save_sent_articles(
            sent_articles
        )

        print(
            "발송 기록 저장 완료"
        )

        sent_count += 1

    return sent_count


def main():
    sent_articles = load_sent_articles()

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

        sent_count = process_blog(
            blog,
            sent_articles
        )

        success_count += 1
        new_count += sent_count

    except Exception as error:

        error_count += 1

        print()
        print(
            f"[오류] {blog['name']}"
        )

        print(
            repr(error)
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
        "현재 발송 기록:",
        len(sent_articles)
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    main()
