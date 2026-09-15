import telegram_bot


TELEGRAM_STATE_FILE = "config/telegram_state.json"


def process_pending_updates():
    if not telegram_bot.TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN이 없습니다."
        )

    telegram_bot.TELEGRAM_OFFSET_FILE = (
        TELEGRAM_STATE_FILE
    )

    offset = telegram_bot.load_offset()

    print(
        "Telegram 예약 polling 시작"
    )

    print(
        "현재 offset:",
        offset,
    )

    updates = telegram_bot.get_updates(
        offset
    )

    processed_count = 0

    for update in updates:
        update_id = update.get(
            "update_id"
        )

        if isinstance(
            update_id,
            int,
        ):
            offset = update_id + 1
            telegram_bot.save_offset(
                offset
            )

        message = update.get(
            "message"
        )

        if isinstance(
            message,
            dict,
        ):
            telegram_bot.process_message(
                message
            )
            processed_count += 1

    print(
        "처리한 Telegram 메시지:",
        processed_count,
    )

    print(
        "최종 offset:",
        offset,
    )

    return processed_count


if __name__ == "__main__":
    process_pending_updates()
