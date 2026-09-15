import html
import json

import telegram_bot
from telegram_digest import (
    create_followup_detail,
    create_on_demand_digest,
    parse_followup_selection,
)


TELEGRAM_STATE_FILE = "config/telegram_state.json"


def _is_allowed_chat(chat_id):
    return (
        bool(telegram_bot.TELEGRAM_ALLOWED_CHAT_ID)
        and str(chat_id) == telegram_bot.TELEGRAM_ALLOWED_CHAT_ID
    )


def _clean_followup_detail_message(detail):
    text = str(detail or "")
    start = text.find("{")
    end = text.rfind("}")

    if start < 0 or end <= start:
        return text

    raw_json = html.unescape(text[start : end + 1])

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return text

    if not isinstance(parsed, dict) or "summary" not in parsed:
        return text

    summary = str(parsed.get("summary", "")).strip()
    key_points = parsed.get("key_points", [])
    takeaway = str(parsed.get("takeaway", "")).strip()

    if not isinstance(key_points, list):
        key_points = []

    replacement = []

    if summary:
        replacement.append(html.escape(summary, quote=True))

    if key_points:
        replacement.extend(["", "<b>핵심 포인트</b>"])
        for point in key_points[:3]:
            replacement.append(
                f"• {html.escape(str(point).strip(), quote=True)}"
            )

    if takeaway:
        replacement.extend(
            [
                "",
                "💡 <b>가져갈 것</b>",
                html.escape(takeaway, quote=True),
            ]
        )

    prefix = text[:start].rstrip()
    suffix = text[end + 1 :].lstrip()

    parts = [prefix]
    if replacement:
        parts.append("\n".join(replacement))
    if suffix:
        parts.append(suffix)

    return "\n\n".join(part for part in parts if part)


def _process_digest_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text")

    if chat_id is None or not isinstance(text, str):
        return False

    followup_position = parse_followup_selection(text)
    command, argument = telegram_bot.parse_command(text)

    is_digest = command == "/digest"
    is_followup = followup_position is not None

    if not is_digest and not is_followup:
        return False

    if not telegram_bot.TELEGRAM_ALLOWED_CHAT_ID:
        telegram_bot.send_message(
            chat_id,
            (
                "아직 허용된 chat id가 설정되지 않았습니다.\n"
                "/chatid 명령으로 현재 chat id를 확인해주세요."
            ),
        )
        return True

    if not _is_allowed_chat(chat_id):
        print(
            "허용되지 않은 Telegram digest 요청 무시:",
            chat_id,
        )
        return True

    if is_followup:
        telegram_bot.send_message(
            chat_id,
            f"{followup_position}번 기사를 더 자세히 읽고 있어요. 잠시만 기다려주세요.",
        )

        try:
            detail = create_followup_detail(followup_position)
            detail = _clean_followup_detail_message(detail)
        except Exception as error:
            print(
                "Telegram 후속 질문 생성 실패:",
                repr(error),
            )
            telegram_bot.send_message(
                chat_id,
                "상세 분석 중 오류가 발생했습니다. 다음 실행에서 다시 시도해주세요.",
            )
            return True

        telegram_bot.send_message(
            chat_id,
            detail,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return True

    if not argument:
        telegram_bot.send_message(
            chat_id,
            "주제를 입력해주세요. 예: /digest MCP",
        )
        return True

    telegram_bot.send_message(
        chat_id,
        f"'{argument}' 관련 기술 뉴스를 찾고 있어요. 잠시만 기다려주세요.",
    )

    try:
        digest = create_on_demand_digest(argument)
    except Exception as error:
        print(
            "Telegram digest 생성 실패:",
            repr(error),
        )
        telegram_bot.send_message(
            chat_id,
            (
                "브리핑 생성 중 오류가 발생했습니다. "
                "다음 실행에서 다시 시도해주세요."
            ),
        )
        return True

    telegram_bot.send_message(
        chat_id,
        digest,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    return True


def process_pending_updates():
    if not telegram_bot.TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN이 없습니다."
        )

    telegram_bot.TELEGRAM_OFFSET_FILE = TELEGRAM_STATE_FILE
    offset = telegram_bot.load_offset()

    print("Telegram 예약 polling 시작")
    print("현재 offset:", offset)

    updates = telegram_bot.get_updates(offset)
    processed_count = 0

    for update in updates:
        update_id = update.get("update_id")

        if isinstance(update_id, int):
            offset = update_id + 1
            telegram_bot.save_offset(offset)

        message = update.get("message")

        if isinstance(message, dict):
            handled = _process_digest_message(message)

            if not handled:
                telegram_bot.process_message(message)

            processed_count += 1

    print("처리한 Telegram 메시지:", processed_count)
    print("최종 offset:", offset)

    return processed_count


if __name__ == "__main__":
    process_pending_updates()
