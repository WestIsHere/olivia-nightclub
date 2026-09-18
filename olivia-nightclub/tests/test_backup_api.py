"""Exercise the real ASGI authentication and download, without an HTTP client package."""
import asyncio
import contextlib
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory(prefix="olivia-backup-api-test-")
os.environ["OLIVIA_DB"] = str(Path(TEMP.name) / "test.db")
os.environ["OLIVIA_REQUIRE_EXISTING_DB"] = "0"
from server import app as application
from server import services


async def request(token=None):
    messages = []
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": "GET", "scheme": "http", "path": "/api/admin/backup",
             "raw_path": b"/api/admin/backup", "query_string": b"", "root_path": "",
             "headers": [(b"cookie", f"olivia_session={token}".encode())] if token else [],
             "client": ("192.0.2.1", 12345), "server": ("test", 80)}

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await application.app(scope, receive, send)
    start = next(m for m in messages if m["type"] == "http.response.start")
    return start["status"], dict(start["headers"]), b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body")


class BackupApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name, admin in (("player", False), ("owner", True)):
            user = services.register(name, name, "fixture-hash", name + " Club", is_admin=admin)
            services.db.create_session(name + "-session", user["id"], 3600)

    def test_anonymous_and_non_admin_cannot_download(self):
        self.assertEqual(asyncio.run(request())[0], 401)
        self.assertEqual(asyncio.run(request("player-session"))[0], 403)

    def test_admin_download_complete_private_and_temporary_file_cleaned(self):
        real_temporary = tempfile.TemporaryDirectory
        created = []

        def track(*args, **kwargs):
            result = real_temporary(*args, **kwargs)
            created.append(Path(result.name))
            return result

        expected = list(services.db.conn.iterdump())
        with patch.object(application.tempfile, "TemporaryDirectory", side_effect=track):
            status, headers, body = asyncio.run(request("owner-session"))
        self.assertEqual(status, 200)
        self.assertEqual(headers[b"cache-control"], b"no-store, private")
        self.assertIn(b"attachment;", headers[b"content-disposition"])
        self.assertEqual(headers[b"x-backup-sha256"].decode(), hashlib.sha256(body).hexdigest())
        self.assertTrue(body.startswith(b"SQLite format 3\x00"))
        saved = Path(TEMP.name) / "download.db"
        saved.write_bytes(body)
        with contextlib.closing(sqlite3.connect(saved)) as connection:
            self.assertEqual(list(connection.iterdump()), expected)
        self.assertTrue(created)
        self.assertTrue(all(not path.exists() for path in created))


if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        services.db.conn.close()
        TEMP.cleanup()
