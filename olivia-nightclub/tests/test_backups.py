import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import backups
from server.db import Database


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {"RENDER": "false", "OLIVIA_REQUIRE_EXISTING_DB": "0"})
        self.environment.start()
        self.db = Database(str(self.root / "live.db"))
        self.db.conn.execute("PRAGMA wal_autocheckpoint=0")
        # Populate every game table, including authentication and history rows.
        for table in sorted(backups.REQUIRED_TABLES):
            columns = self.db.conn.execute(f'PRAGMA table_info("{table}")').fetchall()
            names, values = [], []
            for column in columns:
                names.append('"' + column["name"] + '"')
                value = 1 if column["type"] == "INTEGER" else 123.25 if column["type"] == "REAL" else "fixture"
                if column["name"] == "state":
                    value = json.dumps({"name": "Club", "cash": 123456, "bitcoin": 0.12345678,
                                        "crypto": {"ETH": "1.23456789"}, "cars": {"porsche": 1}})
                values.append(value)
            self.db.conn.execute(f'INSERT INTO "{table}" ({",".join(names)}) VALUES ({",".join("?" for _ in values)})', values)

    def tearDown(self):
        self.db.conn.close()
        self.environment.stop()
        self.temp.cleanup()

    def test_all_tables_and_wal_survive_backup_restore(self):
        expected = list(self.db.conn.iterdump())
        saved = self.root / "backup.db"
        report = self.db.backup_to(saved)
        self.assertEqual(report["sha256"], hashlib.sha256(saved.read_bytes()).hexdigest())
        self.assertTrue(all(value == 1 for value in report["rows"].values()))
        restored = self.root / "restored.db"
        backups.restore(saved, restored)
        with contextlib.closing(sqlite3.connect(restored)) as connection:
            self.assertEqual(list(connection.iterdump()), expected)
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "delete")
        self.assertFalse(Path(str(saved) + "-wal").exists())
        with patch.dict(os.environ, {"OLIVIA_REQUIRE_EXISTING_DB": "1"}):
            loaded = Database(str(restored))
            self.assertEqual(list(loaded.conn.iterdump()), expected)
            loaded.conn.close()

    def test_never_overwrites_destination_even_if_empty(self):
        for content in (b"keep me", b""):
            destination = self.root / "exists.db"
            destination.write_bytes(content)
            with self.assertRaises(FileExistsError):
                self.db.backup_to(destination)
            self.assertEqual(destination.read_bytes(), content)

    def test_sidecar_and_active_transaction_refused(self):
        destination = self.root / "new.db"
        Path(str(destination) + "-wal").write_bytes(b"keep WAL")
        with self.assertRaises(FileExistsError):
            self.db.backup_to(destination)
        self.db.begin()
        with self.assertRaises(RuntimeError):
            self.db.backup_to(self.root / "transaction.db")
        self.db.rollback()

    def test_corrupt_incomplete_and_orphaned_data_refused(self):
        broken = self.root / "broken.db"
        broken.write_bytes(b"not a database")
        with self.assertRaises(sqlite3.DatabaseError):
            backups.restore(broken, self.root / "bad-copy.db")
        self.assertFalse((self.root / "bad-copy.db").exists())
        with contextlib.closing(sqlite3.connect(self.root / "partial.db")) as connection:
            connection.execute("CREATE TABLE users(id INTEGER)")
        with self.assertRaises(ValueError):
            backups.restore(self.root / "partial.db", self.root / "partial-copy.db")
        self.db.conn.execute("UPDATE clubs SET user_id=999")
        with self.assertRaises(ValueError):
            self.db.backup_to(self.root / "orphan.db")
        self.assertFalse((self.root / "orphan.db").exists())
        self.assertEqual(list(self.root.glob(".olivia-snapshot-*")), [])

    def test_missing_source_never_created_and_render_fails_closed(self):
        missing = self.root / "missing.db"
        with self.assertRaises(FileNotFoundError):
            backups.inspect_database(missing)
        with patch.dict(os.environ, {"RENDER": "true"}):
            os.environ.pop("OLIVIA_REQUIRE_EXISTING_DB", None)
            with self.assertRaisesRegex(RuntimeError, "aucune base vide"):
                Database(str(missing))
        self.assertFalse(missing.exists())

    def test_corrupt_existing_database_is_not_changed(self):
        damaged = self.root / "damaged.db"
        damaged.write_bytes(b"original damaged bytes")
        with patch.dict(os.environ, {"OLIVIA_REQUIRE_EXISTING_DB": "1"}):
            with self.assertRaises(RuntimeError):
                Database(str(damaged))
        self.assertEqual(damaged.read_bytes(), b"original damaged bytes")


if __name__ == "__main__":
    unittest.main()
