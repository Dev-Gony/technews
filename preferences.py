import json
import os


USER_PREFERENCES_FILE = "config/user_preferences.json"

DEFAULT_PREFERENCES = {
    "profile_name": "default",
    "interests": [
        "AI Agent",
        "Agentic Workflow",
        "LLM",
        "RAG",
        "MCP",
        "Python",
        "데이터 분석",
        "SQL",
        "업무 자동화",
        "서버",
        "클라우드",
        "백엔드 아키텍처",
        "비용 절감",
        "성능 개선",
        "개발 생산성",
        "Developer Tools",
        "GitHub 및 소프트웨어 개발 워크플로",
    ],
    "avoid_topics": [],
    "scoring": {
        "detailed_threshold": 11,
        "brief_threshold": 9,
    },
    "delivery": {
        "daily_digest": True,
        "language": "ko",
    },
}


def _copy_default_preferences():
    return json.loads(
        json.dumps(
            DEFAULT_PREFERENCES,
            ensure_ascii=False,
        )
    )


def _clean_string_list(value, fallback):
    if not isinstance(value, list):
        return list(fallback)

    cleaned = []

    for item in value:
        if not isinstance(item, str):
            continue

        item = item.strip()

        if item and item not in cleaned:
            cleaned.append(item)

    if not cleaned and fallback:
        return list(fallback)

    return cleaned


def _clean_threshold(value, fallback):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback

    return max(0, min(15, value))


def validate_preferences(raw_preferences):
    defaults = _copy_default_preferences()

    if not isinstance(raw_preferences, dict):
        return defaults

    profile_name = raw_preferences.get(
        "profile_name",
        defaults["profile_name"],
    )

    if not isinstance(profile_name, str) or not profile_name.strip():
        profile_name = defaults["profile_name"]

    interests = _clean_string_list(
        raw_preferences.get("interests"),
        defaults["interests"],
    )

    avoid_topics = _clean_string_list(
        raw_preferences.get("avoid_topics"),
        [],
    )

    raw_scoring = raw_preferences.get("scoring", {})

    if not isinstance(raw_scoring, dict):
        raw_scoring = {}

    detailed_threshold = _clean_threshold(
        raw_scoring.get("detailed_threshold"),
        defaults["scoring"]["detailed_threshold"],
    )

    brief_threshold = _clean_threshold(
        raw_scoring.get("brief_threshold"),
        defaults["scoring"]["brief_threshold"],
    )

    if brief_threshold > detailed_threshold:
        print(
            "사용자 설정 경고: "
            "brief_threshold가 detailed_threshold보다 높아 "
            "기본 점수 기준을 사용합니다."
        )

        brief_threshold = defaults["scoring"]["brief_threshold"]
        detailed_threshold = defaults["scoring"]["detailed_threshold"]

    raw_delivery = raw_preferences.get("delivery", {})

    if not isinstance(raw_delivery, dict):
        raw_delivery = {}

    daily_digest = raw_delivery.get(
        "daily_digest",
        defaults["delivery"]["daily_digest"],
    )

    if not isinstance(daily_digest, bool):
        daily_digest = defaults["delivery"]["daily_digest"]

    language = raw_delivery.get(
        "language",
        defaults["delivery"]["language"],
    )

    if language != "ko":
        print(
            "사용자 설정 경고: 현재 language는 ko만 지원합니다. "
            "ko로 처리합니다."
        )
        language = "ko"

    return {
        "profile_name": profile_name.strip(),
        "interests": interests,
        "avoid_topics": avoid_topics,
        "scoring": {
            "detailed_threshold": detailed_threshold,
            "brief_threshold": brief_threshold,
        },
        "delivery": {
            "daily_digest": daily_digest,
            "language": language,
        },
    }


def load_user_preferences(path=USER_PREFERENCES_FILE):
    if not os.path.exists(path):
        print(
            f"사용자 설정 파일 없음: {path}"
        )
        print(
            "기본 사용자 설정을 사용합니다."
        )
        return _copy_default_preferences()

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            raw_preferences = json.load(file)

    except (OSError, json.JSONDecodeError) as error:
        print(
            "사용자 설정 읽기 실패:",
            error,
        )
        print(
            "기본 사용자 설정을 사용합니다."
        )
        return _copy_default_preferences()

    return validate_preferences(
        raw_preferences
    )
