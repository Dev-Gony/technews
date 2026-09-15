import html
import json
import re

import main as technews
from preferences import load_user_preferences


DIGEST_RECENT_LIMIT = 5
DIGEST_SHORTLIST_LIMIT = 25
DIGEST_RESULT_LIMIT = 3
DIGEST_PREVIEW_LENGTH = 350
DIGEST_TITLE_LENGTH = 90
DIGEST_TEXT_LENGTH = 140


def _normalize_text(text):
    text = str(text or "").casefold()
    text = re.sub(r"[^0-9a-z가-힣+#. ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clip_text(text, limit):
    text = re.sub(r"\s+", " ", str(text or "")).strip()

    if len(text) <= limit:
        return text

    return text[: limit - 1].rstrip() + "…"


def _escape(text, limit=None):
    if limit is not None:
        text = _clip_text(text, limit)

    return html.escape(str(text or ""), quote=True)


def _query_tokens(query):
    normalized = _normalize_text(query)
    tokens = [
        token
        for token in normalized.split()
        if len(token) >= 2
    ]
    return list(dict.fromkeys(tokens))


def _heuristic_score(article, query):
    title = _normalize_text(article.get("title"))
    preview = _normalize_text(
        technews.get_prefilter_text(article)
    )
    combined = f"{title} {preview}"

    normalized_query = _normalize_text(query)
    tokens = _query_tokens(query)

    score = 0

    if normalized_query and normalized_query in combined:
        score += 8

    for token in tokens:
        if token in title:
            score += 4
        elif token in preview:
            score += 2

    return score


def collect_digest_candidates(query):
    articles = []
    failed_sources = []

    for blog in technews.BLOGS:
        if not blog.get("enabled", True):
            continue

        try:
            recent_limit = min(
                blog.get(
                    "recent_limit",
                    DIGEST_RECENT_LIMIT,
                ),
                DIGEST_RECENT_LIMIT,
            )

            articles.extend(
                technews.get_recent_articles(
                    blog,
                    recent_limit,
                )
            )
        except Exception as error:
            print(
                "Telegram digest 수집 실패:",
                blog["name"],
                repr(error),
            )
            failed_sources.append(blog["name"])

    articles = technews.deduplicate_candidate_articles(
        articles
    )

    scored = [
        (
            _heuristic_score(article, query),
            article,
        )
        for article in articles
    ]

    matched = [
        item
        for item in scored
        if item[0] > 0
    ]

    pool = matched or scored
    pool.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    candidates = [
        article
        for _, article in pool[:DIGEST_SHORTLIST_LIMIT]
    ]

    return candidates, failed_sources


def _build_rank_prompt(query, articles, preferences):
    rows = []

    for index, article in enumerate(
        articles,
        start=1,
    ):
        preview = technews.get_prefilter_text(
            article
        )[:DIGEST_PREVIEW_LENGTH]

        rows.append(
            "\n".join(
                [
                    f"기사 번호: {index}",
                    f"출처: {article['company']}",
                    f"제목: {article['title']}",
                    f"미리보기: {preview or '(없음)'}",
                ]
            )
        )

    interests = ", ".join(
        preferences.get("interests", [])
    )

    combined = "\n\n".join(rows)

    return f"""
너는 개발자용 기술 뉴스 에이전트다.

사용자가 Telegram에서 다음 주제로 즉시 브리핑을 요청했다.
요청 주제: {query}

사용자의 평소 관심사:
{interests}

아래 후보 기사들을 평가하고 요청 주제와 가장 관련 있고 실제로 읽을 가치가 높은 기사 최대 {DIGEST_RESULT_LIMIT}개를 고른다.

평가 기준:
- query_relevance: 요청 주제와의 직접 관련성 0~5
- practical_value: 프로젝트/학습/실무 활용 가치 0~5
- significance: 기술적 중요도 0~5

단순히 키워드가 제목에 있다는 이유만으로 높게 평가하지 않는다.
요청 주제와 실제 내용이 연결되는지를 우선한다.

결과는 JSON 배열만 반환한다.
선정 가치가 있는 기사가 없으면 빈 배열 []을 반환한다.

형식:
[
  {{
    "index": 1,
    "query_relevance": 5,
    "practical_value": 4,
    "significance": 4,
    "reason": "선정 이유"
  }}
]

기사 후보:
{combined}
"""


def rank_digest_candidates(query, articles):
    if not articles:
        return []

    preferences = load_user_preferences()
    prompt = _build_rank_prompt(
        query,
        articles,
        preferences,
    )

    result = technews.call_gemini(prompt)
    parsed = json.loads(
        technews.extract_json_text(result)
    )

    if not isinstance(parsed, list):
        return []

    ranked = []

    for item in parsed:
        if not isinstance(item, dict):
            continue

        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue

        if index < 1 or index > len(articles):
            continue

        def clamp_score(name):
            try:
                value = int(item.get(name, 0))
            except (TypeError, ValueError):
                value = 0
            return max(0, min(5, value))

        total = (
            clamp_score("query_relevance")
            + clamp_score("practical_value")
            + clamp_score("significance")
        )

        if clamp_score("query_relevance") < 3:
            continue

        ranked.append(
            {
                "article": articles[index - 1],
                "score": total,
                "reason": str(
                    item.get("reason", "")
                ).strip(),
            }
        )

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return ranked[:DIGEST_RESULT_LIMIT]


def _build_summary_prompt(query, ranked_items):
    rows = []

    for index, item in enumerate(
        ranked_items,
        start=1,
    ):
        article = item["article"]
        content = technews.get_article_content(
            article
        )

        if not content:
            content = technews.get_prefilter_text(
                article
            )

        rows.append(
            f"""
기사 번호: {index}
출처: {article['company']}
제목: {article['title']}
선정 점수: {item['score']}/15
선정 이유: {item['reason']}
본문 또는 미리보기:
{content[:5000]}
"""
        )

    return f"""
너는 Telegram에서 답하는 기술 뉴스 에이전트다.

사용자 요청 주제: {query}

아래 기사들을 각각 한국어로 아주 간결하게 요약한다.

각 기사마다:
- one_line: 핵심 한 문장
- why_it_matters: 왜 지금 읽을 가치가 있는지 한 문장
- takeaway: 사용자가 가져갈 실무/학습 포인트 한 문장

제공된 내용 밖의 사실을 만들지 않는다.
각 문장은 모바일 메신저에서 빠르게 읽을 수 있도록 짧고 직접적으로 쓴다.
결과는 JSON 배열만 반환한다.

형식:
[
  {{
    "index": 1,
    "one_line": "...",
    "why_it_matters": "...",
    "takeaway": "..."
  }}
]

기사:
{"\n".join(rows)}
"""


def summarize_digest(query, ranked_items):
    if not ranked_items:
        return []

    result = technews.call_gemini(
        _build_summary_prompt(
            query,
            ranked_items,
        )
    )

    parsed = json.loads(
        technews.extract_json_text(result)
    )

    if not isinstance(parsed, list):
        return []

    summaries = {}

    for item in parsed:
        if not isinstance(item, dict):
            continue

        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue

        if 1 <= index <= len(ranked_items):
            summaries[index] = item

    output = []

    for index, ranked in enumerate(
        ranked_items,
        start=1,
    ):
        summary = summaries.get(index, {})
        output.append(
            {
                **ranked,
                "summary": summary,
            }
        )

    return output


def build_digest_message(query, items, failed_sources=None):
    failed_sources = failed_sources or []

    if not items:
        return (
            f"'{_escape(query)}' 주제로 지금 확인한 기술 소스에서는 "
            "추천할 만한 새 글을 찾지 못했습니다."
        )

    lines = [
        f"🔎 <b>{_escape(query, 60)} Tech Digest</b>",
        f"지금 볼 만한 기사 {len(items)}개를 골랐어요.",
        "",
    ]

    for position, item in enumerate(
        items,
        start=1,
    ):
        article = item["article"]
        summary = item.get("summary", {})
        one_line = (
            summary.get("one_line")
            or item.get("reason")
            or ""
        )
        why_it_matters = summary.get(
            "why_it_matters",
            "",
        )
        takeaway = summary.get(
            "takeaway",
            "",
        )

        lines.extend(
            [
                (
                    f"<b>{position}. "
                    f"{_escape(article['title'], DIGEST_TITLE_LENGTH)}</b>"
                ),
                (
                    f"{_escape(article['company'], 40)}"
                    f" · {item['score']}/15"
                ),
                _escape(one_line, DIGEST_TEXT_LENGTH),
            ]
        )

        if why_it_matters:
            lines.append(
                f"💡 {_escape(why_it_matters, DIGEST_TEXT_LENGTH)}"
            )

        if takeaway:
            lines.append(
                f"🛠 {_escape(takeaway, DIGEST_TEXT_LENGTH)}"
            )

        lines.extend(
            [
                (
                    f"<a href=\"{_escape(article['link'])}\">"
                    "원문 보기 ↗</a>"
                ),
                "",
            ]
        )

    if failed_sources:
        lines.append(
            f"ℹ️ 일부 소스 {len(failed_sources)}곳은 수집하지 못했어요."
        )

    return "\n".join(lines).strip()[:3900]


def create_on_demand_digest(query):
    query = str(query or "").strip()

    if not query:
        return "주제를 입력해주세요. 예: /digest MCP"

    if len(query) > 80:
        return "검색 주제는 80자 이하로 입력해주세요."

    print(
        "Telegram digest 요청:",
        query,
    )

    candidates, failed_sources = (
        collect_digest_candidates(query)
    )

    print(
        "Telegram digest 후보:",
        len(candidates),
    )

    ranked = rank_digest_candidates(
        query,
        candidates,
    )

    print(
        "Telegram digest 최종 선정:",
        len(ranked),
    )

    summarized = summarize_digest(
        query,
        ranked,
    )

    return build_digest_message(
        query,
        summarized,
        failed_sources,
    )
