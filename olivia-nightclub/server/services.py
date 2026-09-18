"""
Couche services : toutes les opérations du jeu, validées côté serveur.

Chaque action :
  1. prend le verrou global,
  2. met à jour les services écoulés (process_ticks) + événements,
  3. applique la mutation via le moteur,
  4. journalise (service_log / transactions / notifications / flux ville),
  5. sauvegarde et notifie en temps réel (SSE).
"""

import datetime
import copy
import json
import queue
import random
import secrets
import threading
import time

from . import audio as audio_assets
from . import engine
from . import markets
from .showcase_media import choose_playlist, screen_payload
from .config import build_config, public_config
from .db import Database, LOCK

RNG = random.Random()

db = Database()

_config_cache = {"cfg": None}
_market_state = {}
_market_loaded = False
_market_retry_at = 0
_market_failures = 0
_history_cursor = 0


def base_cfg():
    if _config_cache["cfg"] is None:
        _config_cache["cfg"] = build_config(db.get_setting("config_overrides", {}))
    return _config_cache["cfg"]


def cfg():
    return markets.priced_config(base_cfg(), _market_state)


def load_markets():
    global _market_state, _market_loaded
    with LOCK:
        if not _market_loaded:
            _market_state = db.get_setting("live_markets_v1", {})
            markets.advance_luxury(_market_state, base_cfg()["shop"], time.time())
            _market_loaded = True


def market_view():
    return markets.public_snapshot(_market_state, base_cfg()["shop"])


def update_markets():
    """One shared fetch for the server, outside the transaction/game lock."""
    global _market_state, _market_failures, _market_retry_at, _history_cursor
    load_markets()
    quotes, history, symbol = {}, None, None
    now = time.time()
    if now >= _market_retry_at:
        try:
            quotes = markets.fetch_tickers()
            _market_failures = 0
            _market_retry_at = 0
        except Exception:
            _market_failures += 1
            _market_retry_at = now + min(120, 15 * 2 ** min(_market_failures - 1, 3))
        if quotes:
            # BTC uses its own amplified game history, never Kraken's raw curve.
            symbols = [key for key in markets.CATALOG if key != "BTC"]
            symbol = symbols[_history_cursor % len(symbols)]
            _history_cursor += 1
            row = _market_state.get("crypto", {}).get(symbol, {})
            if now - row.get("history_fetched_at", 0) > 3600:
                try:
                    history = markets.fetch_history(symbol)
                except Exception:
                    pass  # Real observed samples remain available; never invent a curve.
    with LOCK:
        state = copy.deepcopy(_market_state)
        stamp = time.time()
        coins = state.setdefault("crypto", {})
        for key, quote in quotes.items():
            old = coins.get(key, {})
            points = old.get("history", [])
            if key == "BTC":
                quote, already_amplified = markets.amplify_bitcoin(old, quote)
                if not already_amplified:
                    points = []
            if key == symbol and history:
                # Replace old candles, retaining observations newer than the downloaded history.
                points = history + [p for p in points if p[0] > history[-1][0]]
            coins[key] = dict(old, **quote, history=markets.history_point(points, quote["updated_at"], quote["price"]))
            if key == "BTC":
                coins[key]["change_pct"] = (quote["price"] / coins[key]["history"][0][1] - 1) * 100
        if symbol in coins and history:
            coins[symbol]["history_fetched_at"] = stamp
        markets.advance_luxury(state, base_cfg()["shop"], stamp)
        db.begin()
        try:
            db.set_setting("live_markets_v1", state)
            db.commit()
        except Exception:
            db.rollback()
            raise
        _market_state = state
        payload = {"markets": market_view(), "shop": cfg()["shop"]}
    hub.broadcast("markets", payload)


def reload_config():
    _config_cache["cfg"] = None
    return cfg()


def money(v):
    return engine.format_money(v)


# ------------------------------------------------------------------
# Temps réel (Server-Sent Events)
# ------------------------------------------------------------------

class Hub:
    def __init__(self):
        self.lock = threading.Lock()
        self.queues = {}  # user_id -> set(queue.Queue)

    def subscribe(self, user_id):
        q = queue.Queue()
        with self.lock:
            self.queues.setdefault(user_id, set()).add(q)
        return q

    def unsubscribe(self, user_id, q):
        with self.lock:
            s = self.queues.get(user_id)
            if s:
                s.discard(q)
                if not s:
                    self.queues.pop(user_id, None)

    def is_online(self, user_id):
        with self.lock:
            return bool(self.queues.get(user_id))

    def online_ids(self):
        with self.lock:
            return set(self.queues.keys())

    def publish(self, user_id, event, data):
        with self.lock:
            targets = list(self.queues.get(user_id, ()))
        for q in targets:
            q.put((event, data))

    def broadcast(self, event, data):
        with self.lock:
            targets = [q for s in self.queues.values() for q in s]
        for q in targets:
            q.put((event, data))


hub = Hub()


# ------------------------------------------------------------------
# Helpers journal
# ------------------------------------------------------------------

def _tx(user_id, club, kind, amount, label, detail=None, ts=None):
    db.add_transaction(user_id, kind, amount, label, int(club.get("cash", 0)), detail, ts)


def notify(user_id, kind, icon, title, text, data=None, ts=None, push=True):
    limit = int(cfg()["web"]["notifications_limit"])
    nid = db.add_notification(user_id, kind, icon, title, text, data, ts, limit)
    if push:
        hub.publish(user_id, "notification", {
            "id": nid, "kind": kind, "icon": icon, "title": title, "text": text,
            "data": data, "ts": ts or time.time(),
        })
    return nid


def feed(icon, text, kind, user_id=None):
    db.add_feed(icon, text, kind, user_id, int(cfg()["web"]["feed_limit"]))
    hub.broadcast("feed", {"icon": icon, "text": text, "kind": kind, "ts": time.time(), "user_id": user_id})


# ------------------------------------------------------------------
# Événements temps réel audio : SHOWCASE_STARTED / SHOWCASE_ENDED / ROBBERY_CREATED
# (le serveur est la seule source de ces événements ; le client ne fait que réagir)
# ------------------------------------------------------------------

def showcase_started(club_id, club, artist, source, started_at, ends_at):
    previous = club.setdefault("last_showcase_videos", {})
    playlist = choose_playlist(cfg(), artist, db.list_audio_assets(), previous.get(artist))
    if playlist:
        previous[artist] = playlist[0]["video_id"]
    sid = db.start_showcase(club_id, artist, source, started_at, ends_at, playlist)
    hub.broadcast("showcase_started", {
        **(screen_payload(db.active_showcase_for(club_id), started_at) or {}),
        "showcase_id": sid, "club_id": club_id, "club_name": club.get("name"), "artist": artist,
        "source": source, "started_at": started_at, "ends_at": ends_at,
    })
    return sid


def showcase_ended(club_id, club, ended_at, reason="served"):
    ended = db.end_showcase(club_id, ended_at)
    for s in ended:
        hub.broadcast("showcase_ended", {
            "showcase_id": s["id"], "club_id": club_id, "club_name": club.get("name"),
            "artist": s["artist"], "ended_at": ended_at, "reason": reason,
        })
    return ended


# ------------------------------------------------------------------
# Cœur : mise à jour d'un club (services + événements)
# ------------------------------------------------------------------

def _log_reports(user_id, club, reports, user_name=None):
    c = cfg()
    for r in reports:
        db.add_service(user_id, r)
        db.add_transaction(user_id, "service", r["total"],
                           f"Service #{r['service_no']}",
                           r["cash_after"], {"bar": r["bar"], "entry": r["entry"], "vip": r["vip"],
                                             "clients": r["clients"], "vips": r["vips"]}, r["time"])
        if r["salary"]:
            db.add_transaction(user_id, "salary", -r["salary"], "Salaire manager",
                               r["cash_after"], None, r["time"])
        notify(user_id, "service", "💰", f"+{money(r['total'])}",
               f"Service #{r['service_no']} : {r['clients']} clients, {r['vips']} VIP.",
               {"service_no": r["service_no"], "bar": r["bar"], "entry": r["entry"], "vip": r["vip"],
                "clients": r["clients"], "vips": r["vips"], "total": r["total"]}, r["time"], push=False)
        if r["showcase"]:
            s = r["showcase"]
            showcase_ended(user_id, club, r["time"])
            notify(user_id, "showcase", "🎤", f"Showcase terminé — {s['artist']}",
                   f"{s['text']} ({'+' if s['clients'] >= 0 else ''}{s['clients']} clients)",
                   s, r["time"], push=False)
            feed("🎤", f"{club['name']} : showcase de {s['artist']} ({'+' if s['clients'] >= 0 else ''}{s['clients']} clients)",
                 "showcase", user_id)
        for combo_id in r["combos"]:
            combo = c["combos"].get(combo_id, {})
            notify(user_id, "combo", "🔥", "COMBO DÉCLENCHÉ",
                   f"{combo.get('name', combo_id)} : la salle explose.", {"combo": combo_id}, r["time"], push=False)
        if r["manager_showcase"]:
            showcase_started(user_id, club, r["manager_showcase"], "manager", r["time"],
                             r["time"] + int(c["tick_seconds"]))
            notify(user_id, "manager", "♣", "Showcase organisé par votre manager",
                   f"{r['manager_showcase']} est programmé pour le prochain service.", None, r["time"], push=False)
        if r["manager_unpaid"]:
            notify(user_id, "manager", "⚠️", "Salaire impayé",
                   "Trésorerie insuffisante : le manager n'a produit aucun bonus ce service.", None, r["time"], push=False)
        if r["vips"] >= 2:
            notify(user_id, "vip", "👑", "VIP arrivés", f"{r['vips']} VIP ont dépensé {money(r['vip'])}.",
                   None, r["time"], push=False)


def _log_event(user_id, club, event):
    if not event:
        return
    if event.get("cash_delta"):
        db.add_transaction(user_id, "event", event["cash_delta"], event["title"],
                           int(club.get("cash", 0)), None, event["time"])
    notify(user_id, "event", event["title"][:2].strip() or "🚨", event["title"], event["text"], event, event["time"])


def touch_club(user_id, now=None, save=True):
    """Met à jour un club : services écoulés + événement éventuel. Retourne (club, slot, reports, event)."""
    now = time.time() if now is None else now
    club, slot = db.get_club(user_id)
    if club is None:
        return None, None, [], None
    c = cfg()
    engine.ensure_club_fields(c, club)
    reports = engine.process_ticks(c, club, now, RNG)
    event = engine.process_random_event(c, club, now, RNG)
    if reports:
        _log_reports(user_id, club, reports)
    if event:
        _log_event(user_id, club, event)
    if save and (reports or event):
        db.save_club(user_id, club)
    return club, slot, reports, event


def process_world():
    """Boucle de fond : fait avancer TOUS les clubs (comme le classement du bot)."""
    now = time.time()
    with LOCK:
        db.begin()
        try:
            changed = []
            for entry in db.all_clubs():
                uid = entry["user_id"]
                club, slot, reports, event = touch_club(uid, now)
                if reports or event:
                    changed.append((uid, club, reports, event))
            db.commit()
        except Exception:
            db.rollback()
            raise
    for uid, club, reports, event in changed:
        for r in reports:
            hub.publish(uid, "service", r)
        if event:
            hub.publish(uid, "event", event)
    if changed:
        hub.broadcast("city", {"changed": [uid for uid, *_ in changed]})


# ------------------------------------------------------------------
# Vues
# ------------------------------------------------------------------

PRIVATE_KEYS = {
    "client_penalty_next", "client_bonus_next", "coca_cherry_pending", "bar_mult_next",
    "entry_mult_next", "vip_mult_next", "manager_id", "manager_last_showcase_tick",
    "last_robbery_service", "last_event_check", "blackjack_game", "combos_discovered",
    "artist_last_service", "showcase_bonus", "last_fun_event", "total_bar", "total_entry", "total_vip",
}


def public_club_view(entry, now=None):
    now = time.time() if now is None else now
    c = cfg()
    club = entry["state"]
    engine.ensure_club_fields(c, club)
    level = int(club.get("level", 0))
    last_event = club.get("last_event") or None
    last_show = club.get("last_showcase_event") or None
    return {
        "user_id": entry["user_id"],
        "owner": entry["display_name"],
        "avatar": entry["avatar"],
        "online": hub.is_online(entry["user_id"]),
        "slot": entry["slot"],
        "name": club.get("name"),
        "level": level,
        "level_name": engine.level_name(c, level),
        "cash": int(club.get("cash", 0)),
        "net_worth": engine.net_worth(c, club),
        "last_clients": int(club.get("last_clients", 0)),
        "last_vips": int(club.get("last_vips", 0)),
        "last_income": int(club.get("last_income", 0)),
        "entry_price": float(club.get("entry_price", c["default_entry_price"])),
        "status": engine.club_status(c, club, now),
        "occupancy": engine.occupancy(c, club),
        "equipment": list(club.get("equipment", []) or []),
        "equipment_count": len(club.get("equipment", []) or []),
        "showcase_pending": bool(club.get("showcase_pending")),
        "showcase_artist": club.get("showcase_artist") if club.get("showcase_pending") else None,
        "showcase_screen": club_screen(entry["user_id"], now)["showcase"],
        "last_showcase": {"artist": last_show.get("artist"), "clients": last_show.get("clients"),
                          "time": last_show.get("time")} if last_show else None,
        "last_event": {"title": last_event.get("title"), "time": last_event.get("time")} if last_event else None,
        "showcases_done": int(club.get("showcases_done", 0)),
        "total_clients": int(club.get("total_clients", 0)),
        "total_vip_clients": int(club.get("total_vip_clients", 0)),
        "service_count": int(club.get("service_count", 0)),
        "robbery_power": engine.robbery_power(c, club),
        "cars": list(club.get("cars", []) or []),
        "watches": list(club.get("watches", []) or []),
        "bitcoin": float(club.get("bitcoin", 0)),
        "crypto": dict(club.get("crypto", {})),
        "blackjack_wins": int(club.get("blackjack_wins", 0)),
        "blackjack_losses": int(club.get("blackjack_losses", 0)),
        "drinks_taken": int(club.get("drinks_taken", 0)),
        "next_service": engine.next_service_time(c, club),
        "created_at": club.get("created_at") or entry["created_at"],
        "last_seen": entry.get("last_seen"),
    }


def derived_for(club):
    c = cfg()
    level = int(club.get("level", 0))
    price = float(club.get("entry_price", c["default_entry_price"]))
    manager = engine.get_manager(c, club)
    nxt = level + 1 if level < engine.max_level(c) else None
    cooldowns = {a: engine.artist_cooldown_remaining(c, club, a) for a in c["artist_order"]}
    return {
        "level_name": engine.level_name(c, level),
        "level_info": engine.level_info(c, level),
        "next_level": engine.level_info(c, nxt) if nxt is not None else None,
        "max_entry_price": engine.max_entry_price(c, level),
        "price_client_mult": engine.entry_price_client_multiplier(c, level, price),
        "income_mult": engine.income_multiplier(c, level),
        "showcase_mult": engine.showcase_multiplier(c, level),
        "client_range": engine.client_range_for_level(c, level),
        "bonuses": {
            "bar": engine.equipment_bonus(c, club, "bar_bonus"),
            "entry": engine.equipment_bonus(c, club, "entry_bonus"),
            "vip": engine.equipment_bonus(c, club, "vip_bonus"),
        },
        "manager": manager,
        "next_service": engine.next_service_time(c, club),
        "status": engine.club_status(c, club),
        "occupancy": engine.occupancy(c, club),
        "estimate": engine.estimate_service(c, club),
        "artist_cooldowns": cooldowns,
        "artist_costs": {a: engine.showcase_cost_for_artist(c, a) for a in c["artist_order"]},
        "robbery_power": engine.robbery_power(c, club),
        "robbery_cooldown": engine.robbery_cooldown_remaining(c, club),
        "net_worth": engine.net_worth(c, club),
        "blackjack": engine.public_blackjack(club.get("blackjack_game")),
        "combos_discovered": list(club.get("combos_discovered", []) or []),
    }


def _day_start():
    today = datetime.date.today()
    return time.mktime(today.timetuple())


def away_recap(user_id, last_seen, now):
    c = cfg()
    if now - last_seen < int(c["tick_seconds"]):
        return None
    services = db.services_since(user_id, last_seen)
    if not services:
        return None
    tx = db.expenses_between(user_id, last_seen)
    expenses = sum(-v["amount"] for k, v in tx.items() if v["amount"] < 0)
    events = tx.get("event", {"n": 0})["n"]
    income = sum(s["total"] for s in services)
    return {
        "away_seconds": now - last_seen,
        "services": len(services),
        "clients": sum(s["clients"] for s in services),
        "vips": sum(s["vips"] for s in services),
        "income": income,
        "bar": sum(s["bar"] for s in services),
        "entry": sum(s["entry"] for s in services),
        "vip": sum(s["vip"] for s in services),
        "expenses": expenses,
        "events": events,
        "showcases": sum(1 for s in services if s["showcase_artist"]),
        "net": income - expenses,
    }


def build_state(user, with_recap=False):
    """État complet envoyé au client après chaque action."""
    now = time.time()
    with LOCK:
        db.begin()
        try:
            club, slot, reports, event = touch_club(user["id"], now)
            recap = None
            if club is not None and with_recap:
                recap = away_recap(user["id"], float(user.get("last_seen") or now), now)
            db.touch_user(user["id"], now)
            unread = db.unread_count(user["id"])
            pending_trades = db.pending_trades_count(user["id"])
            db.commit()
        except Exception:
            db.rollback()
            raise
    if club is None:
        return {"user": public_user(user), "club": None, "config": public_config(cfg()), "server_time": now}
    return {
        "user": public_user(user),
        "club": club,
        "showcase_screen": club_screen(user["id"], now)["showcase"],
        "slot": slot,
        "derived": derived_for(club),
        "config": public_config(cfg()),
        "server_time": now,
        "unread": unread,
        "pending_trades": pending_trades,
        "recap": recap,
    }


def public_user(user):
    prefs = None
    raw = user.get("audio_prefs")
    if raw:
        try:
            prefs = json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            prefs = None
    return {"id": user["id"], "username": user["username"], "display_name": user["display_name"],
            "avatar": user["avatar"], "is_admin": bool(user.get("is_admin")), "created_at": user.get("created_at"),
            "audio_prefs": prefs}


# ------------------------------------------------------------------
# Audio : préférences par joueur, manifeste, showcases actifs
# ------------------------------------------------------------------

PREF_KEYS = ("master", "fx", "showcase", "ambient", "notifications")


def sanitize_audio_prefs(prefs):
    defaults = cfg()["audio"]["default_prefs"]
    out = {}
    for k in PREF_KEYS:
        try:
            v = float(prefs.get(k, defaults.get(k, 0.7)))
        except (TypeError, ValueError):
            v = float(defaults.get(k, 0.7))
        out[k] = max(0.0, min(1.0, v))
    out["muted"] = bool(prefs.get("muted", False))
    return out


def set_audio_prefs(user, prefs):
    clean = sanitize_audio_prefs(prefs or {})
    with LOCK:
        db.begin()
        db.set_audio_prefs(user["id"], clean)
        db.commit()
    return clean


def audio_manifest():
    with LOCK:
        return audio_assets.build_manifest(db, cfg())


def sync_audio_assets(broadcast=True):
    with LOCK:
        db.begin()
        try:
            result = audio_assets.sync_assets(db)
            db.commit()
        except Exception:
            db.rollback()
            raise
    if broadcast:
        hub.broadcast("audio_manifest", {"reason": "rescan"})
    return result


def active_showcases():
    with LOCK:
        rows = db.list_active_showcases()
    return rows


def club_screen(club_id, now=None):
    now = time.time() if now is None else now
    with LOCK:
        row = db.active_showcase_for(club_id)
        # Les showcases commencés avant la migration reçoivent un programme unique.
        if row and row.get("screen_playlist") is None and row["ends_at"] > now:
            playlist = choose_playlist(cfg(), row["artist"], db.list_audio_assets())
            row["screen_playlist"] = json.dumps(playlist)
            db.conn.execute("UPDATE active_showcases SET screen_playlist=? WHERE id=?", (row["screen_playlist"], row["id"]))
        screen = screen_payload(row, now) if cfg().get("audio", {}).get("youtube_enabled", True) else None
    return {"server_time": now, "showcase": screen}


# ------------------------------------------------------------------
# Wrapper générique de mutation
# ------------------------------------------------------------------

class GameError(Exception):
    def __init__(self, code, message, payload=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.payload = payload or {}


def mutate(user_id, fn):
    """fn(club) -> résultat. Tout est atomique sous le verrou."""
    now = time.time()
    with LOCK:
        db.begin()
        try:
            club, slot, reports, event = touch_club(user_id, now)
            if club is None:
                raise GameError("NO_CLUB", "Aucun établissement trouvé.")
            result = fn(club)
            db.save_club(user_id, club)
            db.commit()
        except Exception:
            db.rollback()
            raise
    for r in reports:
        hub.publish(user_id, "service", r)
    if event:
        hub.publish(user_id, "event", event)
    return club, result


def mutate_pair(user_id, other_id, fn):
    now = time.time()
    with LOCK:
        db.begin()
        try:
            club, _, reports, event = touch_club(user_id, now)
            other, _, reports2, event2 = touch_club(other_id, now)
            if club is None:
                raise GameError("NO_CLUB", "Aucun établissement trouvé.")
            if other is None:
                raise GameError("NO_TARGET", "Ce joueur ne possède pas encore de boîte de nuit.")
            result = fn(club, other)
            db.save_club(user_id, club)
            db.save_club(other_id, other)
            db.commit()
        except Exception:
            db.rollback()
            raise
    for r in reports:
        hub.publish(user_id, "service", r)
    for r in reports2:
        hub.publish(other_id, "service", r)
    if event:
        hub.publish(user_id, "event", event)
    if event2:
        hub.publish(other_id, "event", event2)
    hub.publish(other_id, "refresh", {"reason": "pair"})
    return club, other, result


NO_MONEY_MSG = "Trésorerie insuffisante, patron."


# ------------------------------------------------------------------
# Actions
# ------------------------------------------------------------------

def action_entry_price(user, price):
    def fn(club):
        ok, code, payload = engine.set_entry_price(cfg(), club, price)
        if not ok:
            if code == "MAX":
                raise GameError(code, f"Le prix maximum actuel est de {money(payload['max'])}, patron.", payload)
            raise GameError(code, "Entrez un prix valide, patron.")
        return payload
    club, result = mutate(user["id"], fn)
    return result


def action_rename(user, name):
    def fn(club):
        ok, code, payload = engine.rename_club(cfg(), club, name)
        if not ok:
            raise GameError(code, "Nom invalide (2 caractères minimum).")
        return payload
    club, result = mutate(user["id"], fn)
    return result


def action_upgrade(user):
    def fn(club):
        ok, code, payload = engine.upgrade_level(cfg(), club)
        if not ok:
            if code == "MAX":
                raise GameError(code, "Votre établissement est déjà au niveau maximum, patron.")
            raise GameError(code, f"{NO_MONEY_MSG} Il faut {money(payload['cost'])}.", payload)
        _tx(user["id"], club, "upgrade", -payload["cost"], f"Amélioration → {payload['name']}")
        notify(user["id"], "level", "📈", "Niveau supérieur",
               f"Votre établissement devient {payload['name']}.", payload)
        feed("📈", f"{club['name']} passe au niveau {payload['level']} : {payload['name']}.", "upgrade", user["id"])
        return payload
    club, result = mutate(user["id"], fn)
    return result


def action_equipment(user, item_id):
    def fn(club):
        ok, code, payload = engine.buy_equipment(cfg(), club, item_id)
        if not ok:
            if code == "OWNED":
                raise GameError(code, "Cette amélioration est déjà installée.")
            if code == "UNKNOWN":
                raise GameError(code, "Équipement inconnu.")
            raise GameError(code, f"{NO_MONEY_MSG} Il faut {money(payload['cost'])}.", payload)
        item = payload["item"]
        _tx(user["id"], club, "equipment", -payload["cost"], f"Équipement : {item['name']}")
        notify(user["id"], "equipment", item["emoji"], f"{item['name']} installé", item["description"], payload)
        return payload
    club, result = mutate(user["id"], fn)
    return result


def action_hire_manager(user, manager_id):
    def fn(club):
        ok, code, payload = engine.hire_manager(cfg(), club, manager_id)
        if not ok:
            raise GameError(code, "Manager inconnu.")
        m = payload["manager"]
        notify(user["id"], "manager", "♣", "Contrat signé",
               f"{m['name']} devient votre manager. Salaire : {money(m['salary'])} / service.", payload)
        return payload
    club, result = mutate(user["id"], fn)
    return result


def action_fire_manager(user):
    def fn(club):
        ok, code, payload = engine.fire_manager(cfg(), club)
        if not ok:
            raise GameError(code, "Vous n'avez aucun manager à virer.")
        notify(user["id"], "manager", "🗑️", "Manager licencié", "Votre établissement n'a plus de manager.", payload)
        return payload
    club, result = mutate(user["id"], fn)
    return result


def action_showcase(user, artist):
    def fn(club):
        ok, code, payload = engine.book_showcase(cfg(), club, artist)
        if not ok:
            if code == "ALREADY":
                raise GameError(code, "Un showcase est déjà programmé pour le prochain service, patron.", payload)
            if code == "COOLDOWN":
                r = payload["remaining"]
                raise GameError(code, f"{artist} vient déjà de passer dans votre boîte. "
                                      f"Attendez encore {r} service{'s' if r > 1 else ''}.", payload)
            if code == "UNKNOWN":
                raise GameError(code, "Artiste inconnu.")
            raise GameError(code, f"{NO_MONEY_MSG} Il faut {money(payload['cost'])}.", payload)
        _tx(user["id"], club, "showcase", -payload["cost"], f"Showcase : {artist}")
        now = time.time()
        showcase_started(user["id"], club, artist, "player", now, engine.next_service_time(cfg(), club))
        notify(user["id"], "showcase", "🎤", "Showcase programmé",
               f"{artist} passera au prochain service (+{int(payload['bonus'] * 100)} % entrées).", payload)
        feed("🎤", f"{club['name']} programme un showcase de {artist}.", "showcase", user["id"])
        return payload
    club, result = mutate(user["id"], fn)
    return result


ACTIVITY_FUNCS = {
    "drink": engine.activity_drink,
    "promo": engine.activity_promo,
    "influencer": engine.activity_influencer,
    "coca_cherry": engine.activity_coca_cherry,
}

ACTIVITY_MESSAGES = {
    ("drink", "DRUNK"): ("🥃", "Le verre est de trop, patron.", "-8 clients au prochain service."),
    ("drink", "GOOD"): ("🥃", "Bonne ambiance ce soir.", "+4 clients au prochain service."),
    ("promo", "OK"): ("📢", "Campagne lancée", "+12 clients au prochain service."),
    ("influencer", "WIN"): ("📸", "La publication explose", "+30 clients au prochain service."),
    ("influencer", "MISS"): ("🥀", "La publication n'a presque rien donné.", "Les 5 000 € sont dépensés."),
    ("coca_cherry", "OK"): ("🍒", "Coca Cherry est arrivée.",
                            "Elle met l'ambiance avec un show twerk et attire du monde : +40 clients au prochain service."),
}


def action_activity(user, activity_id):
    func = ACTIVITY_FUNCS.get(activity_id)
    if not func:
        raise GameError("UNKNOWN", "Activité inconnue.")
    spec = cfg()["activities"][activity_id]

    def fn(club):
        ok, code, payload = func(cfg(), club, RNG)
        if not ok:
            raise GameError(code, f"Il faut {money(payload['cost'])} pour cette activité, patron.", payload)
        _tx(user["id"], club, "activity", -payload["cost"], f"Activité : {spec['name']}")
        icon, title, text = ACTIVITY_MESSAGES.get((activity_id, code), (spec["emoji"], spec["name"], ""))
        notify(user["id"], "activity", icon, title, text, dict(payload, code=code))
        return dict(payload, code=code, icon=icon, title=title, text=text)
    club, result = mutate(user["id"], fn)
    return result


def action_blackjack(user, op, bet=None):
    c = cfg()
    mode = c["web"].get("blackjack_mode", "interactive")

    def fn(club):
        if mode == "auto":
            if op != "start":
                raise GameError("MODE", "Le blackjack est en mode automatique (original).")
            ok, code, payload = engine.blackjack_auto(c, club, bet, RNG)
        elif op == "start":
            ok, code, payload = engine.blackjack_start(c, club, bet, RNG)
        elif op == "hit":
            ok, code, payload = engine.blackjack_hit(c, club, RNG)
        elif op == "stand":
            ok, code, payload = engine.blackjack_stand(c, club, RNG)
        else:
            raise GameError("INVALID", "Action inconnue.")
        if not ok:
            if code == "NO_MONEY":
                raise GameError(code, "Trésorerie insuffisante pour cette mise, patron.", payload)
            if code == "IN_PROGRESS":
                raise GameError(code, "Une main est déjà en cours.", payload)
            if code == "NO_GAME":
                raise GameError(code, "Aucune main en cours.")
            raise GameError(code, "Mise invalide.")
        if code in ("WIN", "LOSE", "PUSH"):
            if payload["delta"]:
                _tx(user["id"], club, "blackjack", payload["delta"],
                    f"Blackjack : {'victoire' if code == 'WIN' else 'défaite'}")
            label = {"WIN": "Victoire", "LOSE": "Défaite", "PUSH": "Égalité"}[code]
            notify(user["id"], "blackjack", "🃏", f"Blackjack — {label}",
                   f"Vous : {payload['player']} — Banque : {payload['dealer']}"
                   + (f" ({'+' if payload['delta'] > 0 else ''}{money(payload['delta'])})" if payload["delta"] else ""),
                   {"delta": payload["delta"]})
        return dict(payload, status=code)
    club, result = mutate(user["id"], fn)
    return result


def action_shop(user, op, category, item_id, expected_price=None):
    def fn(club):
        c = cfg()
        current = c["shop"].get(category, {}).get(item_id, {}).get("price") if category in ("cars", "watches") else None
        if expected_price is not None and expected_price != current:
            raise GameError("PRICE_CHANGED", "La cote a évolué. Vérifiez le nouveau montant avant de confirmer.")
        if op == "buy":
            ok, code, payload = engine.shop_buy(c, club, category, item_id)
            if not ok:
                if code == "UNKNOWN":
                    raise GameError(code, "Article inconnu.")
                raise GameError(code, NO_MONEY_MSG, payload)
            item = payload["item"]
            _tx(user["id"], club, "shop_buy", -payload["cost"], f"Achat : {item['name']}", payload)
            icon = "🚘" if category == "cars" else "⌚"
            notify(user["id"], "shop", icon, f"Nouvelle {'voiture' if category == 'cars' else 'montre'}",
                   f"{item['name']} acheté pour {money(payload['cost'])}.", payload)
            if int(item["price"]) >= 1_000_000:
                feed(icon, f"{club['name']} s'offre {item['name']}.", "flex", user["id"])
        else:
            ok, code, payload = engine.shop_sell(c, club, category, item_id)
            if not ok:
                raise GameError(code, "Vous ne possédez pas cet article.")
            item = payload["item"]
            _tx(user["id"], club, "shop_sell", payload["gain"], f"Revente : {item['name']}", payload)
            notify(user["id"], "shop", "💸", "Vente confirmée",
                   f"{item['name']} revendu pour {money(payload['gain'])}.", payload)
        return payload
    club, result = mutate(user["id"], fn)
    return result


def action_crypto(user, op, symbol, amount):
    def fn(club):
        quote = _market_state.get("crypto", {}).get(symbol)
        ok, code, payload = markets.trade(club, symbol, op, amount, quote)
        if not ok:
            messages = {
                "MARKET_STALE": "Cours indisponible ou trop ancien. Les échanges reprendront avec un cours frais.",
                "NO_MONEY": "Trésorerie insuffisante, frais inclus.",
                "NOT_OWNED": "Vous ne possédez pas assez de cette crypto.",
                "MINIMUM": "Le montant de cette opération doit atteindre 1 €.",
                "INVALID": "Quantité invalide : de 0,00000001 à 1 000 000, avec 8 décimales maximum.",
            }
            raise GameError(code, messages.get(code, "Opération impossible."), payload)
        amount_eur = -payload["cost"] if op == "buy" else payload["gain"]
        label = f"{'Achat' if op == 'buy' else 'Vente'} {payload['quantity']} {symbol}"
        _tx(user["id"], club, "crypto_" + op, amount_eur, label, payload)
        notify(user["id"], "crypto", "🪙", label, f"{money(abs(amount_eur))}, frais inclus.", payload)
        return payload
    _, result = mutate(user["id"], fn)
    return result


def action_bitcoin(user, op, quantity):
    # Existing clients use exactly the same fresh quote and validation.
    return action_crypto(user, op, "BTC", quantity)


def _target_user(target_id, user):
    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        raise GameError("INVALID", "Je n'ai pas reconnu ce joueur, patron.")
    if target_id == user["id"]:
        raise GameError("SELF", "Vous ne pouvez pas faire ça avec vous-même, patron.")
    target = db.get_user(target_id)
    if not target:
        raise GameError("INVALID", "Je n'ai pas reconnu ce joueur, patron.")
    return target


def action_transfer(user, target_id, amount):
    target = _target_user(target_id, user)

    def fn(club, other):
        ok, code, payload = engine.transfer_money(cfg(), club, other, amount)
        if not ok:
            if code == "NO_MONEY":
                raise GameError(code, "Trésorerie insuffisante pour ce transfert, patron.")
            raise GameError(code, "Le montant doit être supérieur à 0 €.")
        a = payload["amount"]
        _tx(user["id"], club, "transfer_out", -a, f"Transfert → {other['name']}", {"to": target["id"]})
        _tx(target["id"], other, "transfer_in", a, f"Transfert ← {club['name']}", {"from": user["id"]})
        notify(user["id"], "transfer", "💸", "Transfert effectué",
               f"{money(a)} envoyés à {other['name']} ({target['display_name']}).", payload)
        notify(target["id"], "transfer", "💸", "Transfert reçu",
               f"{club['name']} ({user['display_name']}) vous a envoyé {money(a)}.", payload)
        return dict(payload, target=target["display_name"], target_club=other["name"])
    club, other, result = mutate_pair(user["id"], target["id"], fn)
    return result


def action_bottle(user, target_id, pack_id):
    target = _target_user(target_id, user)

    def fn(club, other):
        ok, code, payload = engine.send_bottle_pack(cfg(), club, other, pack_id)
        if not ok:
            if code == "UNKNOWN":
                raise GameError(code, "Pack inconnu.")
            raise GameError(code, f"Il faut {money(payload['cost'])} pour envoyer ce pack.", payload)
        pack = payload["pack"]
        _tx(user["id"], club, "bottle_out", -payload["cost"], f"{pack['name']} → {other['name']}", {"to": target["id"]})
        _tx(target["id"], other, "bottle_in", payload["bonus"], f"{pack['name']} ← {club['name']}", {"from": user["id"]})
        notify(user["id"], "bottle", pack["emoji"], "Pack envoyé",
               f"Vous venez d'envoyer un {pack['name']} à {other['name']}.", payload)
        notify(target["id"], "bottle", pack["emoji"], "Pack reçu",
               f"{club['name']} vous envoie un {pack['name']} : +{money(payload['bonus'])} et +{payload['clients']} clients au prochain service.",
               payload)
        feed(pack["emoji"], f"{club['name']} envoie un {pack['name']} à {other['name']}.", "bottle", user["id"])
        return dict(payload, target=target["display_name"], target_club=other["name"])
    club, other, result = mutate_pair(user["id"], target["id"], fn)
    return result


def action_robbery(user, target_id):
    target = _target_user(target_id, user)

    def fn(club, other):
        ok, code, payload = engine.perform_robbery(cfg(), club, other, RNG)
        if not ok:
            if code == "COOLDOWN":
                r = payload["remaining"]
                raise GameError(code, f"Vos hommes doivent se faire oublier, patron. Attendez encore {r} service{'s' if r > 1 else ''}.", payload)
            raise GameError(code, f"La boîte de {other['name']} n'a rien à voler pour le moment.")
        if code == "SUCCESS":
            _tx(user["id"], club, "robbery", payload["amount"], f"Braquage réussi : {other['name']}", payload)
            _tx(target["id"], other, "robbery", -payload["amount"], f"Braquage subi : {club['name']}", payload)
            notify(user["id"], "robbery", "💰", "Braquage réussi",
                   f"Butin : {money(payload['amount'])} (25 % de la trésorerie de {other['name']}). "
                   f"+{payload['attacker_clients']} clients au prochain service. Chance : {payload['chance']} %.", payload)
            notify(target["id"], "robbery", "🚨", "Votre boîte a été braquée",
                   f"Les hommes de {club['name']} ont volé {money(payload['amount'])}. "
                   f"{payload['victim_clients']} clients au prochain service.", payload)
            feed("💰", f"{club['name']} a braqué {other['name']} : {money(payload['amount'])} envolés.", "robbery", user["id"])
        else:
            _tx(user["id"], club, "robbery", -payload["amount"], f"Braquage raté : {other['name']}", payload)
            notify(user["id"], "robbery", "🚔", "Braquage raté",
                   f"Pertes : {money(payload['amount'])} (25 % de votre trésorerie). "
                   f"{payload['attacker_clients']} clients au prochain service. Chance : {payload['chance']} %.", payload)
            notify(target["id"], "robbery", "🛡️", "Braquage repoussé",
                   f"{club['name']} a tenté de braquer votre boîte et a échoué. "
                   f"+{payload['victim_clients']} clients au prochain service.", payload)
            feed("🚔", f"{club['name']} a raté son braquage contre {other['name']}.", "robbery", user["id"])
        ts = time.time()
        rid = db.add_robbery(user["id"], target["id"], code, payload["amount"], payload["chance"], ts)
        return dict(payload, result=code, target=target["display_name"], target_club=other["name"],
                    robbery_id=rid, ts=ts)
    club, other, result = mutate_pair(user["id"], target["id"], fn)
    # ROBBERY_CREATED : événement mondial, diffusé à TOUS les joueurs connectés (braqueur compris).
    hub.broadcast("robbery_created", {
        "robbery_id": result["robbery_id"],
        "attacker_id": user["id"], "attacker_name": user["display_name"], "attacker_club": club["name"],
        "victim_id": target["id"], "victim_name": target["display_name"], "victim_club": other["name"],
        "result": result["result"], "amount": result["amount"], "chance": result["chance"],
        "timestamp": result["ts"],
    })
    return result


# ---------------- Trades (proposition → acceptation) ----------------

def action_trade_propose(user, target_id, trade_type, value):
    target = _target_user(target_id, user)
    if trade_type not in ("money", "bitcoin", "cars", "watches"):
        raise GameError("INVALID_TYPE", "Type de trade invalide.")
    try:
        value = int(value) if trade_type == "money" else str(markets.quantity(value)) if trade_type == "bitcoin" else str(value)
    except (TypeError, ValueError):
        raise GameError("INVALID", "Valeur invalide.")

    def fn(club, other):
        ok, code = engine.trade_check(cfg(), club, trade_type, value)
        if not ok:
            msgs = {"NO_MONEY": "Trésorerie insuffisante pour cette proposition.",
                    "NO_BTC": "Vous ne possédez pas assez de Bitcoin.",
                    "NOT_OWNED": "Vous ne possédez pas cet objet."}
            raise GameError(code, msgs.get(code, "Proposition invalide."))
        trade_id = db.create_trade(user["id"], target["id"], trade_type, value)
        detail = _trade_detail(trade_type, value)
        notify(target["id"], "trade", "♣", "Proposition de trade",
               f"{club['name']} ({user['display_name']}) vous propose {detail}.", {"trade_id": trade_id})
        return {"trade_id": trade_id, "detail": detail}
    club, other, result = mutate_pair(user["id"], target["id"], fn)
    hub.publish(target["id"], "trade", result)
    return result


def _trade_detail(trade_type, value):
    c = cfg()
    if trade_type == "money":
        return money(int(value))
    if trade_type == "bitcoin":
        return f"{value} BTC"
    return c["shop"][trade_type].get(str(value), {"name": str(value)})["name"]


def action_trade_respond(user, trade_id, accept):
    trade = db.get_trade(trade_id)
    if not trade or trade["status"] != "pending":
        raise GameError("INVALID", "Ce trade n'est plus disponible.")
    if trade["target_id"] != user["id"]:
        raise GameError("FORBIDDEN", "Seul le destinataire peut répondre à ce trade.")
    detail = _trade_detail(trade["trade_type"], trade["value"])
    if not accept:
        with LOCK:
            db.begin()
            db.set_trade_status(trade_id, "refused")
            db.commit()
        notify(trade["sender_id"], "trade", "❌", "Trade refusé", f"Votre proposition ({detail}) a été refusée.")
        hub.publish(trade["sender_id"], "refresh", {"reason": "trade"})
        return {"status": "refused"}

    def fn(target_club, sender_club):
        ok, code, payload = engine.trade_apply(cfg(), sender_club, target_club, trade["trade_type"], trade["value"])
        if not ok:
            db.set_trade_status(trade_id, "failed")
            msgs = {"NO_MONEY": "Le joueur n'a plus assez d'argent pour ce trade.",
                    "NO_BTC": "Le joueur n'a plus assez de Bitcoin.",
                    "NOT_OWNED": "Le joueur ne possède plus cet objet."}
            raise GameError(code, msgs.get(code, "Trade impossible."))
        db.set_trade_status(trade_id, "accepted")
        kind = trade["trade_type"]
        if kind == "money":
            _tx(trade["sender_id"], sender_club, "trade_out", -payload["amount"], f"Trade → {target_club['name']}")
            _tx(user["id"], target_club, "trade_in", payload["amount"], f"Trade ← {sender_club['name']}")
        notify(trade["sender_id"], "trade", "✅", "Trade accepté",
               f"{detail} a été transféré à {target_club['name']}.")
        notify(user["id"], "trade", "✅", "Trade accepté", f"Vous avez reçu {detail} de {sender_club['name']}.")
        return dict(payload, status="accepted")
    club, other, result = mutate_pair(user["id"], trade["sender_id"], fn)
    return result


def action_trade_cancel(user, trade_id):
    trade = db.get_trade(trade_id)
    if not trade or trade["status"] != "pending" or trade["sender_id"] != user["id"]:
        raise GameError("INVALID", "Ce trade ne peut pas être annulé.")
    with LOCK:
        db.begin()
        db.set_trade_status(trade_id, "cancelled")
        db.commit()
    hub.publish(trade["target_id"], "refresh", {"reason": "trade"})
    return {"status": "cancelled"}


def list_trades(user):
    rows = db.list_trades_for(user["id"])
    for r in rows:
        r["detail"] = _trade_detail(r["trade_type"], r["value"])
    return rows


# ------------------------------------------------------------------
# Lecture : ville, visite, classement, finances, profil
# ------------------------------------------------------------------

def city_view():
    now = time.time()
    with LOCK:
        entries = db.all_clubs()
    clubs = [public_club_view(e, now) for e in entries]
    return {"clubs": clubs, "server_time": now, "feed": db.list_feed(40)}


def club_view(user_id):
    with LOCK:
        entries = [e for e in db.all_clubs() if e["user_id"] == int(user_id)]
    if not entries:
        raise GameError("NOT_FOUND", "Club introuvable.")
    return public_club_view(entries[0])


def profile_view(user_id):
    view = club_view(user_id)
    user = db.get_user(int(user_id))
    view["username"] = user["username"] if user else None
    view["recent_services"] = db.recent_services(int(user_id), 10)
    return view


LEADERBOARDS = {
    "cash": "Trésorerie",
    "net_worth": "Richesse totale",
    "income": "Revenus (24 h)",
    "clients": "Clients reçus",
    "vip": "VIP reçus",
    "showcases": "Showcases",
    "level": "Progression",
}


def leaderboard(by="cash"):
    if by not in LEADERBOARDS:
        by = "cash"
    now = time.time()
    with LOCK:
        entries = db.all_clubs()
        income = db.leaderboard_income(now - 86400) if by == "income" else {}
    rows = [public_club_view(e, now) for e in entries]
    for r in rows:
        r["income_24h"] = income.get(r["user_id"], {}).get("total", 0)
    keyfuncs = {
        "cash": lambda r: (r["cash"], r["level"]),
        "net_worth": lambda r: (r["net_worth"], r["level"]),
        "income": lambda r: (r["income_24h"], r["cash"]),
        "clients": lambda r: (r["total_clients"], r["cash"]),
        "vip": lambda r: (r["total_vip_clients"], r["cash"]),
        "showcases": lambda r: (r["showcases_done"], r["cash"]),
        "level": lambda r: (r["level"], r["cash"]),
    }
    rows.sort(key=keyfuncs[by], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return {"by": by, "label": LEADERBOARDS[by], "boards": LEADERBOARDS, "rows": rows}


def finances_view(user):
    uid = user["id"]
    now = time.time()
    day = _day_start()
    with LOCK:
        club, slot = db.get_club(uid)
        if club is None:
            raise GameError("NO_CLUB", "Aucun établissement trouvé.")
        today = db.service_totals(uid, day)
        today_tx = db.expenses_since(uid, day)
        services = db.recent_services(uid, 60)
        transactions = db.recent_transactions(uid, 120)
        all_time = db.expenses_since(uid, 0)
    services.reverse()
    return {
        "totals": {
            "bar": int(club.get("total_bar", 0)), "entry": int(club.get("total_entry", 0)),
            "vip": int(club.get("total_vip", 0)), "clients": int(club.get("total_clients", 0)),
            "vips": int(club.get("total_vip_clients", 0)), "showcases": int(club.get("showcases_done", 0)),
            "expenses": all_time["expenses"], "other_income": all_time["other_income"],
        },
        "today": dict(today, expenses=today_tx["expenses"], other_income=today_tx["other_income"],
                      net=today["total"] + today_tx["other_income"] - today_tx["expenses"]),
        "last": {"clients": int(club.get("last_clients", 0)), "vips": int(club.get("last_vips", 0)),
                 "income": int(club.get("last_income", 0))},
        "services": services,
        "transactions": transactions,
        "server_time": now,
    }


# ------------------------------------------------------------------
# Comptes
# ------------------------------------------------------------------

AVATARS = ["♣", "♠", "♛", "♚", "★", "◆", "☾", "⚡", "🔥", "🖤", "💎", "👑"]


def register(username, display_name, password_hash, club_name, *, is_admin=False):
    with LOCK:
        db.begin()
        try:
            if db.get_user_by_username(username):
                raise GameError("TAKEN", "Ce nom d'utilisateur est déjà pris.")
            avatar = RNG.choice(AVATARS)
            uid = db.create_user(username, display_name, password_hash, avatar, is_admin)
            club = engine.new_club(cfg(), club_name)
            db.create_club(uid, club)
            notify(uid, "welcome", "🖤", "Bonsoir, patron.",
                   f"Olivia, secrétaire de nuit à votre service. {club['name']} est ouvert.", push=False)
            db.commit()
        except Exception:
            db.rollback()
            raise
    feed("🏙️", f"Une nouvelle boîte ouvre en ville : {club['name']} ({display_name}).", "open", uid)
    return db.get_user(uid)


def create_club_for(user, club_name):
    with LOCK:
        db.begin()
        try:
            existing, _ = db.get_club(user["id"])
            if existing:
                raise GameError("EXISTS", "Vous possédez déjà un établissement, patron.")
            club = engine.new_club(cfg(), club_name)
            db.create_club(user["id"], club)
            db.commit()
        except Exception:
            db.rollback()
            raise
    feed("🏙️", f"Une nouvelle boîte ouvre en ville : {club['name']} ({user['display_name']}).", "open", user["id"])
    return club


def delete_club(user):
    with LOCK:
        db.begin()
        try:
            club, _ = db.get_club(user["id"])
            if club is None:
                raise GameError("NO_CLUB", "Aucun établissement trouvé.")
            showcase_ended(user["id"], club, time.time(), reason="club_deleted")
            db.delete_club(user["id"])
            db.commit()
        except Exception:
            db.rollback()
            raise
    feed("🗑️", f"{club['name']} a fermé définitivement ses portes.", "close", user["id"])
    return {"deleted": club["name"]}


# ------------------------------------------------------------------
# Admin
# ------------------------------------------------------------------

def admin_delete_club(admin, user_id, confirm_name):
    """Remove only the selected club, keeping the player's login usable."""
    if not admin.get("is_admin"):
        raise GameError("FORBIDDEN", "Réservé à l'administration.")
    user_id = int(user_id)
    if user_id == admin["id"]:
        raise GameError("SELF", "Vous ne pouvez pas supprimer votre propre boîte depuis ce panneau.")
    with LOCK:
        db.begin()
        try:
            club, _ = db.get_club(user_id)
            if club is None:
                raise GameError("NO_CLUB", "Cette boîte n'existe plus.")
            if confirm_name != club["name"]:
                raise GameError("CONFIRM", "Le nom de confirmation ne correspond pas à la boîte.")
            ended_at = time.time()
            ended = db.end_showcase(user_id, ended_at)
            db.delete_club(user_id)
            # Old services must not pollute the totals of a future new club.
            for table in ("service_log", "transactions"):
                db.conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
            db.conn.execute("UPDATE trades SET status='cancelled', resolved_at=? "
                            "WHERE (sender_id=? OR target_id=?) AND status='pending'",
                            (time.time(), user_id, user_id))
            notify(user_id, "admin", "♣", "Établissement supprimé",
                   f"L'administration a supprimé {club['name']}. Vous pouvez créer une nouvelle boîte.", push=False)
            db.commit()
        except Exception:
            db.rollback()
            raise
    for showcase in ended:
        hub.broadcast("showcase_ended", {"club_id": user_id, "showcase_id": showcase["id"],
                      "club_name": club["name"], "artist": showcase["artist"],
                      "ended_at": ended_at, "reason": "club_deleted"})
    hub.publish(user_id, "refresh", {"reason": "club_deleted"})
    hub.broadcast("city", {"changed": [user_id]})
    feed("♣", f"L'administration a fermé {club['name']}.", "close", user_id)
    return {"deleted": club["name"], "user_id": user_id}

def admin_grant(admin, user_id, amount, label="Ajustement administrateur"):
    target = db.get_user(int(user_id))
    if not target:
        raise GameError("INVALID", "Joueur inconnu.")

    def fn(club):
        club["cash"] = max(0, int(club.get("cash", 0)) + int(amount))
        _tx(target["id"], club, "admin", int(amount), label)
        notify(target["id"], "admin", "♣", label, f"{'+' if int(amount) >= 0 else ''}{money(int(amount))}")
        return {"cash": club["cash"]}
    club, result = mutate(target["id"], fn)
    hub.publish(target["id"], "refresh", {"reason": "admin"})
    return result


def admin_set_config(overrides):
    with LOCK:
        db.begin()
        db.set_setting("config_overrides", overrides or {})
        db.commit()
    reload_config()
    hub.broadcast("refresh", {"reason": "config"})
    return cfg()


def admin_import_bot(data, password_hash_factory):
    """
    Importe nightclub_data.json du bot : { "<discord_id>": {club...}, ... }
    Crée un compte "discord_<id>" (mot de passe à définir par l'admin) + le club tel quel.
    """
    imported, skipped = [], []
    c = cfg()
    with LOCK:
        db.begin()
        try:
            for discord_id, club in data.items():
                if not isinstance(club, dict):
                    skipped.append(discord_id)
                    continue
                username = f"discord_{discord_id}"
                if db.get_user_by_username(username):
                    skipped.append(discord_id)
                    continue
                name = str(club.get("name", "Sans nom"))
                uid = db.create_user(username, name[:24], password_hash_factory(secrets.token_urlsafe(12)),
                                     RNG.choice(AVATARS), 0, str(discord_id))
                engine.ensure_club_fields(c, club)
                db.create_club(uid, club)
                imported.append({"discord_id": discord_id, "user_id": uid, "username": username, "club": name})
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {"imported": imported, "skipped": skipped}
