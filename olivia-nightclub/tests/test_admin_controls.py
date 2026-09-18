import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory(prefix="olivia-admin-test-")
os.environ["OLIVIA_DB"] = str(Path(TEMP.name) / "test.db")
from server import services
from server.local_admin import is_host_request


def request(peer="127.0.0.1", host="127.0.0.1:8000", headers=None):
    return SimpleNamespace(client=SimpleNamespace(host=peer),
                           url=urlsplit("http://" + host), headers=headers or {})


class LocalAdminTests(unittest.TestCase):
    def test_localhost_and_ipv6_only(self):
        self.assertTrue(is_host_request(request()))
        self.assertTrue(is_host_request(request("::1", "[::1]:8000")))
        self.assertTrue(is_host_request(request(host="localhost:8000", headers={"origin": "http://localhost:8000"})))
        for peer in ("192.168.1.2", "8.8.8.8", "bad"):
            self.assertFalse(is_host_request(request(peer)))

    def test_proxy_rebinding_and_cross_origin_rejected(self):
        for headers in ({"x-forwarded-for": "127.0.0.1"}, {"forwarded": "for=127.0.0.1"},
                        {"cf-connecting-ip": "127.0.0.1"}, {"x-real-ip": "127.0.0.1"},
                        {"x-forwarded-host": "localhost"}, {"sec-fetch-site": "cross-site"},
                        {"origin": "http://attacker.example"}, {"origin": "http://localhost:8001"}):
            with self.subTest(headers=headers):
                self.assertFalse(is_host_request(request(headers=headers)))
        self.assertFalse(is_host_request(request(host="attacker.example:8000")))

    def test_first_public_player_is_not_administrator(self):
        user = services.register("first_public", "Public", "test", "Public Club")
        self.assertFalse(user["is_admin"])

    def test_targeted_delete_preserves_other_clubs_and_accounts(self):
        admin = services.register("owner", "Owner", "test", "Owner Club", is_admin=True)
        target = services.register("target", "Target", "test", "Target Club")
        other = services.register("other", "Other", "test", "Other Club")
        club, _ = services.db.get_club(target["id"])
        club["cash"] = 1000000
        services.db.save_club(target["id"], club)
        services.action_showcase(target, "PNL")
        trade = services.db.create_trade(target["id"], other["id"], "money", 50)
        unrelated = services.db.create_trade(admin["id"], other["id"], "money", 75)
        self.assertTrue(services.db.active_showcase_for(target["id"]))
        for actor, uid, name in ((target, other["id"], "Other Club"),
                                 (admin, admin["id"], "Owner Club"),
                                 (admin, target["id"], "wrong")):
            with self.assertRaises(services.GameError):
                services.admin_delete_club(actor, uid, name)
        self.assertIsNotNone(services.db.get_club(target["id"])[0])
        sid = services.db.active_showcase_for(target["id"])["id"]
        with patch.object(services.hub, "broadcast") as broadcast:
            result = services.admin_delete_club(admin, target["id"], "Target Club")
        ended_events = [call.args[1] for call in broadcast.call_args_list if call.args[0] == "showcase_ended"]
        self.assertEqual(ended_events[0]["showcase_id"], sid)
        self.assertEqual(result["deleted"], "Target Club")
        self.assertIsNone(services.db.get_club(target["id"])[0])
        self.assertIsNone(services.db.active_showcase_for(target["id"]))
        self.assertIsNotNone(services.db.get_user(target["id"]))
        self.assertEqual(services.db.get_club(other["id"])[0]["name"], "Other Club")
        self.assertEqual(services.db.get_trade(trade)["status"], "cancelled")
        self.assertEqual(services.db.get_trade(unrelated)["status"], "pending")
        self.assertEqual(services.db.recent_transactions(target["id"]), [])
        services.create_club_for(target, "Fresh Club")
        self.assertEqual(services.db.get_club(target["id"])[0]["name"], "Fresh Club")


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        services.db.conn.close()
        TEMP.cleanup()
