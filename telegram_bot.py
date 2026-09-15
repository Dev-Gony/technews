import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from preferences import (
    USER_PREFERENCES_FILE,
    load_user_preferences,
    save_user_preferences,
)


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_ALLOWED_CHAT_ID = os.environ.get(
    "TELEGRAM_ALLOWED_CHAT_ID",
    "",
).strip()

TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_OFFSET_FILE = "runtime/telegram_offset.json"


def parse_command(text):
    if not isinstance(text, str):
        return "", ""

    text = text.strip()

    if not text.startswith("/"):
        return "", ""

    first, *rest = text.split(maxsplit=1)
    command = first.split("@", 1)[0].lower()
    argument = rest[0].strip() if rest else ""

    return command, argument


def _find_interest_index(interests, keyword):
    target = keyword.casefold()

    for index, interest in enumerate(interests):
        if interest.casefold() == target:
            return index

    return None


def _format_interests(preferences):
    interests = preferences["interests"]
    scoring = preferences["scoring"]

    lines = [
        f"프로필: {preferences['profile_name']}",
        f"관심사: {len(interests)}개",
        "",
    ]

    for index, interest in enumerate(
        interests,
        start=1,
    ):
        lines.append(
            f"{index}. {interest}"
        )

    lines.extend(
        [
            "",
            (
                "상세 브리핑 기준: "
                f"{scoring['detailed_threshold']}점 이상"
            ),
            (
                "짧은 소개 기준: "
                f"{scoring['brief_threshold']}점 이상"
            ),
        ]
    )

    return "\n".join(lines)


def _help_text():
    return "\n".join(
        [
            "Tech News Bot 설정 명령",
            "",
            "/interests - 현재 관심사 확인",
            "/add 키워드 - 관심사 추가",
            "/remove 키워드 - 관심사 삭제",
            "/chatid - 현재 Telegram chat id 확인",
            "/help - 명령 도움말",
            "",
            "예시:",
            "/add FinOps",
            "/remove SQL",
        ]
    )


def handle_preference_command(
    text,
    preference_path=USER_PREFERENCES_FILE,
):
    command, argument = parse_command(
        text
    )

    if command in {"/start", "/help"}:
        return _help_text(), False

    preferences = load_user_preferences(
        preference_path
    )

    if command == "/interests":
        return _format_interests(
            preferences
        ), False

    if command == "/add":
        if not argument:
            return (
                "추가할 관심사를 입력해주세요.\n"
                "예: /add MCP",
                False,
            )

        if len(argument) > 80:
            return (
                "관심사는 80자 이하로 입력해주세요.",
                False,
            )

        interests = preferences["interests"]

        if _find_interest_index(
            interests,
            argument,
        ) is not None:
            return (
                f"이미 등록된 관심사입니다: {argument}",
                False,
            )

        interests.append(
            argument
        )

        save_user_preferences(
            preferences,
            preference_path,
        )

        return (
            f"관심사를 추가했습니다: {argument}\n"
            f"현재 관심사: {len(interests)}개",
            True,
        )

    if command == "/remove":
        if not argument:
            return (
                "삭제할 관심사를 입력해주세요.\n"
                "예: /remove SQL",
                False,
            )

        interests = preferences["interests"]
        index = _find_interest_index(
            interests,
            argument,
        )

        if index is None:
            return (
                f"등록되지 않은 관심사입니다: {argument}",
                False,
            )

        if len(interests) <= 1:
            return (
                "관심사는 최소 1개 이상 유지해야 합니다.",
                False,
            )

        removed = interests.pop(
            index
        )

        save_user_preferences(
            preferences,
            preference_path,
        )

        return (
            f"관심사를 삭제했습니다: {removed}\n"
            f"현재 관심사: {len(interests)}개",
            True,
        )

    if command == "/chatid":
        return "__CHAT_ID__", False

    if command:
        return (
            "지원하지 않는 명령입니다.\n"
            "/help를 입력해 사용 가능한 명령을 확인해주세요.",
            False,
        )

    return (
        "명령 형식으로 입력해주세요.\n"
        "/help를 입력하면 사용 가능한 명령을 볼 수 있습니다.",
        False,
    )


def _telegram_request(
    method,
    payload=None,
):
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN이 없습니다."
        )

    url = (
        f"{TELEGRAM_API_BASE}/bot"
        f"{TELEGRAM_BOT_TOKEN}/{method}"
    )

    encoded = urllib.parse.urlencode(
        payload or {}
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "Content-Type": (
                "application/x-www-form-urlencoded"
            )
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=45,
    ) as response:
        result = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    if not result.get("ok"):
        raise RuntimeError(
            "Telegram API 요청에 실패했습니다."
        )

    return result.get("result")


def get_updates(offset=None):
    payload = {
        "timeout": 30,
        "allowed_updates": json.dumps(
            ["message"]
        ),
    }

    if offset is not None:
        payload["offset"] = offset

    return _telegram_request(
        "getUpdates",
        payload,
    )


def send_message(chat_id, text):
    return _telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
        },
    )


def load_offset():
    if not os.path.exists(
        TELEGRAM_OFFSET_FILE
    ):
        return None

    try:
        with open(
            TELEGRAM_OFFSET_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        value = data.get("offset")

        if isinstance(value, int):
            return value

    except (
        OSError,
        json.JSONDecodeError,
    ):
        pass

    return None


def save_offset(offset):
    directory = os.path.dirname(
        TELEGRAM_OFFSET_FILE
    )

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    with open(
        TELEGRAM_OFFSET_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {"offset": offset},
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def _is_allowed_chat(chat_id):
    if not TELEGRAM_ALLOWED_CHAT_ID:
        return False

    return str(chat_id) == TELEGRAM_ALLOWED_CHAT_ID


def process_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text")

    if chat_id is None or not isinstance(
        text,
        str,
    ):
        return

    command, _ = parse_command(
        text
    )

    if not TELEGRAM_ALLOWED_CHAT_ID:
        if command == "/chatid":
            send_message(
                chat_id,
                f"현재 chat id: {chat_id}",
            )
        else:
            send_message(
                chat_id,
                (
                    "아직 허용된 chat id가 설정되지 않았습니다.\n"
                    "/chatid 명령으로 현재 chat id를 확인한 뒤 "
                    "TELEGRAM_ALLOWED_CHAT_ID에 등록해주세요."
                ),
            )
        return

    if not _is_allowed_chat(
        chat_id
    ):
        print(
            "허용되지 않은 Telegram chat id 요청 무시:",
            chat_id,
        )
        return

    response, changed = (
        handle_preference_command(
            text
        )
    )

    if response == "__CHAT_ID__":
        response = (
            f"현재 chat id: {chat_id}"
        )

    send_message(
        chat_id,
        response,
    )

    if changed:
        print(
            "Telegram 명령으로 사용자 설정이 변경되었습니다."
        )


def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN이 없습니다."
        )

    offset = load_offset()

    print(
        "Telegram preference bot 시작"
    )

    if TELEGRAM_ALLOWED_CHAT_ID:
        print(
            "허용 chat id가 설정되어 있습니다."
        )
    else:
        print(
            "허용 chat id가 없습니다. /chatid 설정 모드로 실행합니다."
        )

    while True:
        try:
            updates = get_updates(
                offset
            )

            for update in updates:
                update_id = update.get(
                    "update_id"
                )

                if isinstance(
                    update_id,
                    int,
                ):
                    offset = update_id + 1
                    save_offset(
                        offset
                    )

                message = update.get(
                    "message"
                )

                if isinstance(
                    message,
                    dict,
                ):
                    process_message(
                        message
                    )

        except KeyboardInterrupt:
            print(
                "Telegram preference bot 종료"
            )
            break

        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            RuntimeError,
        ) as error:
            print(
                "Telegram bot 오류:",
                error,
            )
            time.sleep(5)


if __name__ == "__main__":
    run_bot()
