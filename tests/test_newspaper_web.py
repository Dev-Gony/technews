import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_newspaper


class NewspaperBuilderTest(unittest.TestCase):
    def test_load_issues_orders_latest_first(self):
        with tempfile.TemporaryDirectory() as directory:
            issue_dir = Path(directory)

            for date in [
                "2026-09-18",
                "2026-09-19",
            ]:
                (
                    issue_dir
                    / f"{date}.json"
                ).write_text(
                    json.dumps(
                        {
                            "issue_date": date,
                            "issue_number": 1,
                        }
                    ),
                    encoding="utf-8",
                )

            with patch.object(
                build_newspaper,
                "ISSUES_DIR",
                issue_dir,
            ):
                issues = (
                    build_newspaper.load_issues()
                )

            self.assertEqual(
                issues[0]["issue_date"],
                "2026-09-19",
            )

    def test_issue_render_escapes_article_title(self):
        issue = {
            "issue_date": "2026-09-19",
            "issue_number": 1,
            "stats": {
                "candidate_count": 1,
            },
            "editorial": "",
            "top_stories": [
                {
                    "company": "A&B",
                    "title": "RAG < MCP",
                    "link": "https://example.com/?a=1&b=2",
                    "selection_score": 14,
                    "one_line": "summary",
                    "key_points": [],
                    "topics": [],
                    "recommended_for": "",
                    "actionability": 0,
                    "action": {},
                }
            ],
            "brief_articles": [],
        }

        with patch(
            "build_newspaper._compute_trend_rows",
            return_value=([], 0, 0),
        ):
            rendered = (
                build_newspaper.render_issue(
                    issue,
                    [issue],
                )
            )

        self.assertIn(
            "RAG &lt; MCP",
            rendered,
        )
        self.assertIn(
            "A&amp;B",
            rendered,
        )



    def test_print_style_front_page_structure(self):
        issue = {
            "issue_date": "2026-09-19",
            "issue_number": 1,
            "stats": {
                "candidate_count": 20,
                "detailed_count": 9,
            },
            "editorial": "",
            "top_stories": [
                {
                    "company": "GeekNews",
                    "title": "Main Story",
                    "link": "https://example.com/main",
                    "selection_score": 15,
                    "one_line": "Main summary",
                    "key_points": ["Point"],
                    "topics": ["AI Agent"],
                    "recommended_for": "개발자",
                    "actionability": 5,
                    "action": {
                        "type": "experiment",
                        "title": "Try it",
                        "steps": ["Step 1"],
                        "effort": "30~60분",
                    },
                },
                {
                    "company": "GeekNews",
                    "title": "Side Story 1",
                    "link": "https://example.com/side-1",
                    "selection_score": 14,
                    "one_line": "Side summary 1",
                    "key_points": [],
                    "topics": ["Rust"],
                    "recommended_for": "",
                    "actionability": 0,
                    "action": {},
                },
                {
                    "company": "GeekNews",
                    "title": "Side Story 2",
                    "link": "https://example.com/side-2",
                    "selection_score": 14,
                    "one_line": "Side summary 2",
                    "key_points": [],
                    "topics": ["On-device AI"],
                    "recommended_for": "",
                    "actionability": 0,
                    "action": {},
                },
            ],
            "more_detailed": [],
            "brief_articles": [],
        }

        with patch(
            "build_newspaper._compute_trend_rows",
            return_value=([], 0, 0),
        ):
            rendered = build_newspaper.render_issue(
                issue,
                [issue],
            )

        self.assertIn(
            'class="lead-story"',
            rendered,
        )
        self.assertIn(
            'class="side-news"',
            rendered,
        )
        self.assertIn(
            "오늘의 1면",
            rendered,
        )
        self.assertNotIn(
            'class="story-card"',
            rendered,
        )


    def test_front_page_uses_detailed_story_to_balance_sidebar(self):
        issue = {
            "issue_date": "2026-09-19",
            "issue_number": 1,
            "stats": {
                "candidate_count": 4,
                "detailed_count": 4,
            },
            "editorial": "",
            "top_stories": [
                {
                    "company": "A",
                    "title": "Lead",
                    "link": "https://example.com/lead",
                    "selection_score": 15,
                    "one_line": "Lead summary",
                    "key_points": [],
                    "topics": [],
                    "actionability": 0,
                    "action": {},
                },
                {
                    "company": "B",
                    "title": "Side One",
                    "link": "https://example.com/side-1",
                    "selection_score": 14,
                    "one_line": "Side 1",
                    "key_points": [],
                    "topics": [],
                    "actionability": 0,
                    "action": {},
                },
                {
                    "company": "C",
                    "title": "Side Two",
                    "link": "https://example.com/side-2",
                    "selection_score": 14,
                    "one_line": "Side 2",
                    "key_points": [],
                    "topics": [],
                    "actionability": 0,
                    "action": {},
                },
            ],
            "more_detailed": [
                {
                    "company": "D",
                    "title": "Sidebar Detailed Story",
                    "link": "https://example.com/detail",
                    "selection_score": 13,
                    "one_line": "Detailed summary",
                    "key_points": [],
                    "topics": [],
                    "actionability": 0,
                    "action": {},
                }
            ],
            "brief_articles": [],
        }

        with patch(
            "build_newspaper._compute_trend_rows",
            return_value=([], 0, 0),
        ):
            rendered = build_newspaper.render_issue(
                issue,
                [issue],
            )

        self.assertIn(
            "Sidebar Detailed Story",
            rendered,
        )
        self.assertIn(
            "관련 기사",
            rendered,
        )

    def test_custom_domain_base_path_can_be_root(self):
        issue = {
            "issue_date": "2026-09-19",
            "issue_number": 1,
            "stats": {
                "candidate_count": 0,
            },
            "editorial": "",
            "top_stories": [],
            "brief_articles": [],
        }

        with patch.object(
            build_newspaper,
            "SITE_BASE_PATH",
            "",
        ), patch(
            "build_newspaper._compute_trend_rows",
            return_value=([], 0, 0),
        ):
            rendered = (
                build_newspaper.render_issue(
                    issue,
                    [issue],
                )
            )

        self.assertIn(
            'href="/assets/styles.css"',
            rendered,
        )
        self.assertIn(
            'href="/archive/"',
            rendered,
        )
        self.assertNotIn(
            "/technews/",
            rendered,
        )

    def test_empty_home_is_buildable(self):
        rendered = (
            build_newspaper.render_empty_home()
        )

        self.assertIn(
            "첫 발행을 준비하고 있습니다.",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
