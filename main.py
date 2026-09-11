import urllib.request
import xml.etree.ElementTree as ET
import json
import os


RSS_URL = "https://dev.gmarket.com/rss"

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")


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

    return {
        "title": title.strip(),
        "link": link.strip(),
        "pub_date": pub_date.strip(),
    }


def send_to_slack(article):
    if not SLACK_WEBHOOK_URL:
        raise RuntimeError("SLACK_WEBHOOK_URL Secret이 설정되어 있지 않습니다.")

    message = {
        "text": (
            "📰 G마켓 기술 블로그 최신 글\n\n"
            f"*제목*\n{article['title']}\n\n"
            f"*작성일*\n{article['pub_date']}\n\n"
            f"*원문*\n{article['link']}"
        )
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

    with urllib.request.urlopen(request, timeout=20) as response:
        result = response.read().decode("utf-8")

    if result != "ok":
        raise RuntimeError(f"Slack 전송 실패: {result}")


def main():
    article = get_latest_article()

    print("가져온 게시글:")
    print(article)

    send_to_slack(article)

    print("Slack 전송 완료")


if __name__ == "__main__":
    main()
