import html
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import trend_radar


ISSUES_DIR = Path("config/issues")
OUTPUT_DIR = Path("public")
ASSETS_DIR = OUTPUT_DIR / "assets"
ISSUE_OUTPUT_DIR = OUTPUT_DIR / "issues"
ARCHIVE_OUTPUT_DIR = OUTPUT_DIR / "archive"

SITE_NAME = "TECHNEWS DAILY"
SITE_TAGLINE = "Personal Developer Intelligence Newspaper"


def _escape(value):
    return html.escape(
        str(value or ""),
        quote=True,
    )


def _load_issue(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(data, dict):
        return None

    return data


def load_issues():
    if not ISSUES_DIR.exists():
        return []

    issues = []

    for path in sorted(
        ISSUES_DIR.glob("*.json"),
        reverse=True,
    ):
        issue = _load_issue(path)

        if not issue:
            continue

        issue["_source_path"] = str(path)
        issues.append(issue)

    return issues


def _slug_date(issue):
    return (
        str(
            issue.get(
                "issue_date",
                "",
            )
        )
        .strip()
        .replace("/", "-")
    )


def _action_type_label(action_type):
    return {
        "experiment": "EXPERIMENT",
        "code_improvement": "CODE",
        "study": "STUDY",
        "adoption_review": "REVIEW",
    }.get(
        str(action_type or ""),
        "ACTION",
    )


def _story_card(story, rank):
    topics = story.get(
        "topics",
        [],
    )

    topic_html = "".join(
        (
            '<span class="topic-chip">'
            + _escape(topic)
            + "</span>"
        )
        for topic in topics[:4]
    )

    points = story.get(
        "key_points",
        [],
    )

    point_html = "".join(
        (
            "<li>"
            + _escape(point)
            + "</li>"
        )
        for point in points[:3]
    )

    action = story.get(
        "action",
        {},
    )

    action_html = ""

    if (
        story.get(
            "actionability",
            0,
        )
        >= 4
        and action.get(
            "title"
        )
    ):
        steps = "".join(
            (
                "<li>"
                + _escape(step)
                + "</li>"
            )
            for step in action.get(
                "steps",
                [],
            )[:3]
        )

        meta = " · ".join(
            part
            for part in [
                _action_type_label(
                    action.get(
                        "type"
                    )
                ),
                _escape(
                    action.get(
                        "effort"
                    )
                ),
            ]
            if part
        )

        action_html = f"""
        <section class="inline-action">
          <div class="eyebrow">ACTION</div>
          <h4>{_escape(action.get("title"))}</h4>
          <div class="action-meta">{meta}</div>
          <ol>{steps}</ol>
        </section>
        """

    return f"""
    <article class="story-card">
      <div class="story-kicker">
        <span>{rank:02d}</span>
        <span>{_escape(story.get("company"))}</span>
        <span>{_escape(story.get("selection_score"))}/15</span>
      </div>
      <h3>
        <a href="{_escape(story.get("link"))}" target="_blank" rel="noopener noreferrer">
          {_escape(story.get("title"))}
        </a>
      </h3>
      <p class="lead">{_escape(story.get("one_line"))}</p>
      <ul class="story-points">{point_html}</ul>
      <div class="topic-row">{topic_html}</div>
      {action_html}
      <div class="story-footer">
        <span>{_escape(story.get("recommended_for"))}</span>
        <a href="{_escape(story.get("link"))}" target="_blank" rel="noopener noreferrer">
          ORIGINAL ↗
        </a>
      </div>
    </article>
    """


def _action_desk(issue):
    items = []

    stories = (
        issue.get(
            "top_stories",
            [],
        )
        + issue.get(
            "more_detailed",
            [],
        )
    )

    for story in stories:
        action = story.get(
            "action",
            {},
        )

        if (
            story.get(
                "actionability",
                0,
            )
            < 4
        ):
            continue

        title = str(
            action.get(
                "title",
                "",
            )
        ).strip()

        if not title:
            continue

        items.append(
            (
                story,
                action,
            )
        )

    if not items:
        return """
        <div class="empty-note">
          오늘은 별도의 실행 항목으로 분류된 기사가 없습니다.
        </div>
        """

    cards = []

    for story, action in items[:6]:
        cards.append(
            f"""
            <article class="action-card">
              <div class="action-index">
                {_action_type_label(action.get("type"))}
              </div>
              <h3>{_escape(action.get("title"))}</h3>
              <p>
                {_escape(story.get("company"))}
                ·
                {_escape(story.get("title"))}
              </p>
              <div class="action-effort">
                {_escape(action.get("effort"))}
              </div>
            </article>
            """
        )

    return "".join(cards)


def _compute_trend_rows():
    articles = trend_radar.load_history(
        "config/article_history.json"
    )

    current, previous = (
        trend_radar.split_windows(
            articles
        )
    )

    rising = (
        trend_radar.find_rising_topics(
            current,
            previous,
        )
    )

    return (
        rising,
        len(current),
        len(previous),
    )


def _trend_section():
    rising, current_count, previous_count = (
        _compute_trend_rows()
    )

    if not rising:
        return f"""
        <div class="trend-empty">
          <div class="trend-counts">
            최근 7일 {current_count}개 · 이전 7일 {previous_count}개
          </div>
          <h3>아직 뚜렷한 상승 주제가 없습니다.</h3>
          <p>
            발행 데이터가 쌓이면 최근 7일과 이전 7일을 비교해
            실제로 증가한 기술 주제만 이곳에 표시합니다.
          </p>
        </div>
        """

    rows = []

    for index, row in enumerate(
        rising,
        start=1,
    ):
        rows.append(
            f"""
            <div class="trend-row">
              <span class="trend-rank">{index:02d}</span>
              <div>
                <strong>{_escape(row["topic"])}</strong>
                <span>
                  {row["previous_count"]} → {row["current_count"]} ARTICLES
                </span>
              </div>
              <span class="trend-delta">+{row["delta"]}</span>
            </div>
            """
        )

    return "".join(rows)


def _brief_news(issue):
    articles = issue.get(
        "brief_articles",
        [],
    )

    if not articles:
        return """
        <div class="empty-note">
          추가로 소개할 기사가 없습니다.
        </div>
        """

    rows = []

    for article in articles[:12]:
        rows.append(
            f"""
            <article class="brief-row">
              <div>
                <span class="brief-source">
                  {_escape(article.get("company"))}
                </span>
                <h3>
                  <a href="{_escape(article.get("link"))}" target="_blank" rel="noopener noreferrer">
                    {_escape(article.get("title"))}
                  </a>
                </h3>
              </div>
              <div class="brief-score">
                {_escape(article.get("selection_score"))}/15
              </div>
            </article>
            """
        )

    return "".join(rows)


def _editorial_blocks(editorial):
    text = str(
        editorial or ""
    ).strip()

    if not text:
        return """
        <p class="editorial-copy">
          오늘의 편집 노트가 없습니다.
        </p>
        """

    blocks = []

    current_title = None
    current_lines = []

    def flush():
        if not current_lines:
            return

        body = " ".join(
            line.strip("• ").strip()
            for line in current_lines
            if line.strip()
        )

        if not body:
            return

        heading = (
            f"<h4>{_escape(current_title)}</h4>"
            if current_title
            else ""
        )

        blocks.append(
            (
                '<div class="editorial-block">'
                + heading
                + "<p>"
                + _escape(body)
                + "</p></div>"
            )
        )

    for line in text.splitlines():
        stripped = line.strip()

        if (
            stripped.startswith("[")
            and stripped.endswith("]")
        ):
            flush()
            current_lines = []
            current_title = stripped.strip(
                "[]"
            )
        elif stripped:
            current_lines.append(
                stripped
            )

    flush()

    return "".join(blocks)


def _layout(
    title,
    content,
    description="",
    body_class="",
):
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{_escape(description)}">
  <meta name="color-scheme" content="light dark">
  <title>{_escape(title)}</title>
  <link rel="stylesheet" href="/technews/assets/styles.css">
</head>
<body class="{_escape(body_class)}">
  {content}
</body>
</html>
"""


def render_issue(issue, archive_items):
    issue_date = _slug_date(
        issue
    )

    top_stories = issue.get(
        "top_stories",
        [],
    )

    story_html = "".join(
        _story_card(
            story,
            index,
        )
        for index, story in enumerate(
            top_stories,
            start=1,
        )
    )

    if not story_html:
        story_html = """
        <div class="empty-note">
          오늘의 Top Story가 아직 없습니다.
        </div>
        """

    archive_links = "".join(
        (
            f'<a href="/technews/issues/{_escape(_slug_date(item))}/">'
            f'{_escape(item.get("issue_date"))}</a>'
        )
        for item in archive_items[:7]
    )

    stats = issue.get(
        "stats",
        {},
    )

    content = f"""
    <header class="site-shell masthead-shell">
      <div class="utility-line">
        <span>ISSUE NO. {_escape(issue.get("issue_number"))}</span>
        <span>{_escape(issue.get("issue_date"))} · DAILY EDITION</span>
      </div>
      <div class="masthead">
        <div class="masthead-side">PERSONAL<br>DEVELOPER<br>INTELLIGENCE</div>
        <h1>TECHNEWS<br><span>DAILY.</span></h1>
        <div class="masthead-side right">CURATED<br>WITH AI<br>FOR BUILDERS</div>
      </div>
    </header>

    <main class="paper site-shell">
      <nav class="paper-nav">
        <a href="#top">TOP STORIES</a>
        <a href="#actions">ACTION DESK</a>
        <a href="#radar">TREND RADAR</a>
        <a href="#more">MORE NEWS</a>
        <a href="/technews/archive/">ARCHIVE</a>
      </nav>

      <section class="section hero-section" id="top">
        <div class="section-head">
          <div>
            <div class="eyebrow">01 · TOP STORIES</div>
            <h2>오늘 개발자가<br>봐야 할 기술 변화</h2>
          </div>
          <div class="section-note">
            {stats.get("candidate_count", 0)}개 신규 글 중
            {len(top_stories)}개를 오늘의 핵심 기사로 선정했습니다.
          </div>
        </div>
        <div class="story-grid">{story_html}</div>
      </section>

      <section class="section" id="actions">
        <div class="section-head compact">
          <div>
            <div class="eyebrow">02 · ACTION DESK</div>
            <h2>읽고 끝내지 않는 뉴스</h2>
          </div>
          <div class="section-note">
            실제로 실험하거나 적용할 가치가 높은 기사만 Action으로 전환합니다.
          </div>
        </div>
        <div class="action-grid">{_action_desk(issue)}</div>
      </section>

      <section class="section" id="radar">
        <div class="section-head compact">
          <div>
            <div class="eyebrow">03 · TREND RADAR</div>
            <h2>기사보다 큰 흐름</h2>
          </div>
          <div class="section-note">
            최근 7일과 이전 7일의 실제 기사 데이터를 비교합니다.
          </div>
        </div>
        <div class="trend-board">{_trend_section()}</div>
      </section>

      <section class="section editorial-section">
        <div class="section-head compact">
          <div>
            <div class="eyebrow">04 · EDITOR'S NOTE</div>
            <h2>오늘의 편집 노트</h2>
          </div>
          <div class="section-note">
            기사 전체를 관통하는 핵심 흐름과 학습 포인트입니다.
          </div>
        </div>
        <div class="editorial-grid">
          {_editorial_blocks(issue.get("editorial"))}
        </div>
      </section>

      <section class="section" id="more">
        <div class="section-head compact">
          <div>
            <div class="eyebrow">05 · MORE NEWS</div>
            <h2>추가로 볼 만한 글</h2>
          </div>
          <div class="section-note">
            상세 브리핑까지는 아니지만 확인할 가치가 있는 기사입니다.
          </div>
        </div>
        <div class="brief-list">{_brief_news(issue)}</div>
      </section>

      <section class="section source-section">
        <div class="section-head compact">
          <div>
            <div class="eyebrow">ARCHIVE</div>
            <h2>지난 발행</h2>
          </div>
          <div class="section-note">
            매일 발행본은 날짜별로 그대로 보존됩니다.
          </div>
        </div>
        <div class="archive-strip">{archive_links}</div>
      </section>
    </main>

    <footer class="site-shell site-footer">
      <div>
        <strong>{SITE_NAME}</strong>
        <p>
          원문 전체를 재게시하지 않습니다.
          AI가 생성한 요약·분석·Action과 원문 링크를 제공합니다.
        </p>
      </div>
      <div class="footer-mark">
        See you<br>tomorrow.
      </div>
    </footer>
    """

    return _layout(
        (
            f"{SITE_NAME} · "
            f"{issue.get('issue_date', '')}"
        ),
        content,
        (
            f"{SITE_TAGLINE} - "
            f"{issue.get('issue_date', '')}"
        ),
        "issue-page",
    )


def render_empty_home():
    now = datetime.now(
        ZoneInfo(
            "Asia/Seoul"
        )
    )

    content = f"""
    <header class="site-shell masthead-shell">
      <div class="utility-line">
        <span>ISSUE PREPARATION</span>
        <span>{now.strftime("%Y-%m-%d")} · SEOUL</span>
      </div>
      <div class="masthead">
        <div class="masthead-side">PERSONAL<br>DEVELOPER<br>INTELLIGENCE</div>
        <h1>TECHNEWS<br><span>DAILY.</span></h1>
        <div class="masthead-side right">CURATED<br>WITH AI<br>FOR BUILDERS</div>
      </div>
    </header>
    <main class="paper site-shell empty-paper">
      <div class="eyebrow">FIRST EDITION</div>
      <h2>첫 발행을 준비하고 있습니다.</h2>
      <p>
        다음 Daily Tech News 실행에서 실제 기사 데이터를 기반으로
        첫 번째 Newspaper Issue가 생성됩니다.
      </p>
    </main>
    """

    return _layout(
        SITE_NAME,
        content,
        SITE_TAGLINE,
        "issue-page",
    )


def render_archive(issues):
    rows = []

    for issue in issues:
        rows.append(
            f"""
            <a class="archive-row" href="/technews/issues/{_escape(_slug_date(issue))}/">
              <div>
                <span>ISSUE {_escape(issue.get("issue_number"))}</span>
                <strong>{_escape(issue.get("issue_date"))}</strong>
              </div>
              <p>
                {_escape(
                    issue.get(
                        "top_stories",
                        [{}],
                    )[0].get(
                        "title",
                        "TechNews Daily",
                    )
                    if issue.get("top_stories")
                    else "TechNews Daily"
                )}
              </p>
              <span>READ ↗</span>
            </a>
            """
        )

    if not rows:
        rows.append(
            '<div class="empty-note">아직 발행된 Issue가 없습니다.</div>'
        )

    content = f"""
    <header class="site-shell archive-header">
      <a href="/technews/">← LATEST ISSUE</a>
      <div class="eyebrow">ARCHIVE</div>
      <h1>Every issue,<br>kept intact.</h1>
      <p>
        매일 발행된 기술 신문을 날짜별로 다시 볼 수 있습니다.
      </p>
    </header>
    <main class="site-shell archive-page">
      {"".join(rows)}
    </main>
    """

    return _layout(
        f"{SITE_NAME} · Archive",
        content,
        "Daily TechNews archive",
        "archive-body",
    )


def write_text(path, content):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        content,
        encoding="utf-8",
    )


def build_site():
    issues = load_issues()

    if OUTPUT_DIR.exists():
        shutil.rmtree(
            OUTPUT_DIR
        )

    ASSETS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ISSUE_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ARCHIVE_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    css_source = Path(
        "web/styles.css"
    )

    if not css_source.exists():
        raise RuntimeError(
            "web/styles.css이 없습니다."
        )

    shutil.copyfile(
        css_source,
        ASSETS_DIR / "styles.css",
    )

    write_text(
        OUTPUT_DIR / ".nojekyll",
        "",
    )

    if issues:
        latest = issues[0]

        write_text(
            OUTPUT_DIR / "index.html",
            render_issue(
                latest,
                issues,
            ),
        )

        for issue in issues:
            issue_date = _slug_date(
                issue
            )

            write_text(
                (
                    ISSUE_OUTPUT_DIR
                    / issue_date
                    / "index.html"
                ),
                render_issue(
                    issue,
                    issues,
                ),
            )
    else:
        write_text(
            OUTPUT_DIR / "index.html",
            render_empty_home(),
        )

    write_text(
        ARCHIVE_OUTPUT_DIR
        / "index.html",
        render_archive(
            issues
        ),
    )

    print(
        "Newspaper site build complete:",
        len(issues),
        "issues",
    )


if __name__ == "__main__":
    build_site()
