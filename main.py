import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from html import unescape
from urllib.parse import urljoin, urlsplit
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
from bs4 import BeautifulSoup

from preferences import load_user_preferences


SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID", "").strip()
NEWSPAPER_BASE_URL = os.environ.get(
    "NEWSPAPER_BASE_URL",
    "https://dev-gony.github.io/technews"
).strip().rstrip("/")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-3.1-flash-lite"

SENT_ARTICLES_FILE = "sent_articles.json"
SLACK_FEEDBACK_STATE_FILE = "config/slack_feedback_state.json"
SLACK_FEEDBACK_FILE = "config/slack_feedback.json"
ARTICLE_HISTORY_FILE = "config/article_history.json"
DAILY_ISSUES_DIR = "config/issues"

MAX_CONTENT_LENGTH = 12000

DEFAULT_RECENT_ARTICLE_LIMIT = 10
GEEKNEWS_RECENT_ARTICLE_LIMIT = 30

PREFILTER_TEXT_LENGTH = 800
PREFILTER_BATCH_SIZE = 10
DETAIL_BATCH_SIZE = 5
ACTIONABILITY_THRESHOLD = 4

USER_PREFERENCES = load_user_preferences()
BRIEF_SCORE_THRESHOLD = USER_PREFERENCES["scoring"]["brief_threshold"]
DETAILED_SCORE_THRESHOLD = USER_PREFERENCES["scoring"]["detailed_threshold"]


def load_feedback_topic_weights(
    path=SLACK_FEEDBACK_FILE
):
    if not os.path.exists(
        path
    ):
        return {}

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(
                file
            )
    except (
        OSError,
        json.JSONDecodeError
    ):
        return {}

    articles = data.get(
        "articles",
        {}
    )

    if not isinstance(
        articles,
        dict
    ):
        return {}

    weights = {}

    for record in articles.values():
        if not isinstance(
            record,
            dict
        ):
            continue

        article = record.get(
            "article",
            {}
        )
        feedback = record.get(
            "feedback",
            {}
        )

        topics = article.get(
            "topics",
            []
        )

        if not isinstance(
            topics,
            list
        ):
            continue

        try:
            helpful = int(
                feedback.get(
                    "helpful",
                    0
                )
            )
            not_helpful = int(
                feedback.get(
                    "not_helpful",
                    0
                )
            )
            more_like_this = int(
                feedback.get(
                    "more_like_this",
                    0
                )
            )
            less_like_this = int(
                feedback.get(
                    "less_like_this",
                    0
                )
            )
        except (
            TypeError,
            ValueError
        ):
            continue

        signal = (
            helpful * 0.25
            + more_like_this * 0.75
            - not_helpful * 0.25
            - less_like_this * 0.75
        )

        if signal == 0:
            continue

        for topic in topics:
            normalized_topic = str(
                topic
            ).strip()

            if not normalized_topic:
                continue

            key = normalized_topic.casefold()

            weights[
                key
            ] = weights.get(
                key,
                0.0
            ) + signal

    return {
        topic: max(
            -2.0,
            min(
                2.0,
                weight
            )
        )
        for topic, weight in weights.items()
        if abs(weight) >= 0.25
    }


FEEDBACK_TOPIC_WEIGHTS = (
    load_feedback_topic_weights()
)

INITIALIZE_ONLY = False


BLOGS = [
    {
        "name": "네이버 D2",
        "enabled": True,
        "type": "rss",
        "rss": "https://d2.naver.com/d2.atom",
    },
    {
        "name": "네이버 플레이스",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/naver-place-dev",
    },
    {
        "name": "쿠팡",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/coupang-engineering",
    },
    {
        "name": "우아한형제들",
        "enabled": False,
        "type": "html",
        "url": "https://techblog.woowahan.com/",
        "html_type": "woowahan",
    },
    {
        "name": "요기요",
        "enabled": True,
        "type": "rss",
        "rss": "https://techblog.yogiyo.co.kr/feed",
    },
    {
        "name": "토스",
        "enabled": True,
        "type": "rss",
        "rss": "https://toss.tech/rss.xml",
    },
    {
        "name": "뱅크샐러드",
        "enabled": True,
        "type": "rss",
        "rss": "https://blog.banksalad.com/rss.xml",
    },
    {
        "name": "쏘카",
        "enabled": True,
        "type": "html",
        "url": "https://tech.socar.kr/posts",
        "html_type": "socar",
    },
    {
        "name": "직방",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/zigbang",
    },
    {
        "name": "G마켓",
        "enabled": True,
        "type": "rss",
        "rss": "https://dev.gmarket.com/rss",
    },
    {
        "name": "마켓컬리",
        "enabled": True,
        "type": "rss",
        "rss": "https://helloworld.kurly.com/rss.xml",
    },
    {
        "name": "당근",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/daangn",
    },
    {
        "name": "LINE Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://engineering.linecorp.com/ko/feed/index.html",
    },
    {
        "name": "데브시스터즈",
        "enabled": True,
        "type": "rss",
        "rss": "https://tech.devsisters.com/rss.xml",
    },
    {
        "name": "왓챠",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/watcha",
    },
    {
        "name": "무신사",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/musinsa-tech",
    },
    {
        "name": "Google Developers",
        "enabled": True,
        "type": "rss",
        "rss": "https://developers.googleblog.com/feeds/posts/default/",
    },
    {
        "name": "Apple Developer",
        "enabled": True,
        "type": "rss",
        "rss": "https://developer.apple.com/news/rss/news.rss",
    },
    {
        "name": "GitHub Blog",
        "enabled": True,
        "type": "rss",
        "rss": "https://github.blog/feed/",
    },
    {
        "name": "Meta Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://engineering.fb.com/feed/",
    },
    {
        "name": "Netflix TechBlog",
        "enabled": True,
        "type": "rss",
        "rss": "https://netflixtechblog.com/feed",
    },
    {
        "name": "Google Play",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/googleplaydev",
    },
    {
        "name": "Airbnb Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://medium.com/feed/airbnb-engineering",
    },
    {
        "name": "Slack Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://slack.engineering/feed/",
    },
    {
        "name": "Spotify Engineering",
        "enabled": True,
        "type": "rss",
        "rss": "https://engineering.atspotify.com/feed/",
    },
    {
        "name": "Stripe",
        "enabled": True,
        "type": "rss",
        "rss": "https://stripe.com/blog/feed.rss",
    },
    {
        "name": "Cloudflare",
        "enabled": True,
        "type": "rss",
        "rss": "https://blog.cloudflare.com/rss/",
    },
    {
        "name": "AWS Architecture",
        "enabled": True,
        "type": "rss",
        "rss": "https://aws.amazon.com/blogs/architecture/feed/",
    },
    {
        "name": "AWS Compute",
        "enabled": True,
        "type": "rss",
        "rss": "https://aws.amazon.com/blogs/compute/feed/",
    },
    {
        "name": "Uber Engineering",
        "enabled": True,
        "type": "html",
        "url": "https://www.uber.com/us/en/blog/engineering/",
        "html_type": "uber",
    },
    {
        "name": "GeekNews",
        "enabled": True,
        "type": "rss",
        "rss": "https://feeds.feedburner.com/geeknews-feed",
        "recent_limit": GEEKNEWS_RECENT_ARTICLE_LIMIT,
        "source_kind": "curation",
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
            "발송 기록 읽기 실패:",
            error
        )

        return []


def save_sent_articles(sent_articles):
    unique_articles = list(
        dict.fromkeys(
            sent_articles
        )
    )

    with open(
        SENT_ARTICLES_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            unique_articles,
            file,
            ensure_ascii=False,
            indent=2
        )


def normalize_article_url(url):
    if not url:
        return ""

    parsed = urllib.parse.urlsplit(
        url
    )

    query = ""

    if (
        parsed.netloc == "news.hada.io"
        and parsed.path.rstrip("/") == "/topic"
    ):
        query_params = urllib.parse.parse_qs(
            parsed.query
        )

        topic_id = query_params.get(
            "id",
            []
        )

        if topic_id:
            query = urllib.parse.urlencode(
                {
                    "id": topic_id[0]
                }
            )

    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            query,
            ""
        )
    )


def normalize_title_for_dedupe(title):
    if not title:
        return ""

    normalized = unescape(
        title
    ).lower()

    normalized = re.sub(
        r"\s+",
        " ",
        normalized
    )

    normalized = re.sub(
        r"[^0-9a-z가-힣 ]",
        "",
        normalized
    )

    return normalized.strip()


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
            "iframe",
            "form",
        ]
    ):
        tag.decompose()

    text = soup.get_text(
        separator="\n"
    )

    text = unescape(
        text
    )

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if line:
            lines.append(
                line
            )

    return "\n".join(
        lines
    )


def clean_slack_text(text):
    if not text:
        return ""

    text = unescape(
        text
    )

    text = text.replace(
        "\\-",
        "•"
    )

    text = text.replace(
        "\\*",
        "*"
    )

    text = text.replace(
        "\\_",
        "_"
    )

    text = text.replace(
        "\\.",
        "."
    )

    text = text.replace(
        "\\(",
        "("
    )

    text = text.replace(
        "\\)",
        ")"
    )

    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"*\1*",
        text
    )

    text = re.sub(
        r"(?m)^-\s+",
        "• ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def download_html(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),
            "Accept-Language": (
                "ko-KR,ko;q=0.9,"
                "en-US;q=0.8,en;q=0.7"
            ),
            "Cache-Control": "no-cache",
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="ignore"
        )


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


def get_entry_link(
    entry,
    blog
):
    candidates = []

    if blog.get("name") == "GeekNews":
        for item in entry.get(
            "links",
            []
        ):
            if not isinstance(
                item,
                dict
            ):
                continue

            rel = item.get(
                "rel",
                "alternate"
            )

            href = item.get(
                "href",
                ""
            )

            if (
                rel == "alternate"
                and href
            ):
                candidates.append(
                    href
                )

        candidates.extend(
            [
                entry.get(
                    "link",
                    ""
                ),
                entry.get(
                    "id",
                    ""
                ),
            ]
        )

    else:
        candidates.append(
            entry.get(
                "link",
                ""
            )
        )

    for candidate in candidates:
        if not candidate:
            continue

        normalized = normalize_article_url(
            candidate
        )

        if normalized:
            return normalized

    return ""


def get_rss_articles(
    blog,
    limit
):
    feed = get_feed(
        blog
    )

    articles = []

    for entry in feed.entries[:limit]:
        title = unescape(
            entry.get(
                "title",
                "제목 없음"
            ).strip()
        )

        link = get_entry_link(
            entry,
            blog
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
                    rss_content = (
                        contents[0]
                        .get(
                            "value",
                            ""
                        )
                    )

            except Exception as error:
                print(
                    "RSS 본문 추출 실패:",
                    error
                )

        articles.append(
            {
                "company": blog["name"],
                "title": title,
                "link": link,
                "pub_date": pub_date.strip(),
                "summary": summary,
                "rss_content": rss_content,
                "source_kind": blog.get(
                    "source_kind",
                    "direct"
                ),
            }
        )

    return articles


def get_socar_articles(
    blog,
    limit
):
    print(
        f"HTML 목록 요청: {blog['url']}"
    )

    soup = BeautifulSoup(
        download_html(
            blog["url"]
        ),
        "html.parser"
    )

    articles = []
    seen_urls = set()

    for tag in soup.find_all(
        "a",
        href=True
    ):
        full_url = urljoin(
            blog["url"],
            tag.get(
                "href",
                ""
            )
        )

        parsed = urlsplit(
            full_url
        )

        if not re.fullmatch(
            r"/dev/\d{4}/\d{2}/\d{2}/[^/]+/?",
            parsed.path
        ):
            continue

        url = normalize_article_url(
            full_url
        )

        if url in seen_urls:
            continue

        title = unescape(
            tag.get_text(
                " ",
                strip=True
            )
        )

        if not title:
            continue

        seen_urls.add(
            url
        )

        articles.append(
            {
                "company": blog["name"],
                "title": title,
                "link": url,
                "pub_date": "",
                "summary": "",
                "rss_content": "",
                "source_kind": blog.get(
                    "source_kind",
                    "direct"
                ),
            }
        )

        if len(
            articles
        ) >= limit:
            break

    if not articles:
        raise RuntimeError(
            "쏘카 글 목록을 찾지 못했습니다."
        )

    return articles


def get_uber_articles(
    blog,
    limit
):
    print(
        f"HTML 목록 요청: {blog['url']}"
    )

    soup = BeautifulSoup(
        download_html(
            blog["url"]
        ),
        "html.parser"
    )

    articles = []
    seen_urls = set()

    for tag in soup.find_all(
        "a",
        href=True
    ):
        full_url = urljoin(
            blog["url"],
            tag.get(
                "href",
                ""
            )
        )

        parsed = urlsplit(
            full_url
        )

        if not re.fullmatch(
            r"/us/en/blog/[^/]+/?",
            parsed.path
        ):
            continue

        if parsed.path.rstrip(
            "/"
        ) == "/us/en/blog/engineering":
            continue

        url = normalize_article_url(
            full_url
        )

        if url in seen_urls:
            continue

        title = unescape(
            tag.get_text(
                " ",
                strip=True
            )
        )

        if len(
            title
        ) < 5:
            continue

        seen_urls.add(
            url
        )

        articles.append(
            {
                "company": blog["name"],
                "title": title,
                "link": url,
                "pub_date": "",
                "summary": "",
                "rss_content": "",
                "source_kind": blog.get(
                    "source_kind",
                    "direct"
                ),
            }
        )

        if len(
            articles
        ) >= limit:
            break

    if not articles:
        raise RuntimeError(
            "Uber Engineering 글 목록을 찾지 못했습니다."
        )

    return articles


def get_html_articles(
    blog,
    limit
):
    html_type = blog.get(
        "html_type"
    )

    if html_type == "socar":
        return get_socar_articles(
            blog,
            limit
        )

    if html_type == "uber":
        return get_uber_articles(
            blog,
            limit
        )

    raise RuntimeError(
        f"지원하지 않는 HTML 방식: {html_type}"
    )


def get_recent_articles(
    blog,
    limit=DEFAULT_RECENT_ARTICLE_LIMIT
):
    if blog["type"] == "rss":
        return get_rss_articles(
            blog,
            limit
        )

    if blog["type"] == "html":
        return get_html_articles(
            blog,
            limit
        )

    raise RuntimeError(
        "알 수 없는 수집 방식입니다."
    )


def deduplicate_candidate_articles(
    articles
):
    deduplicated = []
    url_positions = {}
    title_positions = {}

    for article in articles:
        url_key = normalize_article_url(
            article.get(
                "link",
                ""
            )
        )

        title_key = normalize_title_for_dedupe(
            article.get(
                "title",
                ""
            )
        )

        duplicate_position = None

        if (
            url_key
            and url_key in url_positions
        ):
            duplicate_position = (
                url_positions[url_key]
            )

        elif (
            title_key
            and title_key in title_positions
        ):
            duplicate_position = (
                title_positions[title_key]
            )

        if duplicate_position is None:
            position = len(
                deduplicated
            )

            deduplicated.append(
                article
            )

            if url_key:
                url_positions[
                    url_key
                ] = position

            if title_key:
                title_positions[
                    title_key
                ] = position

            continue

        existing = deduplicated[
            duplicate_position
        ]

        existing_kind = existing.get(
            "source_kind",
            "direct"
        )

        new_kind = article.get(
            "source_kind",
            "direct"
        )

        if (
            existing_kind == "curation"
            and new_kind == "direct"
        ):
            deduplicated[
                duplicate_position
            ] = article

    return deduplicated


def get_prefilter_text(
    article
):
    rss_content = clean_html(
        article.get(
            "rss_content",
            ""
        )
    )

    summary = clean_html(
        article.get(
            "summary",
            ""
        )
    )

    text = rss_content or summary

    return text[
        :PREFILTER_TEXT_LENGTH
    ]


def extract_json_text(text):
    if not text:
        return ""

    text = text.strip()

    fenced_match = re.search(
        r"```(?:json)?\s*(.*?)```",
        text,
        re.S | re.I
    )

    if fenced_match:
        text = fenced_match.group(
            1
        ).strip()

    first_bracket = text.find(
        "["
    )

    last_bracket = text.rfind(
        "]"
    )

    if (
        first_bracket >= 0
        and last_bracket > first_bracket
    ):
        return text[
            first_bracket:
            last_bracket + 1
        ]

    return text


def get_429_wait_seconds(
    error_body,
    fallback_seconds=45
):
    if not error_body:
        return fallback_seconds

    match = re.search(
        r"retry in\s+([0-9.]+)s",
        error_body,
        re.I
    )

    if not match:
        return fallback_seconds

    try:
        return max(
            1,
            math.ceil(
                float(
                    match.group(1)
                )
            ) + 1
        )

    except ValueError:
        return fallback_seconds


def call_gemini(prompt):
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY가 없습니다."
        )

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

    max_attempts = 4

    for attempt in range(
        1,
        max_attempts + 1
    ):
        print(
            f"Gemini 요청 시도 "
            f"{attempt}/{max_attempts}"
        )

        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type":
                    "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=90
            ) as response:
                result = json.loads(
                    response
                    .read()
                    .decode(
                        "utf-8"
                    )
                )

            text = (
                result["candidates"][0]
                ["content"]["parts"][0]
                ["text"]
            )

            print(
                "Gemini 요청 성공"
            )

            return text

        except urllib.error.HTTPError as error:
            status_code = error.code

            try:
                error_body = (
                    error
                    .read()
                    .decode(
                        "utf-8",
                        errors="ignore"
                    )
                )

            except Exception:
                error_body = ""

            print(
                "Gemini HTTP 오류:",
                status_code
            )

            print(
                error_body[:1000]
            )

            retryable_codes = {
                429,
                500,
                502,
                503,
                504,
            }

            if (
                status_code
                not in retryable_codes
            ):
                raise

            if attempt >= max_attempts:
                raise

            if status_code == 429:
                wait_seconds = (
                    get_429_wait_seconds(
                        error_body
                    )
                )

            else:
                wait_seconds = (
                    3
                    * (
                        2
                        ** (
                            attempt - 1
                        )
                    )
                )

            print(
                f"{wait_seconds}초 후 다시 시도"
            )

            time.sleep(
                wait_seconds
            )

        except (
            TimeoutError,
            urllib.error.URLError
        ) as error:
            print(
                "Gemini 네트워크 오류:",
                repr(
                    error
                )
            )

            if attempt >= max_attempts:
                raise

            wait_seconds = (
                3
                * (
                    2
                    ** (
                        attempt - 1
                    )
                )
            )

            print(
                f"{wait_seconds}초 후 다시 시도"
            )

            time.sleep(
                wait_seconds
            )

    raise RuntimeError(
        "Gemini 요청이 모두 실패했습니다."
    )


def get_feedback_relevance_bias(
    article,
    topic_weights=None
):
    weights = (
        FEEDBACK_TOPIC_WEIGHTS
        if topic_weights is None
        else topic_weights
    )

    if not weights:
        return 0

    text = " ".join(
        [
            str(
                article.get(
                    "title",
                    ""
                )
            ),
            get_prefilter_text(
                article
            ),
        ]
    ).casefold()

    matched_weight = 0.0

    for topic, weight in (
        weights.items()
    ):
        if topic in text:
            matched_weight += weight

    if matched_weight >= 0.5:
        return 1

    if matched_weight <= -0.5:
        return -1

    return 0


def format_feedback_learning_context(
    topic_weights=None
):
    weights = (
        FEEDBACK_TOPIC_WEIGHTS
        if topic_weights is None
        else topic_weights
    )

    if not weights:
        return "아직 충분한 피드백 데이터가 없음"

    positive = sorted(
        [
            (topic, weight)
            for topic, weight in weights.items()
            if weight > 0
        ],
        key=lambda item: item[1],
        reverse=True
    )[:5]

    negative = sorted(
        [
            (topic, weight)
            for topic, weight in weights.items()
            if weight < 0
        ],
        key=lambda item: item[1]
    )[:5]

    lines = []

    if positive:
        lines.append(
            "더 선호하는 경향: "
            + ", ".join(
                topic
                for topic, _ in positive
            )
        )

    if negative:
        lines.append(
            "덜 선호하는 경향: "
            + ", ".join(
                topic
                for topic, _ in negative
            )
        )

    return "\n".join(
        lines
    ) or "아직 충분한 피드백 데이터가 없음"


def build_prefilter_prompt(
    articles
):
    article_inputs = []

    for index, article in enumerate(
        articles,
        start=1
    ):
        preview = get_prefilter_text(
            article
        )

        article_inputs.append(
            f"""
기사 번호: {index}
출처: {article["company"]}
출처 유형: {article.get("source_kind", "direct")}
제목: {article["title"]}
게시일: {article["pub_date"]}
RSS 미리보기:
{preview if preview else "(미리보기 없음)"}
"""
        )

    combined = "\n".join(
        article_inputs
    )

    interest_lines = "\n".join(
        f"{index}. {interest}"
        for index, interest in enumerate(
            USER_PREFERENCES["interests"],
            start=1,
        )
    )

    avoid_topics = USER_PREFERENCES.get(
        "avoid_topics",
        [],
    )

    if avoid_topics:
        avoid_lines = "\n".join(
            f"- {topic}"
            for topic in avoid_topics
        )
    else:
        avoid_lines = "(없음)"

    feedback_context = (
        format_feedback_learning_context()
    )

    return f"""
너는 개발자와 IT 실무자를 위한 기술 뉴스 편집자다.

아래 기사 {len(articles)}개를 빠짐없이 모두 평가한다.

사용자의 우선 관심 분야:

{interest_lines}

사용자가 우선순위를 낮추고 싶은 주제:

{avoid_lines}

실제 Slack 피드백에서 학습한 약한 선호 신호:

{feedback_context}

이 피드백은 보조 신호다.
중요한 기술 변화나 실제 활용 가치가 높은 글을 피드백만으로 강제 제외하지 않는다.

avoid_topics는 강제 제외 규칙이 아니다.
관련성이 높거나 업계적으로 중요한 글이라면 다른 점수를 함께 고려한다.

각 기사마다 다음 세 점수를 0~5점으로 평가한다.

relevance:
사용자의 관심 분야 및 현재 학습 방향과 얼마나 관련 있는가

practical_value:
실무, 프로젝트, 학습에 실제로 활용할 가치가 얼마나 있는가

significance:
중요한 기술 변화, 업계 변화, 보안 이슈,
플랫폼 변화 또는 알아둘 가치가 얼마나 큰가

total_score는 세 점수의 합계다.

판단 기준:

• {DETAILED_SCORE_THRESHOLD}~15점:
상세하게 읽을 가치가 높은 글

• {BRIEF_SCORE_THRESHOLD}~{DETAILED_SCORE_THRESHOLD - 1}점:
상세 요약까지는 필요 없지만 링크와 제목은 확인할 가치가 있는 글

• 0~{BRIEF_SCORE_THRESHOLD - 1}점:
현재 사용자에게 우선순위가 낮은 글

다음과 같은 경우는 관심 분야와 조금 다르더라도
significance 점수를 높게 줄 수 있다.

• 주요 보안 사고
• 주요 플랫폼 정책 변화
• 널리 사용되는 개발 도구의 큰 변경
• AI 및 소프트웨어 산업의 중대한 변화

반대로 단순 홍보,
기술적 내용이 거의 없는 기업 소식,
사용자와 무관한 생활 뉴스,
반복 콘텐츠는 낮게 평가한다.

직접 구독 중인 기업 기술블로그는
사용자가 의도적으로 선택한 출처라는 점을
약간 고려할 수 있다.

GeekNews라는 이유만으로
점수를 높이거나 낮추지 않는다.

중요:
현재 배치에는 기사 번호 1부터 {len(articles)}까지가 있다.

반드시 모든 번호를 정확히 한 번씩 반환한다.
어떤 기사도 생략하면 안 된다.

결과는 JSON 배열만 반환한다.
Markdown 코드블록이나 추가 설명은 쓰지 않는다.

형식:

[
  {{
    "index": 1,
    "relevance": 0,
    "practical_value": 0,
    "significance": 0,
    "total_score": 0,
    "reason": "판단 이유를 한국어 한 문장으로 작성"
  }}
]

기사 목록:

{combined}
"""


def parse_prefilter_result(
    result,
    article_count
):
    json_text = extract_json_text(
        result
    )

    parsed = json.loads(
        json_text
    )

    if not isinstance(
        parsed,
        list
    ):
        raise ValueError(
            "기사 선별 결과가 JSON 배열이 아닙니다."
        )

    decisions = {}

    for item in parsed:
        if not isinstance(
            item,
            dict
        ):
            continue

        try:
            index = int(
                item.get(
                    "index"
                )
            )

        except (
            TypeError,
            ValueError
        ):
            continue

        if (
            index < 1
            or index > article_count
        ):
            continue

        if index in decisions:
            continue

        decisions[
            index
        ] = item

    return decisions


def evaluate_article_batch(
    articles
):
    prompt = build_prefilter_prompt(
        articles
    )

    last_decisions = {}

    for content_attempt in range(
        1,
        3
    ):
        print(
            f"배치 평가 응답 확인 "
            f"{content_attempt}/2"
        )

        result = call_gemini(
            prompt
        )

        decisions = parse_prefilter_result(
            result,
            len(
                articles
            )
        )

        last_decisions = decisions

        missing_indices = [
            index
            for index in range(
                1,
                len(
                    articles
                ) + 1
            )
            if index not in decisions
        ]

        if not missing_indices:
            return decisions

        print(
            "평가 응답에서 빠진 기사 번호:",
            missing_indices
        )

        print(
            "같은 배치를 한 번 더 평가합니다."
        )

    return last_decisions


def select_relevant_articles(
    candidate_articles
):
    detailed_articles = []
    brief_articles = []
    excluded_articles = []
    unresolved_articles = []

    total_batches = math.ceil(
        len(
            candidate_articles
        )
        / PREFILTER_BATCH_SIZE
    )

    for batch_number, start in enumerate(
        range(
            0,
            len(
                candidate_articles
            ),
            PREFILTER_BATCH_SIZE
        ),
        start=1
    ):
        batch = candidate_articles[
            start:
            start + PREFILTER_BATCH_SIZE
        ]

        print()
        print(
            f"1차 선별 배치 "
            f"{batch_number}/{total_batches}"
        )

        try:
            decisions = (
                evaluate_article_batch(
                    batch
                )
            )

        except Exception as error:
            print(
                "배치 평가 실패:",
                repr(
                    error
                )
            )

            decisions = {}

        for local_index, article in enumerate(
            batch,
            start=1
        ):
            decision = decisions.get(
                local_index
            )

            if decision is None:
                article[
                    "selection_score"
                ] = None

                article[
                    "selection_reason"
                ] = (
                    "Gemini 평가 결과를 받지 못함"
                )

                unresolved_articles.append(
                    article
                )

                print(
                    "평가 미완료:",
                    article["title"]
                )

                continue

            try:
                relevance = int(
                    decision.get(
                        "relevance",
                        0
                    )
                )

                practical_value = int(
                    decision.get(
                        "practical_value",
                        0
                    )
                )

                significance = int(
                    decision.get(
                        "significance",
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):
                relevance = 0
                practical_value = 0
                significance = 0

            relevance = max(
                0,
                min(
                    5,
                    relevance
                )
            )

            practical_value = max(
                0,
                min(
                    5,
                    practical_value
                )
            )

            significance = max(
                0,
                min(
                    5,
                    significance
                )
            )

            feedback_bias = (
                get_feedback_relevance_bias(
                    article
                )
            )

            if feedback_bias:
                relevance = max(
                    0,
                    min(
                        5,
                        relevance
                        + feedback_bias
                    )
                )

                article[
                    "feedback_bias"
                ] = feedback_bias

                print(
                    "피드백 학습 보정:",
                    feedback_bias,
                    article["title"]
                )
            else:
                article[
                    "feedback_bias"
                ] = 0

            calculated_total = (
                relevance
                + practical_value
                + significance
            )

            article[
                "selection_score"
            ] = calculated_total

            article[
                "selection_reason"
            ] = str(
                decision.get(
                    "reason",
                    ""
                )
            ).strip()

            print(
                f"[{calculated_total}/15] "
                f"{article['company']} - "
                f"{article['title']}"
            )

            if (
                calculated_total
                >= DETAILED_SCORE_THRESHOLD
            ):
                detailed_articles.append(
                    article
                )

            elif (
                calculated_total
                >= BRIEF_SCORE_THRESHOLD
            ):
                brief_articles.append(
                    article
                )

            else:
                excluded_articles.append(
                    article
                )

    return (
        detailed_articles,
        brief_articles,
        excluded_articles,
        unresolved_articles,
    )


def get_content_from_rss(article):
    rss_content = article.get(
        "rss_content",
        ""
    )

    if rss_content:
        cleaned = clean_html(
            rss_content
        )

        if len(
            cleaned
        ) >= 200:
            return cleaned[
                :MAX_CONTENT_LENGTH
            ]

    summary = article.get(
        "summary",
        ""
    )

    if summary:
        cleaned = clean_html(
            summary
        )

        if len(
            cleaned
        ) >= 200:
            return cleaned[
                :MAX_CONTENT_LENGTH
            ]

    return ""


def download_article_page(article):
    try:
        html = download_html(
            article["link"]
        )

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        main_content = (
            soup.find("article")
            or soup.find("main")
        )

        if main_content:
            content = clean_html(
                str(
                    main_content
                )
            )

        else:
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
    content = get_content_from_rss(
        article
    )

    if content:
        return content

    return download_article_page(
        article
    )


def build_detail_prompt(
    article_contents
):
    inputs = []

    for index, item in enumerate(
        article_contents,
        start=1
    ):
        article = item[
            "article"
        ]

        content = item[
            "content"
        ]

        inputs.append(
            f"""
기사 번호: {index}

출처:
{article["company"]}

제목:
{article["title"]}

게시일:
{article["pub_date"]}

1차 선별 점수:
{article.get("selection_score")}/15

1차 선별 이유:
{article.get("selection_reason", "")}

본문:
{content}
"""
        )

    combined = "\n".join(
        inputs
    )

    return f"""
너는 개발자를 위한 기술 뉴스 요약 편집자다.

아래 기사 {len(article_contents)}개를
각각 독립적으로 한국어로 요약한다.

반드시 기사 번호 1부터 {len(article_contents)}까지
모든 기사를 빠짐없이 반환한다.

각 기사에 대해 다음 정보를 작성한다.

one_line:
핵심 한줄 요약

key_points:
가장 중요한 내용 3개
각 항목은 1~2문장

concepts:
알아두면 좋은 핵심 개념 1~3개

recommended_for:
누가 읽으면 좋은지 한 문장

actionability:
이 기사를 읽은 뒤 개발자가 바로 실험하거나 적용해볼 가치가 있는지 0~5점으로 평가한다.
단순 개념 소개, 홍보성 내용, 즉시 적용하기 어려운 내용은 낮게 평가한다.

action:
actionability가 4점 이상일 때만 구체적인 실행 항목을 작성한다.
- type: experiment, code_improvement, study, adoption_review 중 하나
- title: 무엇을 해볼지 한 문장
- steps: 바로 시작할 수 있는 단계 1~3개
- effort: 15~30분, 30~60분, 1~2시간, 추가 검토 필요 중 하나

actionability가 3점 이하면 type은 none, title은 빈 문자열, steps는 빈 배열, effort는 빈 문자열로 작성한다.

사용자의 평소 관심 분야:
{", ".join(USER_PREFERENCES.get("interests", []))}

규칙:

- 본문에 없는 사실을 만들지 않는다.
- 숫자나 결과를 추측하지 않는다.
- 해외 글도 한국어로 작성한다.
- 기술명은 원래 이름을 유지한다.
- Action은 기사 본문과 사용자의 관심 분야에서 직접 도출할 수 있는 범위로만 작성한다.
- 기사에 없는 제품 기능, 성능 수치, 구현 결과를 추측해서 Action의 근거로 사용하지 않는다.
- Action은 "공부해보기"처럼 추상적으로 끝내지 말고 첫 행동이 명확해야 한다.
- 불필요하게 길게 작성하지 않는다.
- 모든 기사 번호를 정확히 한 번씩 포함한다.

결과는 JSON 배열만 반환한다.
Markdown 코드블록이나 추가 설명은 쓰지 않는다.

형식:

[
  {{
    "index": 1,
    "one_line": "한줄 요약",
    "key_points": [
      "핵심 내용 1",
      "핵심 내용 2",
      "핵심 내용 3"
    ],
    "concepts": [
      "핵심 개념 1",
      "핵심 개념 2"
    ],
    "recommended_for": "추천 대상",
    "actionability": 5,
    "action": {{
      "type": "experiment",
      "title": "바로 해볼 실험",
      "steps": [
        "첫 단계",
        "두 번째 단계"
      ],
      "effort": "30~60분"
    }}
  }}
]

기사 목록:

{combined}
"""


def parse_detail_result(
    result,
    article_count
):
    json_text = extract_json_text(
        result
    )

    parsed = json.loads(
        json_text
    )

    if not isinstance(
        parsed,
        list
    ):
        raise ValueError(
            "상세 요약 결과가 JSON 배열이 아닙니다."
        )

    summaries = {}

    for item in parsed:
        if not isinstance(
            item,
            dict
        ):
            continue

        try:
            index = int(
                item.get(
                    "index"
                )
            )

        except (
            TypeError,
            ValueError
        ):
            continue

        if (
            index < 1
            or index > article_count
        ):
            continue

        if index in summaries:
            continue

        summaries[
            index
        ] = item

    return summaries


def format_article_summary(
    summary_data
):
    one_line = str(
        summary_data.get(
            "one_line",
            ""
        )
    ).strip()

    key_points = summary_data.get(
        "key_points",
        []
    )

    concepts = summary_data.get(
        "concepts",
        []
    )

    recommended_for = str(
        summary_data.get(
            "recommended_for",
            ""
        )
    ).strip()

    try:
        actionability = int(
            summary_data.get(
                "actionability",
                0
            )
        )
    except (
        TypeError,
        ValueError
    ):
        actionability = 0

    actionability = max(
        0,
        min(
            5,
            actionability
        )
    )

    action = summary_data.get(
        "action",
        {}
    )

    if not isinstance(
        action,
        dict
    ):
        action = {}

    if not isinstance(
        key_points,
        list
    ):
        key_points = []

    if not isinstance(
        concepts,
        list
    ):
        concepts = []

    parts = [
        "[한줄 요약]",
        one_line or "요약 없음",
        "",
        "[핵심 내용]",
    ]

    if key_points:
        for point in key_points[:3]:
            parts.append(
                f"• {str(point).strip()}"
            )

    else:
        parts.append(
            "• 핵심 내용 추출 실패"
        )

    parts.extend(
        [
            "",
            "[알아둬야 할 것]",
        ]
    )

    if concepts:
        for concept in concepts[:3]:
            parts.append(
                f"• {str(concept).strip()}"
            )

    else:
        parts.append(
            "• 추가 개념 없음"
        )

    parts.extend(
        [
            "",
            "[추천 대상]",
            (
                recommended_for
                or "관련 기술에 관심 있는 개발자"
            ),
        ]
    )

    if actionability >= ACTIONABILITY_THRESHOLD:
        action_title = str(
            action.get(
                "title",
                ""
            )
        ).strip()
        action_type = str(
            action.get(
                "type",
                ""
            )
        ).strip()
        action_steps = action.get(
            "steps",
            []
        )
        effort = str(
            action.get(
                "effort",
                ""
            )
        ).strip()

        if not isinstance(
            action_steps,
            list
        ):
            action_steps = []

        if action_title:
            parts.extend(
                [
                    "",
                    "⚡ [직접 해볼 것]",
                    action_title,
                ]
            )

            action_type_labels = {
                "experiment": "실험",
                "code_improvement": "코드 개선",
                "study": "학습",
                "adoption_review": "도입 검토",
            }

            label = action_type_labels.get(
                action_type,
                action_type
            )

            meta = []

            if label:
                meta.append(
                    f"유형: {label}"
                )

            if effort:
                meta.append(
                    f"예상 작업량: {effort}"
                )

            if meta:
                parts.append(
                    " · ".join(
                        meta
                    )
                )

            for step in action_steps[:3]:
                step = str(
                    step
                ).strip()

                if step:
                    parts.append(
                        f"• {step}"
                    )

    return clean_slack_text(
        "\n".join(
            parts
        )
    )


def summarize_article_batches(
    articles
):
    summarized_articles = []
    unresolved_articles = []

    article_contents = []

    for article in articles:
        print()
        print(
            "본문 준비:",
            article["company"],
            "-",
            article["title"]
        )

        content = get_article_content(
            article
        )

        if not content:
            print(
                "본문 없음 - 이번 실행에서는 보류"
            )

            unresolved_articles.append(
                article
            )

            continue

        article_contents.append(
            {
                "article": article,
                "content": content,
            }
        )

    if not article_contents:
        return (
            summarized_articles,
            unresolved_articles
        )

    total_batches = math.ceil(
        len(
            article_contents
        )
        / DETAIL_BATCH_SIZE
    )

    for batch_number, start in enumerate(
        range(
            0,
            len(
                article_contents
            ),
            DETAIL_BATCH_SIZE
        ),
        start=1
    ):
        batch = article_contents[
            start:
            start + DETAIL_BATCH_SIZE
        ]

        print()
        print(
            f"상세 요약 배치 "
            f"{batch_number}/{total_batches}"
        )

        prompt = build_detail_prompt(
            batch
        )

        summaries = {}

        try:
            for content_attempt in range(
                1,
                3
            ):
                result = call_gemini(
                    prompt
                )

                summaries = parse_detail_result(
                    result,
                    len(
                        batch
                    )
                )

                missing_indices = [
                    index
                    for index in range(
                        1,
                        len(
                            batch
                        ) + 1
                    )
                    if index not in summaries
                ]

                if not missing_indices:
                    break

                print(
                    "상세 요약 누락 번호:",
                    missing_indices
                )

                print(
                    "같은 배치를 한 번 더 요약합니다."
                )

        except Exception as error:
            print(
                "상세 요약 배치 실패:",
                repr(
                    error
                )
            )

        for local_index, item in enumerate(
            batch,
            start=1
        ):
            article = item[
                "article"
            ]

            summary_data = summaries.get(
                local_index
            )

            if summary_data is None:
                print(
                    "상세 요약 미완료:",
                    article["title"]
                )

                unresolved_articles.append(
                    article
                )

                continue

            summarized_articles.append(
                {
                    "article": article,
                    "summary_data": summary_data,
                    "summary": (
                        format_article_summary(
                            summary_data
                        )
                    ),
                }
            )

    return (
        summarized_articles,
        unresolved_articles
    )


def create_daily_editorial(
    summarized_articles,
    brief_articles
):
    editorial_input = []

    for index, item in enumerate(
        summarized_articles,
        start=1
    ):
        article = item[
            "article"
        ]

        editorial_input.append(
            f"""
상세 글 {index}

출처:
{article["company"]}

제목:
{article["title"]}

선별 점수:
{article.get("selection_score")}/15

선별 이유:
{article.get("selection_reason", "")}

요약:
{item["summary"]}
"""
        )

    for index, article in enumerate(
        brief_articles,
        start=1
    ):
        editorial_input.append(
            f"""
참고 글 {index}

출처:
{article["company"]}

제목:
{article["title"]}

선별 점수:
{article.get("selection_score")}/15

선별 이유:
{article.get("selection_reason", "")}
"""
        )

    combined = "\n".join(
        editorial_input
    )

    prompt = f"""
너는 개발자와 IT 실무자를 위한
아침 기술 뉴스레터의 편집장이다.

오늘 AI가 선별한 기술 글들이 아래에 있다.

{combined}

다음 형식으로 작성한다.

[오늘 꼭 볼 글 번호]

상세 글 중 가장 우선해서 볼 가치가 높은 글을
최대 3개 선정한다.

상세 글이 없으면 NONE이라고 작성한다.

번호만 쉼표로 작성한다.

예:
3, 1, 5


[오늘의 기술 키워드]

오늘의 기술 키워드 또는 개념을
3~5개 쉼표로 작성한다.


[오늘의 한줄 포인트]

오늘 콘텐츠 전체를 관통하는 흐름을
한국어 한 문장으로 작성한다.


[오늘 왜 중요한가]

오늘 개발자 또는 AI/데이터 학습자가
왜 관심을 가져야 하는지
2~3문장으로 설명한다.


[왜 이 글들을 골랐나]

오늘 꼭 볼 글로 선정한 상세 글 각각에 대해
왜 읽을 가치가 높은지 한 문장씩 작성한다.


[오늘 공부해볼 것]

오늘 글을 바탕으로
20~30분 정도 추가 공부하면 좋은
주제 1~3개를 추천한다.

각 주제마다 이유도 짧게 작성한다.

규칙:

- 제공된 내용에 없는 사실을 만들지 않는다.
- 회사 인지도만으로 우선순위를 정하지 않는다.
- 실제 기술 문제 해결 사례를 우선한다.
- 실무 활용성과 학습 가치를 중요하게 본다.
- Slack에서 읽기 쉽게 작성한다.
- 목록은 • 기호를 사용한다.
- ** 같은 Markdown 강조 문법은 사용하지 않는다.
"""

    result = call_gemini(
        prompt
    )

    return clean_slack_text(
        result
    )


def parse_top_indices(editorial):
    match = re.search(
        r"\[오늘 꼭 볼 글 번호\]\s*([0-9,\s]+)",
        editorial
    )

    if not match:
        return []

    values = []

    for raw in match.group(
        1
    ).split(","):
        raw = raw.strip()

        if raw.isdigit():
            values.append(
                int(
                    raw
                )
            )

    return values[:3]


def remove_internal_editorial_sections(
    editorial
):
    cleaned_editorial = re.sub(
        r"\[오늘 꼭 볼 글 번호\]\s*.*?(?=\n\[|\Z)",
        "",
        editorial,
        flags=re.S
    ).strip()

    cleaned_editorial = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned_editorial
    )

    return cleaned_editorial


def split_slack_messages(
    text,
    limit=3500
):
    messages = []

    while len(
        text
    ) > limit:
        split_at = text.rfind(
            "\n",
            0,
            limit
        )

        if split_at <= 0:
            split_at = limit

        messages.append(
            text[
                :split_at
            ]
        )

        text = text[
            split_at:
        ].lstrip()

    if text:
        messages.append(
            text
        )

    return messages


def _slack_api_request(method, payload):
    if not SLACK_BOT_TOKEN:
        raise RuntimeError(
            "SLACK_BOT_TOKEN이 없습니다."
        )

    url = f"https://slack.com/api/{method}"
    data = json.dumps(
        payload
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        result = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    if not result.get("ok"):
        raise RuntimeError(
            "Slack API 요청 실패: "
            f"{result.get('error', 'unknown_error')}"
        )

    return result


def send_slack_text(text):
    if (
        SLACK_BOT_TOKEN
        and SLACK_CHANNEL_ID
    ):
        return _slack_api_request(
            "chat.postMessage",
            {
                "channel": SLACK_CHANNEL_ID,
                "text": text,
                "unfurl_links": False,
                "unfurl_media": False,
            }
        )

    if not SLACK_WEBHOOK_URL:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL이 없습니다."
        )

    data = json.dumps(
        {
            "text": text
        }
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type":
                "application/json"
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
            .decode(
                "utf-8"
            )
        )

    if result != "ok":
        raise RuntimeError(
            f"Slack 전송 실패: {result}"
        )

    return {
        "ok": True,
        "transport": "webhook",
    }


def _extract_one_line_summary(item):
    summary = item.get(
        "summary",
        ""
    )

    match = re.search(
        r"\[한줄 요약\]\s*(.+?)(?:\n|$)",
        summary,
        re.S
    )

    if match:
        return (
            match
            .group(1)
            .strip()
        )

    return (
        str(summary)
        .replace("\n", " ")
        [:180]
    )


def _load_article_history():
    if not os.path.exists(
        ARTICLE_HISTORY_FILE
    ):
        return {
            "articles": []
        }

    try:
        with open(
            ARTICLE_HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(
                file
            )
    except (
        OSError,
        json.JSONDecodeError
    ):
        return {
            "articles": []
        }

    articles = data.get(
        "articles",
        []
    )

    if not isinstance(
        articles,
        list
    ):
        articles = []

    return {
        "articles": articles
    }


def save_article_history(
    summarized_articles
):
    history = _load_article_history()
    records = history[
        "articles"
    ]

    by_link = {
        record.get(
            "link"
        ): record
        for record in records
        if isinstance(
            record,
            dict
        )
        and record.get(
            "link"
        )
    }

    now = datetime.now(
        ZoneInfo(
            "Asia/Seoul"
        )
    ).isoformat()

    for item in summarized_articles:
        article = item.get(
            "article",
            {}
        )
        summary_data = item.get(
            "summary_data",
            {}
        )

        link = article.get(
            "link"
        )

        if not link:
            continue

        concepts = summary_data.get(
            "concepts",
            []
        )

        if not isinstance(
            concepts,
            list
        ):
            concepts = []

        one_line = str(
            summary_data.get(
                "one_line",
                ""
            )
        ).strip()

        try:
            actionability = int(
                summary_data.get(
                    "actionability",
                    0
                )
            )
        except (
            TypeError,
            ValueError
        ):
            actionability = 0

        by_link[
            link
        ] = {
            "recorded_at": now,
            "company": article.get(
                "company",
                ""
            ),
            "title": article.get(
                "title",
                ""
            ),
            "link": link,
            "published_at": article.get(
                "pub_date",
                ""
            ),
            "selection_score": article.get(
                "selection_score"
            ),
            "feedback_bias": article.get(
                "feedback_bias",
                0
            ),
            "topics": [
                str(topic).strip()
                for topic in concepts[:5]
                if str(topic).strip()
            ],
            "one_line": one_line,
            "actionability": max(
                0,
                min(
                    5,
                    actionability
                )
            ),
        }

    trimmed = sorted(
        by_link.values(),
        key=lambda record: record.get(
            "recorded_at",
            ""
        ),
        reverse=True
    )[:500]

    os.makedirs(
        os.path.dirname(
            ARTICLE_HISTORY_FILE
        ),
        exist_ok=True
    )

    temp_path = (
        ARTICLE_HISTORY_FILE
        + ".tmp"
    )

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {
                "articles": trimmed,
                "updated_at": now,
            },
            file,
            ensure_ascii=False,
            indent=2
        )
        file.write("\n")

    os.replace(
        temp_path,
        ARTICLE_HISTORY_FILE
    )


def _safe_string_list(value, limit=5):
    if not isinstance(
        value,
        list
    ):
        return []

    return [
        str(item).strip()
        for item in value[:limit]
        if str(item).strip()
    ]


def serialize_issue_article(item):
    article = item.get(
        "article",
        {}
    )
    summary_data = item.get(
        "summary_data",
        {}
    )

    try:
        actionability = int(
            summary_data.get(
                "actionability",
                0
            )
        )
    except (
        TypeError,
        ValueError
    ):
        actionability = 0

    action = summary_data.get(
        "action",
        {}
    )

    if not isinstance(
        action,
        dict
    ):
        action = {}

    action_steps = (
        _safe_string_list(
            action.get(
                "steps",
                []
            ),
            limit=3
        )
    )

    return {
        "company": article.get(
            "company",
            ""
        ),
        "title": article.get(
            "title",
            ""
        ),
        "link": article.get(
            "link",
            ""
        ),
        "published_at": article.get(
            "pub_date",
            ""
        ),
        "selection_score": article.get(
            "selection_score"
        ),
        "selection_reason": article.get(
            "selection_reason",
            ""
        ),
        "feedback_bias": article.get(
            "feedback_bias",
            0
        ),
        "one_line": str(
            summary_data.get(
                "one_line",
                ""
            )
        ).strip(),
        "key_points": _safe_string_list(
            summary_data.get(
                "key_points",
                []
            ),
            limit=3
        ),
        "topics": _safe_string_list(
            summary_data.get(
                "concepts",
                []
            ),
            limit=5
        ),
        "recommended_for": str(
            summary_data.get(
                "recommended_for",
                ""
            )
        ).strip(),
        "actionability": max(
            0,
            min(
                5,
                actionability
            )
        ),
        "action": {
            "type": str(
                action.get(
                    "type",
                    ""
                )
            ).strip(),
            "title": str(
                action.get(
                    "title",
                    ""
                )
            ).strip(),
            "steps": action_steps,
            "effort": str(
                action.get(
                    "effort",
                    ""
                )
            ).strip(),
        },
    }


def serialize_brief_article(article):
    return {
        "company": article.get(
            "company",
            ""
        ),
        "title": article.get(
            "title",
            ""
        ),
        "link": article.get(
            "link",
            ""
        ),
        "published_at": article.get(
            "pub_date",
            ""
        ),
        "selection_score": article.get(
            "selection_score"
        ),
        "selection_reason": article.get(
            "selection_reason",
            ""
        ),
        "feedback_bias": article.get(
            "feedback_bias",
            0
        ),
    }


def save_daily_issue(
    summarized_articles,
    brief_articles,
    editorial,
    top_indices,
    failed_blogs,
    candidate_count,
    excluded_count,
    unresolved_count
):
    now = datetime.now(
        ZoneInfo(
            "Asia/Seoul"
        )
    )
    issue_date = now.strftime(
        "%Y-%m-%d"
    )

    os.makedirs(
        DAILY_ISSUES_DIR,
        exist_ok=True
    )

    issue_path = os.path.join(
        DAILY_ISSUES_DIR,
        f"{issue_date}.json"
    )

    existing_issue_number = None

    if os.path.exists(
        issue_path
    ):
        try:
            with open(
                issue_path,
                "r",
                encoding="utf-8"
            ) as file:
                existing = json.load(
                    file
                )
                existing_issue_number = (
                    existing.get(
                        "issue_number"
                    )
                )
        except (
            OSError,
            json.JSONDecodeError
        ):
            existing_issue_number = None

    issue_files = [
        name
        for name in os.listdir(
            DAILY_ISSUES_DIR
        )
        if name.endswith(
            ".json"
        )
    ]

    issue_number = (
        existing_issue_number
        or len(
            issue_files
        ) + 1
    )

    top_set = set(
        top_indices
    )
    top_stories = []
    more_detailed = []

    for index, item in enumerate(
        summarized_articles,
        start=1
    ):
        serialized = (
            serialize_issue_article(
                item
            )
        )

        if index in top_set:
            serialized[
                "editorial_rank"
            ] = (
                top_indices.index(
                    index
                ) + 1
            )
            top_stories.append(
                serialized
            )
        else:
            more_detailed.append(
                serialized
            )

    top_stories.sort(
        key=lambda item: item.get(
            "editorial_rank",
            999
        )
    )

    issue = {
        "schema_version": 1,
        "issue_number": issue_number,
        "issue_date": issue_date,
        "generated_at": now.isoformat(),
        "profile_name": USER_PREFERENCES.get(
            "profile_name",
            "default"
        ),
        "editorial": (
            remove_internal_editorial_sections(
                editorial
            )
        ),
        "stats": {
            "candidate_count":
                candidate_count,
            "detailed_count":
                len(
                    summarized_articles
                ),
            "brief_count":
                len(
                    brief_articles
                ),
            "excluded_count":
                excluded_count,
            "unresolved_count":
                unresolved_count,
        },
        "top_stories": top_stories,
        "more_detailed":
            more_detailed,
        "brief_articles": [
            serialize_brief_article(
                article
            )
            for article in (
                brief_articles
            )
        ],
        "failed_sources": list(
            failed_blogs
        ),
    }

    temp_path = (
        issue_path
        + ".tmp"
    )

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            issue,
            file,
            ensure_ascii=False,
            indent=2
        )
        file.write(
            "\n"
        )

    os.replace(
        temp_path,
        issue_path
    )

    return issue_path


def _save_slack_feedback_state(items):
    os.makedirs(
        os.path.dirname(
            SLACK_FEEDBACK_STATE_FILE
        ),
        exist_ok=True
    )

    temp_path = (
        SLACK_FEEDBACK_STATE_FILE
        + ".tmp"
    )

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {
                "items": items,
                "updated_at": datetime.now(
                    ZoneInfo(
                        "Asia/Seoul"
                    )
                ).isoformat(),
            },
            file,
            ensure_ascii=False,
            indent=2
        )
        file.write("\n")

    os.replace(
        temp_path,
        SLACK_FEEDBACK_STATE_FILE
    )


def send_slack_feedback_cards(
    summarized_articles,
    top_indices
):
    if not (
        SLACK_BOT_TOKEN
        and SLACK_CHANNEL_ID
    ):
        print(
            "Slack feedback card 생략: "
            "SLACK_BOT_TOKEN/SLACK_CHANNEL_ID 미설정"
        )
        return []

    state_items = []

    for position, index in enumerate(
        top_indices,
        start=1
    ):
        if (
            index < 1
            or index > len(
                summarized_articles
            )
        ):
            continue

        item = summarized_articles[
            index - 1
        ]
        article = item[
            "article"
        ]

        summary_data = item.get(
            "summary_data",
            {}
        )

        topics = summary_data.get(
            "concepts",
            []
        )

        if not isinstance(
            topics,
            list
        ):
            topics = []

        text = "\n".join(
            [
                "🧭 *추천 피드백*",
                (
                    f"*{position}. "
                    f"{article['title']}*"
                ),
                (
                    f"{article['company']} · "
                    f"{article.get('selection_score')}/15"
                ),
                "",
                _extract_one_line_summary(
                    item
                ),
                "",
                "이 추천이 어땠는지 반응으로 알려주세요.",
                "👍 도움됨  👎 별로  🔥 이런 거 더  🙈 이 주제 줄이기",
                f"🔗 {article['link']}",
            ]
        )

        response = send_slack_text(
            text
        )

        timestamp = response.get(
            "ts"
        )

        if not timestamp:
            continue

        state_items.append(
            {
                "ts": timestamp,
                "channel": response.get(
                    "channel",
                    SLACK_CHANNEL_ID
                ),
                "article": {
                    "title": article[
                        "title"
                    ],
                    "company": article[
                        "company"
                    ],
                    "link": article[
                        "link"
                    ],
                    "score": article.get(
                        "selection_score"
                    ),
                    "topics": [
                        str(topic).strip()
                        for topic in topics[:5]
                        if str(topic).strip()
                    ],
                },
            }
        )

    if state_items:
        _save_slack_feedback_state(
            state_items
        )

    return state_items


def build_digest(
    summarized_articles,
    brief_articles,
    editorial,
    top_indices,
    failed_blogs,
    candidate_count,
    excluded_count,
    unresolved_count
):
    now = datetime.now(
        ZoneInfo(
            "Asia/Seoul"
        )
    )

    date_text = now.strftime(
        "%Y-%m-%d"
    )

    parts = [
        f"📰 *{date_text} GONY DAILY*",
        "",
        "개발자를 위한 매일의 기술신문 · AI · 데이터 · 자동화 · 백엔드",
        "",
        f"오늘 확인한 새 글: *{candidate_count}개*",
        (
            f"상세 브리핑: "
            f"*{len(summarized_articles)}개*"
        ),
        (
            f"추가로 볼 만한 글: "
            f"*{len(brief_articles)}개*"
        ),
        f"우선순위 낮음: *{excluded_count}개*",
        "",
        (
            "📰 오늘 신문 보기: "
            f"{NEWSPAPER_BASE_URL}/issues/{date_text}/"
        ),
    ]

    if unresolved_count:
        parts.append(
            f"평가 보류: *{unresolved_count}개*"
        )

    top_set = set(
        top_indices
    )

    if summarized_articles:
        parts.extend(
            [
                "",
                "━━━━━━━━━━━━━━━━━━",
                "🔥 *오늘 꼭 볼 글*",
                "",
            ]
        )

        for position, index in enumerate(
            top_indices,
            start=1
        ):
            if (
                index < 1
                or index > len(
                    summarized_articles
                )
            ):
                continue

            item = summarized_articles[
                index - 1
            ]

            article = item[
                "article"
            ]

            parts.extend(
                [
                    (
                        f"*{position}. "
                        f"{article['company']}* "
                        f"[{article.get('selection_score')}/15]"
                    ),
                    f"*{article['title']}*",
                    "",
                    item["summary"],
                    "",
                    f"🔗 {article['link']}",
                    "",
                ]
            )

        remaining = []

        for index, item in enumerate(
            summarized_articles,
            start=1
        ):
            if index in top_set:
                continue

            remaining.append(
                item
            )

        if remaining:
            parts.extend(
                [
                    "━━━━━━━━━━━━━━━━━━",
                    "📚 *그 외 상세 브리핑*",
                    "",
                ]
            )

            for item in remaining:
                article = item[
                    "article"
                ]

                one_line = item[
                    "summary"
                ]

                match = re.search(
                    r"\[한줄 요약\]\s*(.+?)(?:\n|$)",
                    one_line,
                    re.S
                )

                if match:
                    one_line = (
                        match
                        .group(1)
                        .strip()
                    )

                else:
                    one_line = (
                        one_line
                        .replace(
                            "\n",
                            " "
                        )
                        [:180]
                    )

                parts.extend(
                    [
                        (
                            f"• *{article['company']}* "
                            f"[{article.get('selection_score')}/15] "
                            f"— {article['title']}"
                        ),
                        f"  {one_line}",
                        f"  🔗 {article['link']}",
                        "",
                    ]
                )

    if brief_articles:
        parts.extend(
            [
                "━━━━━━━━━━━━━━━━━━",
                "👀 *추가로 볼 만한 글*",
                "",
            ]
        )

        for article in brief_articles:
            parts.extend(
                [
                    (
                        f"• *{article['company']}* "
                        f"[{article.get('selection_score')}/15] "
                        f"— {article['title']}"
                    ),
                    (
                        f"  {article.get('selection_reason', '')}"
                    ),
                    f"  🔗 {article['link']}",
                    "",
                ]
            )

    cleaned_editorial = (
        remove_internal_editorial_sections(
            editorial
        )
    )

    parts.extend(
        [
            "━━━━━━━━━━━━━━━━━━",
            "💡 *오늘의 편집 노트*",
            "",
            cleaned_editorial,
        ]
    )

    if failed_blogs:
        parts.extend(
            [
                "",
                "━━━━━━━━━━━━━━━━━━",
                "⚠️ *수집 실패*",
                ", ".join(
                    failed_blogs
                ),
            ]
        )

    return clean_slack_text(
        "\n".join(
            parts
        )
    )


def add_processed_articles(
    sent_articles,
    articles
):
    for article in articles:
        link = article.get(
            "link"
        )

        if link:
            sent_articles.append(
                link
            )


def main():
    sent_articles = load_sent_articles()

    enabled_blogs = [
        blog
        for blog in BLOGS
        if blog.get(
            "enabled",
            True
        )
    ]

    candidate_articles = []
    failed_blogs = []

    print(
        "================================"
    )

    print(
        "GONY DAILY Bot 시작"
    )

    print(
        "설정 프로필:",
        USER_PREFERENCES["profile_name"]
    )

    print(
        "관심사 개수:",
        len(
            USER_PREFERENCES["interests"]
        )
    )

    print(
        "상세 브리핑 기준:",
        DETAILED_SCORE_THRESHOLD
    )

    print(
        "짧은 소개 기준:",
        BRIEF_SCORE_THRESHOLD
    )

    if not USER_PREFERENCES["delivery"]["daily_digest"]:
        print(
            "daily_digest 설정이 false라 실행을 종료합니다."
        )
        return

    print(
        "활성 블로그:",
        len(
            enabled_blogs
        )
    )

    print(
        "기존 처리 기록:",
        len(
            sent_articles
        )
    )

    print(
        "================================"
    )

    for blog in enabled_blogs:
        try:
            print()
            print(
                "=" * 60
            )

            print(
                "확인 중:",
                blog["name"]
            )

            recent_limit = blog.get(
                "recent_limit",
                DEFAULT_RECENT_ARTICLE_LIMIT
            )

            print(
                "최근 확인 범위:",
                recent_limit
            )

            articles = get_recent_articles(
                blog,
                recent_limit
            )

            new_articles = [
                article
                for article in articles
                if article["link"]
                and article["link"]
                not in sent_articles
            ]

            print(
                "새 글 수:",
                len(
                    new_articles
                )
            )

            new_articles.reverse()

            candidate_articles.extend(
                new_articles
            )

        except Exception as error:
            print(
                "[오류]",
                blog["name"],
                repr(
                    error
                )
            )

            failed_blogs.append(
                blog["name"]
            )

    print()
    print(
        "중복 제거 전 새 글 후보:",
        len(
            candidate_articles
        )
    )

    candidate_articles = (
        deduplicate_candidate_articles(
            candidate_articles
        )
    )

    print(
        "중복 제거 후 새 글 후보:",
        len(
            candidate_articles
        )
    )

    if not candidate_articles:
        print(
            "새 글이 없습니다."
        )

        return

    print()
    print(
        "Gemini 1차 기사 선별 시작"
    )

    (
        detailed_articles,
        brief_articles,
        excluded_articles,
        unresolved_selection_articles,
    ) = select_relevant_articles(
        candidate_articles
    )

    print()
    print(
        "1차 선별 완료"
    )

    print(
        "상세 요약 대상:",
        len(
            detailed_articles
        )
    )

    print(
        "짧게 소개할 글:",
        len(
            brief_articles
        )
    )

    print(
        "선별 제외:",
        len(
            excluded_articles
        )
    )

    print(
        "선별 평가 보류:",
        len(
            unresolved_selection_articles
        )
    )

    print()
    print(
        "상세 요약 시작"
    )

    (
        summarized_articles,
        unresolved_detail_articles,
    ) = summarize_article_batches(
        detailed_articles
    )

    unresolved_articles = (
        unresolved_selection_articles
        + unresolved_detail_articles
    )

    if (
        not summarized_articles
        and not brief_articles
    ):
        print(
            "오늘 Slack으로 보낼 우선순위 글이 없습니다."
        )

        add_processed_articles(
            sent_articles,
            excluded_articles
        )

        save_sent_articles(
            sent_articles
        )

        print(
            "우선순위가 낮은 글은 "
            "처리 기록에 저장했습니다."
        )

        print(
            "평가 보류 글은 "
            "다음 실행에서 다시 확인합니다."
        )

        return

    print()
    print(
        "오늘의 편집 브리핑 생성"
    )

    try:
        editorial = create_daily_editorial(
            summarized_articles,
            brief_articles
        )

    except Exception as error:
        print(
            "편집 브리핑 생성 실패:",
            repr(
                error
            )
        )

        editorial = (
            "[오늘의 기술 키워드]\n"
            "편집 요약 생성 실패\n\n"
            "[오늘의 한줄 포인트]\n"
            "선별된 개별 글은 정상적으로 준비되었습니다."
        )

    top_indices = parse_top_indices(
        editorial
    )

    if (
        summarized_articles
        and not top_indices
    ):
        top_indices = list(
            range(
                1,
                min(
                    3,
                    len(
                        summarized_articles
                    )
                ) + 1
            )
        )

    digest = build_digest(
        summarized_articles,
        brief_articles,
        editorial,
        top_indices,
        failed_blogs,
        candidate_count=len(
            candidate_articles
        ),
        excluded_count=len(
            excluded_articles
        ),
        unresolved_count=len(
            unresolved_articles
        )
    )

    try:
        issue_path = save_daily_issue(
            summarized_articles,
            brief_articles,
            editorial,
            top_indices,
            failed_blogs,
            candidate_count=len(
                candidate_articles
            ),
            excluded_count=len(
                excluded_articles
            ),
            unresolved_count=len(
                unresolved_articles
            )
        )
        print(
            "GONY DAILY issue 저장:",
            issue_path
        )
    except Exception as error:
        print(
            "GONY DAILY issue 저장 실패:",
            repr(error)
        )

    messages = split_slack_messages(
        digest
    )

    for index, message in enumerate(
        messages,
        start=1
    ):
        print(
            f"Slack 발송 "
            f"{index}/{len(messages)}"
        )

        send_slack_text(
            message
        )

    try:
        save_article_history(
            summarized_articles
        )
        print(
            "Trend Radar 기사 이력 저장:",
            len(
                summarized_articles
            ),
            "개"
        )
    except Exception as error:
        print(
            "기사 이력 저장 실패:",
            repr(error)
        )

    try:
        feedback_items = (
            send_slack_feedback_cards(
                summarized_articles,
                top_indices
            )
        )

        if feedback_items:
            print(
                "Slack 피드백 카드:",
                len(feedback_items),
                "개"
            )

    except Exception as error:
        print(
            "Slack 피드백 카드 생성 실패:",
            repr(error)
        )

    successfully_processed = []

    successfully_processed.extend(
        excluded_articles
    )

    successfully_processed.extend(
        brief_articles
    )

    successfully_processed.extend(
        [
            item["article"]
            for item in summarized_articles
        ]
    )

    add_processed_articles(
        sent_articles,
        successfully_processed
    )

    save_sent_articles(
        sent_articles
    )

    print()
    print(
        "브리핑 발송 완료"
    )

    print(
        "전체 후보:",
        len(
            candidate_articles
        )
    )

    print(
        "상세 브리핑:",
        len(
            summarized_articles
        )
    )

    print(
        "짧은 소개:",
        len(
            brief_articles
        )
    )

    print(
        "선별 제외:",
        len(
            excluded_articles
        )
    )

    print(
        "평가 보류:",
        len(
            unresolved_articles
        )
    )


if __name__ == "__main__":
    main()
