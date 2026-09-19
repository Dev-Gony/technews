import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo


SLACK_BOT_TOKEN = os.environ.get(
    "SLACK_BOT_TOKEN",
    "",
).strip()

STATE_FILE = "config/slack_feedback_state.json"
FEEDBACK_FILE = "config/slack_feedback.json"

REACTION_MAP = {
    "+1": "helpful",
    "-1": "not_helpful",
    "fire": "more_like_this",
    "see_no_evil": "less_like_this",
}


def _slack_api_request(method, payload):
    if not SLACK_BOT_TOKEN:
        raise RuntimeError(
            "SLACK_BOT_TOKEN이 없습니다."
        )

    request = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(
            payload
        ).encode(
            "utf-8"
        ),
        headers={
            "Authorization":
                f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type":
                "application/json; charset=utf-8",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
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


def _load_json(path, default):
    if not os.path.exists(
        path
    ):
        return default

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(
                file
            )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return default


def _save_json(path, data):
    directory = os.path.dirname(
        path
    )

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    temp_path = path + ".tmp"

    with open(
        temp_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    os.replace(
        temp_path,
        path,
    )


def _reaction_counts(message):
    counts = {
        value: 0
        for value in REACTION_MAP.values()
    }

    for reaction in message.get(
        "reactions",
        [],
    ):
        reaction_name = reaction.get(
            "name"
        )

        feedback_name = (
            REACTION_MAP.get(
                reaction_name
            )
        )

        if not feedback_name:
            continue

        try:
            count = int(
                reaction.get(
                    "count",
                    0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            count = 0

        counts[
            feedback_name
        ] = max(
            0,
            count,
        )

    return counts


def _feedback_key(item):
    article = item.get(
        "article",
        {}
    )

    return (
        article.get(
            "link"
        )
        or item.get(
            "ts"
        )
        or ""
    )


def sync_feedback():
    state = _load_json(
        STATE_FILE,
        {
            "items": [],
        },
    )

    items = state.get(
        "items",
        [],
    )

    feedback = _load_json(
        FEEDBACK_FILE,
        {
            "articles": {},
        },
    )

    articles = feedback.get(
        "articles",
        {},
    )

    if not isinstance(
        articles,
        dict,
    ):
        articles = {}

    updated = 0

    for item in items:
        channel = item.get(
            "channel"
        )
        timestamp = item.get(
            "ts"
        )

        if not (
            channel
            and timestamp
        ):
            continue

        response = (
            _slack_api_request(
                "reactions.get",
                {
                    "channel": channel,
                    "timestamp": timestamp,
                    "full": True,
                },
            )
        )

        message = response.get(
            "message",
            {},
        )

        counts = _reaction_counts(
            message
        )

        key = _feedback_key(
            item
        )

        if not key:
            continue

        previous = articles.get(
            key,
            {},
        )

        next_record = {
            "article": item.get(
                "article",
                {},
            ),
            "slack": {
                "channel": channel,
                "ts": timestamp,
            },
            "feedback": counts,
            "updated_at": datetime.now(
                ZoneInfo(
                    "Asia/Seoul"
                )
            ).isoformat(),
        }

        if previous != next_record:
            articles[
                key
            ] = next_record
            updated += 1

    feedback[
        "articles"
    ] = articles

    feedback[
        "updated_at"
    ] = datetime.now(
        ZoneInfo(
            "Asia/Seoul"
        )
    ).isoformat()

    _save_json(
        FEEDBACK_FILE,
        feedback,
    )

    print(
        "Slack 피드백 동기화 완료:",
        updated,
        "개 갱신",
    )


if __name__ == "__main__":
    sync_feedback()
