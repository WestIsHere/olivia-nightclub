"""
Stockage SQLite (stdlib). Un seul fichier : data/olivia.db

Le club est stocké comme document JSON (même structure que nightclub_data.json
du bot) → migration triviale, et le moteur reste identique au bot.
Autour : tables normalisées pour l'historique, la banque, les notifications,
les trades, le flux de la ville et la configuration admin.
"""

import json
import os
import sqlite3
import threading
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.environ.get("OLIVIA_DB", os.path.join(DATA_DIR, "olivia.db"))

LOCK = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    avatar TEXT NOT NULL DEFAULT '♣',
    is_admin INTEGER NOT NULL DEFAULT 0,
    discord_id TEXT UNIQUE,
    created_at REAL NOT NULL,
    last_seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS clubs (
    user_id INTEGER PRIMARY KEY,
    slot INTEGER NOT NULL,
    state TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS service_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    service_no INTEGER NOT NULL,
    ts REAL NOT NULL,
    clients INTEGER NOT NULL,
    vips INTEGER NOT NULL,
    bar INTEGER NOT NULL,
    entry INTEGER NOT NULL,
    vip INTEGER NOT NULL,
    total INTEGER NOT NULL,
    salary INTEGER NOT NULL,
    showcase_artist TEXT,
    showcase_clients INTEGER,
    combos TEXT,
    fun_title TEXT,
    cash_after INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_service_user_ts ON service_log(user_id, ts);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    amount INTEGER NOT NULL,
    label TEXT NOT NULL,
    detail TEXT,
    balance_after INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_user_ts ON transactions(user_id, ts);
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    icon TEXT NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    data TEXT,
    read INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, id);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    trade_type TEXT NOT NULL,
    value TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    resolved_at REAL
);
CREATE TABLE IF NOT EXISTS city_feed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    user_id INTEGER,
    icon TEXT NOT NULL,
    text TEXT NOT NULL,
    kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audio_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    file_url TEXT UNIQUE NOT NULL,
    duration REAL,
    enabled INTEGER NOT NULL DEFAULT 1,
    weight REAL NOT NULL DEFAULT 1.0
);
CREATE TABLE IF NOT EXISTS active_showcases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    artist TEXT NOT NULL,
    source TEXT NOT NULL,
    started_at REAL NOT NULL,
    ends_at REAL NOT NULL,
    status TEXT NOT NULL,
    ended_at REAL
);
CREATE INDEX IF NOT EXISTS idx_showcase_club ON active_showcases(club_id, status);
CREATE TABLE IF NOT EXISTS robberies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attacker_id INTEGER NOT NULL,
    victim_id INTEGER NOT NULL,
    result TEXT NOT NULL,
    amount INTEGER NOT NULL,
    chance INTEGER NOT NULL,
    ts REAL NOT NULL
);
"""

# Colonnes ajoutées après la première version (migration douce)
MIGRATIONS = [
    ("active_showcases", "screen_playlist", "TEXT"),
    ("users", "audio_prefs", "TEXT"),
    ("audio_assets", "kind", "TEXT NOT NULL DEFAULT 'file'"),   # 'file' | 'youtube'
    ("audio_assets", "title", "TEXT"),
    ("audio_assets", "note", "TEXT"),
]


class Database:
    def __init__(self, path=DB_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(SCHEMA)
        for table, column, ctype in MIGRATIONS:
            cols = [r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if column not in cols:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ctype}")

    # ---------------- transactions ----------------
    def begin(self):
        self.conn.execute("BEGIN")

    def commit(self):
        self.conn.execute("COMMIT")

    def rollback(self):
        try:
            self.conn.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass

    # ---------------- settings / config ----------------
    def get_setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )

    # ---------------- users ----------------
    def create_user(self, username, display_name, password_hash, avatar, is_admin=0, discord_id=None):
        now = time.time()
        cur = self.conn.execute(
            "INSERT INTO users(username, display_name, password_hash, avatar, is_admin, discord_id, created_at, last_seen)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (username, display_name, password_hash, avatar, is_admin, discord_id, now, now),
        )
        return cur.lastrowid

    def get_user(self, user_id):
        row = self.conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username):
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None

    def list_users(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM users ORDER BY id").fetchall()]

    def count_users(self):
        return self.conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]

    def touch_user(self, user_id, ts=None):
        self.conn.execute("UPDATE users SET last_seen=? WHERE id=?", (ts or time.time(), user_id))

    def set_admin(self, user_id, is_admin):
        self.conn.execute("UPDATE users SET is_admin=? WHERE id=?", (1 if is_admin else 0, user_id))

    def update_user(self, user_id, **fields):
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE users SET {cols} WHERE id=?", (*fields.values(), user_id))

    def reset_server(self, keep_user_id, keep_session_token=None):
        """Efface toutes les données de jeu en conservant uniquement l'admin courant.

        Le compte admin courant et sa session peuvent rester actifs afin que
        l'administrateur puisse continuer à utiliser le panneau après le reset.
        Les assets audio, qui sont des fichiers de déploiement et non des sauvegardes,
        ne sont pas supprimés.
        """
        tables = (
            "clubs", "service_log", "transactions", "notifications",
            "trades", "city_feed", "active_showcases", "robberies",
        )
        with LOCK:
            self.begin()
            try:
                for table in tables:
                    self.conn.execute(f"DELETE FROM {table}")
                # Les réglages admin sont aussi des données persistantes :
                # on revient aux valeurs par défaut du projet.
                self.conn.execute("DELETE FROM settings")
                # Tous les comptes et sessions disparaissent sauf l'admin qui
                # vient de lancer l'opération.
                self.conn.execute("DELETE FROM users WHERE id != ?", (int(keep_user_id),))
                if keep_session_token:
                    self.conn.execute("DELETE FROM sessions WHERE token != ?", (keep_session_token,))
                else:
                    self.conn.execute("DELETE FROM sessions")
                # Garantit que le compte conservé reste administrateur.
                self.conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (int(keep_user_id),))
                self.commit()
            except Exception:
                self.rollback()
                raise

    def delete_user_data(self, user_id):
        for table in ("clubs", "service_log", "transactions", "notifications", "sessions"):
            col = "user_id"
            self.conn.execute(f"DELETE FROM {table} WHERE {col}=?", (user_id,))
        self.conn.execute("DELETE FROM trades WHERE sender_id=? OR target_id=?", (user_id, user_id))

    # ---------------- sessions ----------------
    def create_session(self, token, user_id, ttl_seconds):
        now = time.time()
        self.conn.execute("INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES(?,?,?,?)",
                          (token, user_id, now, now + ttl_seconds))

    def get_session_user(self, token):
        row = self.conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token=? AND s.expires_at > ?",
            (token, time.time()),
        ).fetchone()
        return dict(row) if row else None

    def delete_session(self, token):
        self.conn.execute("DELETE FROM sessions WHERE token=?", (token,))

    def purge_sessions(self):
        self.conn.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))

    # ---------------- clubs ----------------
    def next_slot(self):
        row = self.conn.execute("SELECT COALESCE(MAX(slot), -1) + 1 AS s FROM clubs").fetchone()
        return row["s"]

    def create_club(self, user_id, state, slot=None):
        slot = self.next_slot() if slot is None else slot
        self.conn.execute("INSERT INTO clubs(user_id, slot, state, updated_at) VALUES(?,?,?,?)",
                          (user_id, slot, json.dumps(state, ensure_ascii=False), time.time()))
        return slot

    def get_club(self, user_id):
        row = self.conn.execute("SELECT * FROM clubs WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return None, None
        return json.loads(row["state"]), row["slot"]

    def save_club(self, user_id, state):
        self.conn.execute("UPDATE clubs SET state=?, updated_at=? WHERE user_id=?",
                          (json.dumps(state, ensure_ascii=False), time.time(), user_id))

    def delete_club(self, user_id):
        self.conn.execute("DELETE FROM clubs WHERE user_id=?", (user_id,))

    def all_clubs(self):
        rows = self.conn.execute(
            "SELECT c.user_id, c.slot, c.state, u.display_name, u.username, u.avatar, u.last_seen, u.created_at"
            " FROM clubs c JOIN users u ON u.id = c.user_id ORDER BY c.slot"
        ).fetchall()
        out = []
        for r in rows:
            out.append({
                "user_id": r["user_id"], "slot": r["slot"], "state": json.loads(r["state"]),
                "display_name": r["display_name"], "username": r["username"], "avatar": r["avatar"],
                "last_seen": r["last_seen"], "created_at": r["created_at"],
            })
        return out

    # ---------------- service log ----------------
    def add_service(self, user_id, report):
        showcase = report.get("showcase") or {}
        fun = report.get("fun_event") or {}
        self.conn.execute(
            "INSERT INTO service_log(user_id, service_no, ts, clients, vips, bar, entry, vip, total, salary,"
            " showcase_artist, showcase_clients, combos, fun_title, cash_after) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, report["service_no"], report["time"], report["clients"], report["vips"], report["bar"],
             report["entry"], report["vip"], report["total"], report["salary"], showcase.get("artist"),
             showcase.get("clients"), ",".join(report.get("combos") or []), fun.get("title"), report["cash_after"]),
        )

    def services_since(self, user_id, ts):
        rows = self.conn.execute(
            "SELECT * FROM service_log WHERE user_id=? AND ts > ? ORDER BY ts", (user_id, ts)
        ).fetchall()
        return [dict(r) for r in rows]

    def recent_services(self, user_id, limit=50):
        rows = self.conn.execute(
            "SELECT * FROM service_log WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def service_totals(self, user_id, since_ts):
        row = self.conn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(total),0) AS total, COALESCE(SUM(bar),0) AS bar,"
            " COALESCE(SUM(entry),0) AS entry, COALESCE(SUM(vip),0) AS vip, COALESCE(SUM(clients),0) AS clients,"
            " COALESCE(SUM(vips),0) AS vips, COALESCE(SUM(salary),0) AS salary,"
            " SUM(CASE WHEN showcase_artist IS NOT NULL THEN 1 ELSE 0 END) AS showcases"
            " FROM service_log WHERE user_id=? AND ts >= ?",
            (user_id, since_ts),
        ).fetchone()
        return dict(row)

    def leaderboard_income(self, since_ts):
        rows = self.conn.execute(
            "SELECT user_id, COALESCE(SUM(total),0) AS total, COALESCE(SUM(clients),0) AS clients,"
            " COALESCE(SUM(vips),0) AS vips FROM service_log WHERE ts >= ? GROUP BY user_id",
            (since_ts,),
        ).fetchall()
        return {r["user_id"]: dict(r) for r in rows}

    # ---------------- transactions ----------------
    def add_transaction(self, user_id, kind, amount, label, balance_after, detail=None, ts=None):
        self.conn.execute(
            "INSERT INTO transactions(user_id, ts, kind, amount, label, detail, balance_after) VALUES(?,?,?,?,?,?,?)",
            (user_id, ts or time.time(), kind, int(amount), label,
             json.dumps(detail, ensure_ascii=False) if detail is not None else None, int(balance_after)),
        )

    def recent_transactions(self, user_id, limit=100):
        rows = self.conn.execute(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["detail"] = json.loads(d["detail"]) if d["detail"] else None
            out.append(d)
        return out

    def expenses_since(self, user_id, since_ts):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END),0) AS expenses,"
            " COALESCE(SUM(CASE WHEN amount > 0 AND kind != 'service' THEN amount ELSE 0 END),0) AS other_income"
            " FROM transactions WHERE user_id=? AND ts >= ?",
            (user_id, since_ts),
        ).fetchone()
        return dict(row)

    def expenses_between(self, user_id, since_ts):
        rows = self.conn.execute(
            "SELECT kind, COALESCE(SUM(amount),0) AS amount, COUNT(*) AS n FROM transactions"
            " WHERE user_id=? AND ts > ? GROUP BY kind",
            (user_id, since_ts),
        ).fetchall()
        return {r["kind"]: {"amount": r["amount"], "n": r["n"]} for r in rows}

    # ---------------- notifications ----------------
    def add_notification(self, user_id, kind, icon, title, text, data=None, ts=None, limit=300):
        cur = self.conn.execute(
            "INSERT INTO notifications(user_id, ts, kind, icon, title, text, data) VALUES(?,?,?,?,?,?,?)",
            (user_id, ts or time.time(), kind, icon, title, text,
             json.dumps(data, ensure_ascii=False) if data is not None else None),
        )
        # Purge au-delà de la limite
        self.conn.execute(
            "DELETE FROM notifications WHERE user_id=? AND id NOT IN"
            " (SELECT id FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT ?)",
            (user_id, user_id, limit),
        )
        return cur.lastrowid

    def list_notifications(self, user_id, limit=80):
        rows = self.conn.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d["data"]) if d["data"] else None
            out.append(d)
        return out

    def unread_count(self, user_id):
        return self.conn.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND read=0", (user_id,)
        ).fetchone()["n"]

    def mark_read(self, user_id, ids=None):
        if ids:
            marks = ",".join("?" for _ in ids)
            self.conn.execute(f"UPDATE notifications SET read=1 WHERE user_id=? AND id IN ({marks})",
                              (user_id, *ids))
        else:
            self.conn.execute("UPDATE notifications SET read=1 WHERE user_id=?", (user_id,))

    # ---------------- trades ----------------
    def create_trade(self, sender_id, target_id, trade_type, value):
        cur = self.conn.execute(
            "INSERT INTO trades(sender_id, target_id, trade_type, value, status, created_at)"
            " VALUES(?,?,?,?,'pending',?)",
            (sender_id, target_id, trade_type, str(value), time.time()),
        )
        return cur.lastrowid

    def get_trade(self, trade_id):
        row = self.conn.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        return dict(row) if row else None

    def set_trade_status(self, trade_id, status):
        self.conn.execute("UPDATE trades SET status=?, resolved_at=? WHERE id=?", (status, time.time(), trade_id))

    def list_trades_for(self, user_id, limit=40):
        rows = self.conn.execute(
            "SELECT t.*, su.display_name AS sender_name, tu.display_name AS target_name"
            " FROM trades t JOIN users su ON su.id=t.sender_id JOIN users tu ON tu.id=t.target_id"
            " WHERE t.sender_id=? OR t.target_id=? ORDER BY t.id DESC LIMIT ?",
            (user_id, user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def pending_trades_count(self, user_id):
        return self.conn.execute(
            "SELECT COUNT(*) AS n FROM trades WHERE target_id=? AND status='pending'", (user_id,)
        ).fetchone()["n"]

    # ---------------- audio ----------------
    def list_audio_assets(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM audio_assets ORDER BY category, key, file_url").fetchall()]

    def add_audio_asset(self, category, key, file_url, duration, kind="file", title=None, note=None):
        cur = self.conn.execute(
            "INSERT INTO audio_assets(category, key, file_url, duration, kind, title, note) VALUES(?,?,?,?,?,?,?)",
            (category, key, file_url, duration, kind, title, note))
        return cur.lastrowid

    def get_audio_asset_by_url(self, file_url):
        row = self.conn.execute("SELECT * FROM audio_assets WHERE file_url=?", (file_url,)).fetchone()
        return dict(row) if row else None

    def update_audio_asset_meta(self, asset_id, duration):
        self.conn.execute("UPDATE audio_assets SET duration=? WHERE id=?", (duration, asset_id))

    def update_audio_asset(self, asset_id, enabled=None, weight=None):
        if enabled is not None:
            self.conn.execute("UPDATE audio_assets SET enabled=? WHERE id=?", (1 if enabled else 0, asset_id))
        if weight is not None:
            self.conn.execute("UPDATE audio_assets SET weight=? WHERE id=?", (float(weight), asset_id))

    def delete_audio_asset(self, asset_id):
        self.conn.execute("DELETE FROM audio_assets WHERE id=?", (asset_id,))

    def get_audio_prefs(self, user_id):
        row = self.conn.execute("SELECT audio_prefs FROM users WHERE id=?", (user_id,)).fetchone()
        if not row or not row["audio_prefs"]:
            return None
        try:
            return json.loads(row["audio_prefs"])
        except ValueError:
            return None

    def set_audio_prefs(self, user_id, prefs):
        self.conn.execute("UPDATE users SET audio_prefs=? WHERE id=?",
                          (json.dumps(prefs, ensure_ascii=False), user_id))

    # ---------------- showcases actifs (miroir pour les événements audio) ----------------
    def start_showcase(self, club_id, artist, source, started_at, ends_at, playlist=None):
        self.conn.execute(
            "UPDATE active_showcases SET status='ended', ended_at=? WHERE club_id=? AND status='active'",
            (started_at, club_id))
        cur = self.conn.execute(
            "INSERT INTO active_showcases(club_id, artist, source, started_at, ends_at, status, screen_playlist)"
            " VALUES(?,?,?,?,?,'active',?)", (club_id, artist, source, started_at, ends_at, json.dumps(playlist or [])))
        return cur.lastrowid

    def active_showcase_for(self, club_id):
        row = self.conn.execute("SELECT * FROM active_showcases WHERE club_id=? AND status='active' ORDER BY id DESC LIMIT 1", (club_id,)).fetchone()
        return dict(row) if row else None

    def end_showcase(self, club_id, ended_at):
        rows = self.conn.execute(
            "SELECT * FROM active_showcases WHERE club_id=? AND status='active'", (club_id,)).fetchall()
        self.conn.execute(
            "UPDATE active_showcases SET status='ended', ended_at=? WHERE club_id=? AND status='active'",
            (ended_at, club_id))
        return [dict(r) for r in rows]

    def list_active_showcases(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM active_showcases WHERE status='active' ORDER BY started_at").fetchall()]

    # ---------------- braquages ----------------
    def add_robbery(self, attacker_id, victim_id, result, amount, chance, ts):
        cur = self.conn.execute(
            "INSERT INTO robberies(attacker_id, victim_id, result, amount, chance, ts) VALUES(?,?,?,?,?,?)",
            (attacker_id, victim_id, result, amount, chance, ts))
        return cur.lastrowid

    def recent_robberies(self, limit=20):
        rows = self.conn.execute(
            "SELECT r.*, a.display_name AS attacker_name, v.display_name AS victim_name"
            " FROM robberies r JOIN users a ON a.id=r.attacker_id JOIN users v ON v.id=r.victim_id"
            " ORDER BY r.id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # ---------------- city feed ----------------
    def add_feed(self, icon, text, kind, user_id=None, limit=60):
        self.conn.execute("INSERT INTO city_feed(ts, user_id, icon, text, kind) VALUES(?,?,?,?,?)",
                          (time.time(), user_id, icon, text, kind))
        self.conn.execute(
            "DELETE FROM city_feed WHERE id NOT IN (SELECT id FROM city_feed ORDER BY id DESC LIMIT ?)", (limit,)
        )

    def list_feed(self, limit=40):
        rows = self.conn.execute("SELECT * FROM city_feed ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
