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
SITE_TAGLINE = "개발자를 위한 매일의 기술신문"
SITE_BASE_PATH = os.environ.get(
    "SITE_BASE_PATH",
    "/technews"
).strip()

if (
    not SITE_BASE_PATH
    or SITE_BASE_PATH == "/"
):
    SITE_BASE_PATH = ""
else:
    SITE_BASE_PATH = "/" + SITE_BASE_PATH.strip("/")


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


def _display_date(value):
    text = str(value or "").strip()

    try:
        parsed = datetime.strptime(
            text,
            "%Y-%m-%d",
        )
    except ValueError:
        return text

    weekdays = [
        "월요일",
        "화요일",
        "수요일",
        "목요일",
        "금요일",
        "토요일",
        "일요일",
    ]

    return (
        f"{parsed.year}년 "
        f"{parsed.month}월 "
        f"{parsed.day}일 "
        f"{weekdays[parsed.weekday()]}"
    )


def _action_type_label(action_type):
    return {
        "experiment": "실험",
        "code_improvement": "코드 개선",
        "study": "학습",
        "adoption_review": "도입 검토",
    }.get(
        str(action_type or ""),
        "실행",
    )


def _topic_line(story):
    topics = story.get(
        "topics",
        [],
    )

    if not isinstance(
        topics,
        list,
    ):
        return ""

    cleaned = [
        str(topic).strip()
        for topic in topics[:4]
        if str(topic).strip()
    ]

    if not cleaned:
        return ""

    return " · ".join(
        _escape(topic)
        for topic in cleaned
    )


def _source_line(story):
    parts = []

    company = str(
        story.get(
            "company",
            "",
        )
    ).strip()

    if company:
        parts.append(
            _escape(company)
        )

    score = story.get(
        "selection_score"
    )

    if score is not None:
        parts.append(
            f"{_escape(score)}/15"
        )

    return " · ".join(parts)


def _story_points(story):
    points = story.get(
        "key_points",
        [],
    )

    if not isinstance(
        points,
        list,
    ):
        return ""

    rows = []

    for point in points[:3]:
        text = str(point).strip()

        if text:
            rows.append(
                "<li>"
                + _escape(text)
                + "</li>"
            )

    if not rows:
        return ""

    return (
        '<ul class="article-points">'
        + "".join(rows)
        + "</ul>"
    )


def _lead_action(story):
    if (
        story.get(
            "actionability",
            0,
        )
        < 4
    ):
        return ""

    action = story.get(
        "action",
        {},
    )

    if not isinstance(
        action,
        dict,
    ):
        return ""

    title = str(
        action.get(
            "title",
            "",
        )
    ).strip()

    if not title:
        return ""

    steps = []

    for step in action.get(
        "steps",
        [],
    )[:3]:
        text = str(step).strip()

        if text:
            steps.append(
                "<li>"
                + _escape(text)
                + "</li>"
            )

    meta = []

    action_type = str(
        action.get(
            "type",
            "",
        )
    ).strip()

    if action_type:
        meta.append(
            _action_type_label(
                action_type
            )
        )

    effort = str(
        action.get(
            "effort",
            "",
        )
    ).strip()

    if effort:
        meta.append(
            _escape(effort)
        )

    return f"""
    <aside class="lead-action">
      <div class="small-label">오늘의 실행 제안</div>
      <h4>{_escape(title)}</h4>
      <div class="action-meta">{" · ".join(meta)}</div>
      <ol>{"".join(steps)}</ol>
    </aside>
    """


def _lead_story(story):
    if not story:
        return """
        <div class="empty-note">
          오늘의 톱기사가 아직 없습니다.
        </div>
        """

    return f"""
    <article class="lead-story">
      <div class="article-meta">
        <span class="small-label">오늘의 톱기사</span>
        <span>{_source_line(story)}</span>
      </div>

      <h1>
        <a
          href="{_escape(story.get("link"))}"
          target="_blank"
          rel="noopener noreferrer"
        >
          {_escape(story.get("title"))}
        </a>
      </h1>

      <p class="lead-deck">
        {_escape(story.get("one_line"))}
      </p>

      <div class="article-byline">
        TECHNEWS 편집부 · {_topic_line(story)}
      </div>

      <div class="lead-detail">
        {_story_points(story)}
        {_lead_action(story)}
      </div>

      <div class="original-link">
        <a
          href="{_escape(story.get("link"))}"
          target="_blank"
          rel="noopener noreferrer"
        >
          원문 보기 →
        </a>
      </div>
    </article>
    """


def _secondary_story(story, label):
    if not story:
        return ""

    return f"""
    <article class="secondary-story">
      <div class="small-label">{_escape(label)}</div>
      <h2>
        <a
          href="{_escape(story.get("link"))}"
          target="_blank"
          rel="noopener noreferrer"
        >
          {_escape(story.get("title"))}
        </a>
      </h2>
      <p>{_escape(story.get("one_line"))}</p>
      <div class="article-meta bottom">
        <span>{_source_line(story)}</span>
        <span>{_topic_line(story)}</span>
      </div>
    </article>
    """


def _news_column(story, index):
    if not story:
        return ""

    return f"""
    <article class="news-column">
      <div class="small-label">기사 {index:02d}</div>
      <h3>
        <a
          href="{_escape(story.get("link"))}"
          target="_blank"
          rel="noopener noreferrer"
        >
          {_escape(story.get("title"))}
        </a>
      </h3>
      <p>{_escape(story.get("one_line"))}</p>
      <div class="article-meta bottom">
        <span>{_source_line(story)}</span>
      </div>
    </article>
    """


def _action_desk(issue):
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

    rows = []

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
            or not isinstance(
                action,
                dict,
            )
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

        steps = []

        for step in action.get(
            "steps",
            [],
        )[:3]:
            step_text = str(step).strip()

            if step_text:
                steps.append(
                    "<li>"
                    + _escape(step_text)
                    + "</li>"
                )

        rows.append(
            f"""
            <article class="action-column">
              <div class="small-label">
                {_escape(_action_type_label(action.get("type")))}
                · {_escape(action.get("effort"))}
              </div>
              <h3>{_escape(title)}</h3>
              <p class="action-source">
                {_escape(story.get("company"))}
                ·
                {_escape(story.get("title"))}
              </p>
              <ol>{"".join(steps)}</ol>
            </article>
            """
        )

        if len(rows) >= 4:
            break

    if not rows:
        return """
        <div class="empty-note">
          오늘은 별도의 실행 항목으로 분류된 기사가 없습니다.
        </div>
        """

    return "".join(rows)


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

    intro = f"""
    <div class="trend-summary">
      <div class="small-label">최근 7일 분석</div>
      <strong>{current_count}개</strong>
      <span>이전 7일 {previous_count}개 기사와 비교</span>
    </div>
    """

    if not rising:
        return intro + """
        <div class="trend-empty">
          <h3>아직 뚜렷한 상승 주제가 없습니다.</h3>
          <p>
            발행 이력이 더 쌓이면 최근 7일과 이전 7일을 비교해
            실제로 증가한 기술 주제만 이 지면에 싣습니다.
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
              <span class="trend-rank">{index}</span>
              <div class="trend-topic">
                <strong>{_escape(row["topic"])}</strong>
                <span>
                  이전 {row["previous_count"]}건
                  · 최근 {row["current_count"]}건
                </span>
              </div>
              <span class="trend-delta">+{row["delta"]}</span>
            </div>
            """
        )

    return (
        intro
        + '<div class="trend-table">'
        + "".join(rows)
        + "</div>"
    )


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

    for index, article in enumerate(
        articles[:12],
        start=1,
    ):
        rows.append(
            f"""
            <article class="brief-item">
              <span class="brief-number">{index:02d}</span>
              <div>
                <div class="small-label">
                  {_escape(article.get("company"))}
                  · {_escape(article.get("selection_score"))}/15
                </div>
                <h3>
                  <a
                    href="{_escape(article.get("link"))}"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {_escape(article.get("title"))}
                  </a>
                </h3>
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
                '<section class="editorial-block">'
                + heading
                + "<p>"
                + _escape(body)
                + "</p></section>"
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
  <title>{_escape(title)}</title>
  <link rel="stylesheet" href="{SITE_BASE_PATH}/assets/styles.css">
</head>
<body class="{_escape(body_class)}">
  {content}
</body>
</html>
"""


def _archive_links(archive_items):
    links = []

    for item in archive_items[:7]:
        links.append(
            (
                f'<a href="{SITE_BASE_PATH}/issues/'
                f'{_escape(_slug_date(item))}/">'
                f'{_escape(item.get("issue_date"))}'
                "</a>"
            )
        )

    if not links:
        return """
        <span class="muted">
          지난 발행본이 아직 없습니다.
        </span>
        """

    return "".join(links)


def render_issue(issue, archive_items):
    top_stories = issue.get(
        "top_stories",
        [],
    )

    more_detailed = issue.get(
        "more_detailed",
        [],
    )

    lead = (
        top_stories[0]
        if top_stories
        else None
    )

    side_one = (
        top_stories[1]
        if len(top_stories) > 1
        else None
    )

    side_two = (
        top_stories[2]
        if len(top_stories) > 2
        else None
    )

    below_fold = (
        top_stories[3:]
        + more_detailed
    )[:6]

    stats = issue.get(
        "stats",
        {},
    )

    content = f"""
    <div class="newspaper">
      <header class="newspaper-header page-width">
        <div class="edition-line">
          <span>{_escape(_display_date(issue.get("issue_date")))}</span>
          <span>제 {_escape(issue.get("issue_number"))}호</span>
          <span>
            후보 {_escape(stats.get("candidate_count", 0))}개
            · 상세 {_escape(stats.get("detailed_count", 0))}개
          </span>
        </div>

        <div class="masthead">
          <h1>{SITE_NAME}</h1>
          <p>{SITE_TAGLINE}</p>
        </div>

        <nav class="section-nav">
          <a href="#front">1면</a>
          <a href="#actions">실행면</a>
          <a href="#radar">분석면</a>
          <a href="#editorial">편집자 노트</a>
          <a href="#briefs">단신</a>
          <a href="{SITE_BASE_PATH}/archive/">지난 호</a>
        </nav>
      </header>

      <main class="page-width">
        <section class="front-page" id="front">
          <div class="section-rule">
            <span>오늘의 1면</span>
            <span>TOP STORIES</span>
          </div>

          <div class="front-grid">
            {_lead_story(lead)}

            <aside class="side-news">
              {_secondary_story(side_one, "주요 기사")}
              {_secondary_story(side_two, "주요 기사")}
            </aside>
          </div>

          <div class="below-fold">
            {"".join(
                _news_column(
                    story,
                    index,
                )
                for index, story in enumerate(
                    below_fold,
                    start=1,
                )
            )}
          </div>
        </section>

        <section class="newspaper-section" id="actions">
          <div class="section-rule">
            <span>실행면</span>
            <span>ACTION DESK</span>
          </div>
          <div class="section-intro">
            <h2>오늘 읽은 기술을<br>직접 움직여 보는 법</h2>
            <p>
              모든 기사에 행동을 붙이지 않습니다.
              실제로 실험하거나 적용할 가치가 높은 기사만 골라
              첫 행동과 예상 작업량을 정리합니다.
            </p>
          </div>
          <div class="action-columns">
            {_action_desk(issue)}
          </div>
        </section>

        <section class="newspaper-section" id="radar">
          <div class="section-rule">
            <span>분석면</span>
            <span>TREND RADAR</span>
          </div>
          <div class="analysis-grid">
            <div>
              <h2>한 기사보다<br>큰 기술의 흐름</h2>
              <p class="analysis-copy">
                최근 7일과 이전 7일의 기사 빈도를 비교해
                실제로 증가한 기술 주제만 추적합니다.
                데이터가 부족하면 억지로 트렌드를 만들지 않습니다.
              </p>
            </div>
            <div>
              {_trend_section()}
            </div>
          </div>
        </section>

        <section class="newspaper-section" id="editorial">
          <div class="section-rule">
            <span>편집자 노트</span>
            <span>EDITOR'S NOTE</span>
          </div>
          <div class="editorial-heading">
            <h2>오늘의 기술면을<br>한 번 더 읽는 방법</h2>
          </div>
          <div class="editorial-columns">
            {_editorial_blocks(issue.get("editorial"))}
          </div>
        </section>

        <section class="newspaper-section" id="briefs">
          <div class="section-rule">
            <span>단신</span>
            <span>BRIEF NEWS</span>
          </div>
          <div class="brief-grid">
            {_brief_news(issue)}
          </div>
        </section>

        <section class="newspaper-section archive-section">
          <div class="section-rule">
            <span>지난 호</span>
            <span>ARCHIVE</span>
          </div>
          <div class="archive-links">
            {_archive_links(archive_items)}
          </div>
        </section>
      </main>

      <footer class="newspaper-footer page-width">
        <div>
          <strong>{SITE_NAME}</strong>
          <p>
            원문 전체를 재게시하지 않습니다.
            AI가 생성한 요약·분석·실행 제안과 원문 링크를 제공합니다.
          </p>
        </div>
        <div>
          <a href="{SITE_BASE_PATH}/archive/">지난 호 보기 →</a>
        </div>
      </footer>
    </div>
    """

    return _layout(
        (
            f"{SITE_NAME} · "
            f"{issue.get('issue_date', '')}"
        ),
        content,
        (
            f"{SITE_TAGLINE} · "
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
    <div class="newspaper">
      <header class="newspaper-header page-width">
        <div class="edition-line">
          <span>{_escape(_display_date(now.strftime("%Y-%m-%d")))}</span>
          <span>창간 준비호</span>
          <span>DAILY EDITION</span>
        </div>
        <div class="masthead">
          <h1>{SITE_NAME}</h1>
          <p>{SITE_TAGLINE}</p>
        </div>
      </header>
      <main class="page-width empty-page">
        <div class="section-rule">
          <span>창간 안내</span>
          <span>FIRST EDITION</span>
        </div>
        <h2>첫 발행을 준비하고 있습니다.</h2>
        <p>
          다음 Daily Tech News 실행에서 실제 기사 데이터를 기반으로
          첫 번째 Newspaper Issue가 생성됩니다.
        </p>
      </main>
    </div>
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
        top_story = ""

        if issue.get(
            "top_stories"
        ):
            top_story = (
                issue[
                    "top_stories"
                ][0].get(
                    "title",
                    "",
                )
            )

        rows.append(
            f"""
            <a
              class="archive-row"
              href="{SITE_BASE_PATH}/issues/{_escape(_slug_date(issue))}/"
            >
              <div class="archive-date">
                <span>제 {_escape(issue.get("issue_number"))}호</span>
                <strong>{_escape(_display_date(issue.get("issue_date")))}</strong>
              </div>
              <div class="archive-headline">
                {_escape(top_story or "TechNews Daily")}
              </div>
              <div class="archive-arrow">읽기 →</div>
            </a>
            """
        )

    if not rows:
        rows.append(
            '<div class="empty-note">'
            "아직 발행된 호가 없습니다."
            "</div>"
        )

    content = f"""
    <div class="newspaper">
      <header class="newspaper-header page-width archive-header">
        <div class="edition-line">
          <a href="{SITE_BASE_PATH}/">← 최신호</a>
          <span>ARCHIVE</span>
          <span>{len(issues)}개 발행본</span>
        </div>
        <div class="masthead archive-masthead">
          <h1>{SITE_NAME}</h1>
          <p>지난 호 보관실</p>
        </div>
      </header>

      <main class="page-width archive-page">
        <div class="section-rule">
          <span>지난 호</span>
          <span>ALL ISSUES</span>
        </div>
        {"".join(rows)}
      </main>
    </div>
    """

    return _layout(
        f"{SITE_NAME} · 지난 호",
        content,
        "TechNews Daily Archive",
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
