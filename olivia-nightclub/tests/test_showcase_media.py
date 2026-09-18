import json
import os
import random
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory()
os.environ["OLIVIA_DB"] = str(Path(TEMP.name) / "test.db")
from server import services
from server.config import build_config
from server.showcase_media import choose_playlist, screen_payload


class SharedShowcaseTests(unittest.TestCase):
    def test_all_artists_have_three_distinct_clips(self):
        cfg = build_config()
        for artist in cfg["artists"]:
            with self.subTest(artist=artist):
                clips = choose_playlist(cfg, artist, [], rng=random.Random(4))
                self.assertEqual(len(clips), 3)
                self.assertEqual(len({c["video_id"] for c in clips}), 3)
                previous = clips[0]["video_id"]
                again = choose_playlist(cfg, artist, [], previous, random.Random(4))
                self.assertNotEqual(again[0]["video_id"], previous)

    def test_two_clubs_share_only_their_own_program(self):
        for name, artist in (("palmeray", "PNL"), ("babinski", "Gims")):
            user = services.register(name, name, "unused-test-hash", name)
            club, _ = services.db.get_club(user["id"])
            club["cash"] = 1_000_000
            services.db.save_club(user["id"], club)
            services.action_showcase(user, artist)
            state = services.build_state(user)
            own = state["showcase_screen"]
            visitor1 = services.club_screen(user["id"])["showcase"]
            visitor2 = services.club_view(user["id"])["showcase_screen"]
            self.assertEqual(own, visitor1)
            self.assertEqual(own, visitor2)
            self.assertEqual(own["artist"], artist)
            self.assertIn(own["video"]["video_id"], {c["video_id"] for c in build_config()["audio"]["showcase_videos"][artist]})
            self.assertIsNone(services.club_screen(user["id"], own["ends_at"])["showcase"])
        self.assertNotEqual(services.club_screen(1)["showcase"]["video"]["video_id"], services.club_screen(2)["showcase"]["video"]["video_id"])

    def test_late_join_playlist_boundary_and_end(self):
        row = {"id": 10, "club_id": 1, "artist": "PNL", "status": "active", "started_at": 1000, "ends_at": 1180,
               "screen_playlist": json.dumps([{"video_id": "BtyHYIpykN0", "title": "Au DD", "duration": 60},
                                                {"video_id": "u8bHjdljyLw", "title": "Blanka", "duration": 70}])}
        a = screen_payload(row, 1040)
        self.assertEqual(a["video"]["started_at"], 1000)
        b = screen_payload(row, 1060)
        self.assertEqual(b["video"]["video_id"], "u8bHjdljyLw")
        self.assertEqual(b["video"]["started_at"], 1060)
        self.assertEqual(screen_payload(row, 1130)["video"]["key"], "10:1:0")
        self.assertIsNone(screen_payload(row, 1180))
        row["status"] = "ended"
        self.assertIsNone(screen_payload(row, 1001))

    def test_disabled_assets_and_invalid_ids(self):
        cfg = build_config()
        cfg["audio"]["showcase_videos"] = {"PNL": [{"video_id": "invalid"}, {"video_id": "BtyHYIpykN0", "duration": 291}]}
        disabled = [{"kind": "youtube", "enabled": 0, "file_url": "yt:BtyHYIpykN0", "key": "pnl"}]
        self.assertEqual(choose_playlist(cfg, "PNL", disabled), [])
        cfg["audio"]["youtube_enabled"] = False
        self.assertEqual(choose_playlist(cfg, "PNL", []), [])

    def test_program_survives_database_reopen(self):
        from server.db import Database
        path = str(Path(TEMP.name) / "restart.db")
        db = Database(path)
        clips = choose_playlist(build_config(), "PNL", [])
        db.start_showcase(9, "PNL", "player", 1000, 1180, clips)
        before = screen_payload(db.active_showcase_for(9), 1020)
        db.conn.close()
        db = Database(path)
        self.assertEqual(before, screen_payload(db.active_showcase_for(9), 1020))
        db.conn.close()


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        services.db.conn.close()
        TEMP.cleanup()
