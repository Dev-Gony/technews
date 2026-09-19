import json
import os
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import main as technews


ARTICLE_HISTORY_FILE = "config/article_history.json"
MIN_TOPIC_COUNT = 2
MAX_TOPICS = 5


def _parse_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value
        )
    except ValueError:
        return None


def load_history(
    path=ARTICLE_HISTORY_FILE
):
    if not os.path.exists(
        path
    ):
        return []

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
        return []

    articles = data.get(
        "articles",
        []
    )

    if not isinstance(
        articles,
        list
    ):
        return []

    return [
        article
        for article in articles
        if isinstance(
            article,
            dict
        )
    ]


def _topic_counts(
    articles
):
    counts = Counter()

    for article in articles:
        topics = article.get(
            "topics",
            []
        )

        if not isinstance(
            topics,
            list
        ):
            continue

        unique_topics = {
            str(topic).strip()
            for topic in topics
            if str(topic).strip()
        }

        counts.update(
            unique_topics
        )

    return counts


def split_windows(
    articles,
    now=None
):
    now = (
        now
        or datetime.now(
            ZoneInfo(
                "Asia/Seoul"
            )
        )
    )

    current_start = (
        now
        - timedelta(
            days=7
        )
    )
    previous_start = (
        now
        - timedelta(
            days=14
        )
    )

    current = []
    previous = []

    for article in articles:
        recorded_at = _parse_datetime(
            article.get(
                "recorded_at"
            )
        )

        if recorded_at is None:
            continue

        if recorded_at.tzinfo is None:
            recorded_at = (
                recorded_at.replace(
                    tzinfo=now.tzinfo
                )
            )

        if (
            current_start
            <= recorded_at
            <= now
        ):
            current.append(
                article
            )

        elif (
            previous_start
            <= recorded_at
            < current_start
        ):
            previous.append(
                article
            )

    return (
        current,
        previous,
    )


def find_rising_topics(
    current_articles,
    previous_articles
):
    current_counts = (
        _topic_counts(
            current_articles
        )
    )
    previous_counts = (
        _topic_counts(
            previous_articles
        )
    )

    rows = []

    for topic, current_count in (
        current_counts.items()
    ):
        if (
            current_count
            < MIN_TOPIC_COUNT
        ):
            continue

        previous_count = (
            previous_counts.get(
                topic,
                0
            )
        )

        delta = (
            current_count
            - previous_count
        )

        if delta <= 0:
            continue

        ratio = (
            current_count
            / max(
                1,
                previous_count
            )
        )

        rows.append(
            {
                "topic": topic,
                "current_count":
                    current_count,
                "previous_count":
                    previous_count,
                "delta": delta,
                "ratio": ratio,
            }
        )

    rows.sort(
        key=lambda row: (
            row[
                "delta"
            ],
            row[
                "current_count"
            ],
            row[
                "ratio"
            ],
        ),
        reverse=True,
    )

    return rows[
        :MAX_TOPICS
    ]


def _articles_for_topic(
    topic,
    articles,
    limit=4
):
    matched = []

    for article in articles:
        topics = article.get(
            "topics",
            []
        )

        if topic not in topics:
            continue

        matched.append(
            article
        )

    matched.sort(
        key=lambda article: (
            article.get(
                "selection_score"
            )
            or 0,
            article.get(
                "actionability"
            )
            or 0,
        ),
        reverse=True,
    )

    return matched[
        :limit
    ]


def build_radar_prompt(
    rising_topics,
    current_articles
):
    sections = []

    for row in rising_topics:
        topic = row[
            "topic"
        ]

        articles = (
            _articles_for_topic(
                topic,
                current_articles,
            )
        )

        article_lines = []

        for article in articles:
            article_lines.append(
                (
                    f"- {article.get('company', '')}: "
                    f"{article.get('title', '')}\n"
                    f"  요약: {article.get('one_line', '')}"
                )
            )

        sections.append(
            "\n".join(
                [
                    (
                        f"주제: {topic}"
                    ),
                    (
                        "최근 7일: "
                        f"{row['current_count']}건"
                    ),
                    (
                        "이전 7일: "
                        f"{row['previous_count']}건"
                    ),
                    (
                        "증가: "
                        f"+{row['delta']}건"
                    ),
                    "관련 기사:",
                    (
                        "\n".join(
                            article_lines
                        )
                        or "- 없음"
                    ),
                ]
            )
        )

    combined = (
        "\n\n".join(
            sections
        )
    )

    return f"""
너는 개발자를 위한 주간 기술 Trend Radar 편집자다.

아래 데이터는 실제 수집된 기술 기사 metadata를
최근 7일과 이전 7일로 비교한 결과다.

{combined}

각 주제에 대해 다음 세 가지를 작성한다.

1. 흐름:
최근 기사들이 어떤 방향으로 모이고 있는지 1~2문장

2. 왜 주목할까:
개발자 관점에서 왜 볼 가치가 있는지 1문장

3. 해볼 것:
관련 기사에 근거해 30~60분 안에 시도할 수 있는 학습 또는 실험 1개

규칙:
- 제공된 기사 내용 밖의 사실을 추측하지 않는다.
- 단순히 기사 개수가 늘었다는 말만 반복하지 않는다.
- 실제 내용의 공통점이나 변화 방향을 설명한다.
- 과장된 표현을 쓰지 않는다.
- 각 주제마다 짧고 명확하게 작성한다.
- Slack에서 읽기 쉬운 한국어로 작성한다.
"""


def build_radar_message(
    rising_topics,
    synthesis,
    current_count,
    previous_count,
    now=None,
):
    now = (
        now
        or datetime.now(
            ZoneInfo(
                "Asia/Seoul"
            )
        )
    )

    parts = [
        (
            "📡 *Weekly Tech Radar* "
            f"({now.strftime('%Y-%m-%d')})"
        ),
        "",
        (
            f"최근 7일 상세 기사: "
            f"*{current_count}개*"
        ),
        (
            f"이전 7일 상세 기사: "
            f"*{previous_count}개*"
        ),
        "",
    ]

    if not rising_topics:
        parts.extend(
            [
                "뚜렷하게 상승한 기술 주제가 아직 없습니다.",
                (
                    "기사 이력이 더 쌓이면 "
                    "7일 단위 변화를 비교합니다."
                ),
            ]
        )

        return "\n".join(
            parts
        )

    parts.append(
        "🔥 *상승 중인 주제*"
    )

    for row in rising_topics:
        parts.append(
            (
                f"• {row['topic']}: "
                f"{row['previous_count']} → "
                f"{row['current_count']}건"
            )
        )

    parts.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━",
            "🧭 *흐름 해석*",
            "",
            technews.clean_slack_text(
                synthesis
            ),
        ]
    )

    return "\n".join(
        parts
    )


def create_weekly_radar(
    history_path=ARTICLE_HISTORY_FILE
):
    articles = load_history(
        history_path
    )

    current, previous = (
        split_windows(
            articles
        )
    )

    rising = find_rising_topics(
        current,
        previous,
    )

    if rising:
        prompt = build_radar_prompt(
            rising,
            current,
        )

        synthesis = (
            technews.call_gemini(
                prompt
            )
        )
    else:
        synthesis = ""

    message = build_radar_message(
        rising,
        synthesis,
        len(
            current
        ),
        len(
            previous
        ),
    )

    technews.send_slack_text(
        message
    )

    print(
        "Weekly Tech Radar 발송 완료"
    )


if __name__ == "__main__":
    create_weekly_radar()
