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
