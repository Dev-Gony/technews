import unittest
from unittest.mock import patch

import main


class NewspaperSlackLinkTest(unittest.TestCase):
    @patch(
        "main.datetime"
    )
    def test_digest_links_to_daily_issue(
        self,
        mock_datetime,
    ):
        mock_datetime.now.return_value.strftime.return_value = "2026-09-19"

        digest = main.build_digest(
            summarized_articles=[],
            brief_articles=[],
            editorial="",
            top_indices=[],
            failed_blogs=[],
            candidate_count=0,
            excluded_count=0,
            unresolved_count=0,
        )

        self.assertIn(
            "https://dev-gony.github.io/technews/issues/2026-09-19/",
            digest,
        )


if __name__ == "__main__":
    unittest.main()
