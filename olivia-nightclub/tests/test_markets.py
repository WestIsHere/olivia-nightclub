import copy
import os
import sys
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory(prefix="olivia-market-tests-")
os.environ["OLIVIA_DB"] = str(Path(TEMP.name) / "test.db")
from server import engine, markets, services
from server.config import build_config


class MarketsTests(unittest.TestCase):
    def setUp(self):
        self.cfg = build_config()
        self.club = engine.new_club(self.cfg, "Market test")
        self.club["cash"] = 1_000_000
        self.quote = {"price": 65000, "updated_at": 1000}

    def test_fractional_buy_sell_fee_rounding_and_conservation(self):
        ok, _, buy = markets.trade(self.club, "BTC", "buy", "0.12345678", self.quote, 1001)
        self.assertTrue(ok)
        self.assertEqual(markets.balance(self.club, "BTC"), Decimal("0.12345678"))
        ok, _, sell = markets.trade(self.club, "BTC", "sell", "0.12345678", self.quote, 1001)
        self.assertTrue(ok)
        self.assertEqual(markets.balance(self.club, "BTC"), 0)
        self.assertLess(self.club["cash"], 1_000_000)
        self.assertEqual(self.club["cash"], 1_000_000 - buy["cost"] + sell["gain"])

    def test_invalid_input_and_stale_quotes_do_not_mutate(self):
        old = copy.deepcopy(self.club)
        for amount in (True, None, {}, "NaN", "Infinity", "-1", "0", "0.000000001", "1000001"):
            self.assertFalse(markets.trade(self.club, "ETH", "buy", amount, self.quote, 1001)[0])
        for quote, now in ((None, 1001), (self.quote, 1091), (self.quote, 999),
                           ({"price": float("nan"), "updated_at": 1000}, 1001)):
            self.assertEqual(markets.trade(self.club, "ETH", "buy", "1", quote, now)[1], "MARKET_STALE")
        self.assertFalse(markets.trade(self.club, "SCAM", "buy", "1", self.quote, 1001)[0])
        self.assertEqual(old, self.club)

    def test_small_orders_cannot_mint_money(self):
        cheap = {"price": .076, "updated_at": 1000}
        self.assertEqual(markets.trade(self.club, "DOGE", "buy", "1", cheap, 1001)[2]["cost"], 1)
        before = copy.deepcopy(self.club)
        self.assertEqual(markets.trade(self.club, "DOGE", "sell", "1", cheap, 1001)[1], "MINIMUM")
        self.assertEqual(self.club, before)
        self.assertEqual(markets.trade(self.club, "ETH", "sell", "1", self.quote, 1001)[1], "NOT_OWNED")

    def test_legacy_bitcoins_survive_fractional_transfer(self):
        self.club["bitcoin"] = 3
        target = engine.new_club(self.cfg, "Other")
        ok, _, _ = engine.trade_apply(self.cfg, self.club, target, "bitcoin", ".125")
        self.assertTrue(ok)
        self.assertEqual(self.club["bitcoin"], 2.875)
        self.assertEqual(target["bitcoin"], .125)
        self.assertEqual(self.club["bitcoin"] + target["bitcoin"], 3)

    def test_net_worth_uses_current_crypto_and_luxury_prices(self):
        self.club.update(bitcoin=.5, crypto={"ETH": "2.5"}, cars=["audi_rs3"], watches=["day_date"])
        market = {"crypto": {"BTC": {"price": 60000}, "ETH": {"price": 2000}},
                  "cars": {"audi_rs3": {"price": 35000}}, "watches": {"day_date": {"price": 40000}}}
        dynamic = markets.priced_config(self.cfg, market)
        self.assertEqual(engine.net_worth(dynamic, self.club), 1_110_000)
        self.assertEqual(self.cfg["shop"]["cars"]["audi_rs3"]["price"], 30000)
        self.assertEqual(engine.shop_sell(dynamic, self.club, "watches", "day_date")[2]["gain"], 30000)

    def test_luxury_global_history_bounds_and_restart(self):
        state = {"seed": "test-seed"}
        markets.advance_luxury(state, self.cfg["shop"], 6000)
        markets.advance_luxury(state, self.cfg["shop"], 6060)
        self.assertEqual(len(state["cars"]["audi_rs3"]["history"]), 2)
        saved = copy.deepcopy(state)
        markets.advance_luxury(state, self.cfg["shop"], 7200)
        markets.advance_luxury(saved, self.cfg["shop"], 7200)
        self.assertEqual(state, saved)
        self.assertTrue(any(row["price"] != self.cfg["shop"][cat][key]["price"]
                            for cat in ("cars", "watches") for key, row in state[cat].items()))
        markets.advance_luxury(state, self.cfg["shop"], 1000000)
        for cat in ("cars", "watches"):
            for key, row in state[cat].items():
                base = self.cfg["shop"][cat][key]["price"]
                self.assertTrue(.45 * base <= row["price"] <= 2.5 * base)
                self.assertLessEqual(len(row["history"]), 289)
        self.assertNotIn("seed", markets.public_snapshot(state, self.cfg["shop"], 1000000))

    def test_bad_provider_quotes_are_not_replaced_by_fake_prices(self):
        with patch.object(markets, "request_public", return_value={"XXBTZEUR": {"c": ["NaN"], "o": "2"}}):
            with self.assertRaises(ValueError):
                markets.fetch_tickers()

    def test_bitcoin_amplifies_both_directions_without_polling_drift(self):
        initial, active = markets.amplify_bitcoin({"price": 65000}, {"price": 70000, "updated_at": 1000})
        self.assertFalse(active)
        self.assertEqual(initial["price"], 65000)  # No windfall at activation.
        up, active = markets.amplify_bitcoin(initial, {"price": 70700, "updated_at": 1015})
        self.assertTrue(active)
        self.assertAlmostEqual(up["price"], 65000 * 1.01**5)
        self.assertEqual(up["market_price"], 70700)
        down, _ = markets.amplify_bitcoin(up, {"price": 69300, "updated_at": 1030})
        self.assertAlmostEqual(down["price"], 65000 * .99**5)
        repeated, _ = markets.amplify_bitcoin(copy.deepcopy(down), {"price": 69300, "updated_at": 1045})
        self.assertEqual(down["price"], repeated["price"])
        back, _ = markets.amplify_bitcoin(repeated, {"price": 70000, "updated_at": 1060})
        self.assertEqual(back["price"], initial["price"])

    def test_service_shared_snapshot_persistence_outage_and_legacy_route(self):
        user = services.register("market_test", "Market test", "test", "Market Club")
        club, _ = services.db.get_club(user["id"])
        club["cash"] = 1000000
        services.db.save_club(user["id"], club)
        now = time.time()
        quote = {"price": 1000, "updated_at": now, "name": "Bitcoin", "change_pct": 2}
        with patch.object(markets, "fetch_tickers", return_value={"BTC": quote}), \
             patch.object(markets, "fetch_history", return_value=[[now - 300, 990]]), \
             patch.object(services.hub, "broadcast") as broadcast:
            services.update_markets()
        self.assertEqual(broadcast.call_args.args[0], "markets")
        self.assertEqual(services.db.get_setting("live_markets_v1")["crypto"]["BTC"]["price"], 1000)
        self.assertEqual(services.action_bitcoin(user, "buy", ".5")["cost"], 503)
        services._market_state["crypto"]["BTC"]["updated_at"] = now - 100
        with patch.object(markets, "fetch_tickers", side_effect=OSError("offline")):
            services.update_markets()
        self.assertTrue(services.market_view()["crypto"]["BTC"]["stale"])
        before = services.db.get_club(user["id"])[0]
        with self.assertRaises(services.GameError) as err:
            services.action_bitcoin(user, "buy", 1)
        self.assertEqual(err.exception.code, "MARKET_STALE")
        after = services.db.get_club(user["id"])[0]
        self.assertEqual(before["cash"], after["cash"])
        with self.assertRaises(services.GameError) as err:
            services.action_shop(user, "buy", "cars", "audi_rs3", -1)
        self.assertEqual(err.exception.code, "PRICE_CHANGED")


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        services.db.conn.close()
        TEMP.cleanup()
