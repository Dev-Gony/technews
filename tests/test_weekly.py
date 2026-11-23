import os
import sys
import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import weekly  # noqa: E402

KST = ZoneInfo("Asia/Seoul")


def entry(day, score, video="v", script=True):
    return {
        "date": f"2026-11-{day:02d}",
        "publish_at": f"2026-11-{day:02d}T18:00:00+09:00",
        "video_id": f"{video}{day}",
        "pick_score": score,
        **({"script": {"title": f"제목{day}", "cuts": []}} if script else {}),
    }


class WeeklyTest(unittest.TestCase):
    def test_week_entries_and_countdown(self):
        history = [entry(16, 9), entry(17, 6), entry(20, 8), entry(22, 7), entry(23, 5), entry(21, 9, script=False),
                   {"date": "2026-11-19", "link": "x", "skipped": "factcheck"}]
        picked = weekly.week_entries(history, date(2026, 11, 23))
        # 11/17~11/23, 대본이 있는 업로드만 (11/16, 대본 없는 11/21, 건너뛴 기록 제외)
        self.assertEqual([e["video_id"] for e in picked], ["v17", "v20", "v22", "v23"])

        items = weekly.choose(picked)
        # 카운트다운: 점수 낮은 4위부터 1위까지
        self.assertEqual([(i["rank"], i["video_id"]) for i in items], [(4, "v23"), (3, "v17"), (2, "v22"), (1, "v20")])

    def test_chapters_start_at_zero_and_skip_short_intro(self):
        items = [{"rank": 3, "script": {"title": "셋"}, "seconds": 30.2}, {"rank": 2, "script": {"title": "둘"}, "seconds": 28},
                 {"rank": 1, "script": {"title": "하나"}, "seconds": 31}]
        self.assertEqual(weekly.chapters(5.4, items), ["00:00 3위 셋", "00:35 2위 둘", "01:03 1위 하나"])

    def test_next_sunday_publish(self):
        # 일요일 새벽에 만들면 그날 11시, 일요일 11시가 지났으면 다음 주
        self.assertEqual(weekly.next_sunday_publish(datetime(2026, 11, 29, 5, 47, tzinfo=KST)), datetime(2026, 11, 29, 11, 0, tzinfo=KST))
        self.assertEqual(weekly.next_sunday_publish(datetime(2026, 11, 29, 12, 0, tzinfo=KST)), datetime(2026, 12, 6, 11, 0, tzinfo=KST))
        self.assertEqual(weekly.next_sunday_publish(datetime(2026, 11, 25, 9, 0, tzinfo=KST)), datetime(2026, 11, 29, 11, 0, tzinfo=KST))


if __name__ == "__main__":
    unittest.main()
