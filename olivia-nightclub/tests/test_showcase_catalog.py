"""Contrats du catalogue et réservation de chaque artiste, sans base de données."""
import copy
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.artists import RAP_SELECTION, RAP_ARTISTS
from server.config import ARTIST_ORDER, build_config, public_config
from server import engine


class ShowcaseCatalogTests(unittest.TestCase):
    def test_catalog_and_public_data(self):
        cfg = build_config()
        self.assertEqual(len(RAP_SELECTION), 100)
        self.assertEqual(len(RAP_ARTISTS), 100)
        self.assertEqual(len(cfg["artist_order"]), len(set(cfg["artist_order"])))
        self.assertEqual(set(cfg["artist_order"]), set(cfg["artists"]))
        self.assertTrue(set(ARTIST_ORDER) <= set(cfg["artists"]))
        public = public_config(cfg)
        self.assertIn("showcase_default_phrase", public)
        for name, spec in RAP_ARTISTS.items():
            self.assertEqual(public["artists"][name], spec)
            self.assertTrue(1 <= spec["rating"] <= 100)
            self.assertTrue(0 < spec["bonus"] <= 1)
            self.assertGreater(spec["cost"], 0)
            for phrase, low, high in cfg["showcase_phrases"][name]:
                self.assertIn(name, phrase)
                self.assertTrue(0 < low <= high)

    def test_all_artists_booking_payment_service_and_cooldown(self):
        cfg = build_config()
        for name, spec in RAP_ARTISTS.items():
            with self.subTest(artist=name):
                club = engine.new_club(cfg, "Test", now=1000)
                club["cash"] = spec["cost"] - 1
                before = copy.deepcopy(club)
                self.assertEqual(engine.book_showcase(cfg, club, name)[1], "NO_MONEY")
                self.assertEqual(club, before)
                club["cash"] += 1
                self.assertTrue(engine.book_showcase(cfg, club, name)[0])
                self.assertEqual(club["cash"], 0)
                self.assertEqual(club["showcase_bonus"], spec["bonus"])
                self.assertEqual(engine.book_showcase(cfg, club, name)[1], "ALREADY")
                reports = engine.process_ticks(cfg, club, now=1181, rng=random.Random(42))
                self.assertEqual(reports[0]["showcase"]["artist"], name)
                self.assertGreater(reports[0]["showcase"]["clients"], 0)
                self.assertFalse(club["showcase_pending"])
                self.assertEqual(engine.book_showcase(cfg, club, name)[1], "COOLDOWN")

    def test_saved_order_and_admin_prices(self):
        cfg = build_config({"artist_order": ["Lagui", "Gims", "Gims", "inconnu"],
                            "artists": {"Ninho": {"cost": 12345}}})
        self.assertEqual(set(cfg["artist_order"]), set(cfg["artists"]))
        self.assertEqual(cfg["artist_order"][:2], ["Lagui", "Gims"])
        self.assertEqual(engine.showcase_cost_for_artist(cfg, "Ninho"), 12345)
        self.assertEqual(engine.showcase_cost_for_artist(cfg, "Lagui"), 25000)
        self.assertEqual(engine.showcase_cost_for_artist(cfg, "Bello&Dallas"), 15000)


if __name__ == "__main__":
    unittest.main()
