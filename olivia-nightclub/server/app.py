"""
API HTTP (FastAPI) + temps réel (SSE) + fichiers statiques du jeu.

Toutes les opérations financières passent par services.py et sont validées
côté serveur. Le frontend ne fait qu'afficher l'état renvoyé.
"""

import asyncio
import contextlib
import json
import os
import queue
import threading
import time
import traceback
from typing import Optional

from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import auth, services, markets
from .local_admin import is_host_request
from .config import DEFAULT_CONFIG, public_config
from .services import GameError, db, hub

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

WORLD_INTERVAL = float(os.environ.get("OLIVIA_WORLD_INTERVAL", "5"))
_stop = threading.Event()


# ------------------------------------------------------------------
# Boucle monde (fait avancer tous les clubs, même hors-ligne)
# ------------------------------------------------------------------

def world_loop():
    while not _stop.is_set():
        try:
            services.process_world()
        except Exception:
            traceback.print_exc()
        _stop.wait(WORLD_INTERVAL)


def market_loop():
    while not _stop.is_set():
        started = time.monotonic()
        try:
            services.update_markets()
        except Exception:
            traceback.print_exc()
        _stop.wait(max(1, markets.POLL_SECONDS - (time.monotonic() - started)))


@contextlib.asynccontextmanager
async def lifespan(_app):
    _stop.clear()
    services.cfg()
    services.load_markets()
    try:
        print("Audio :", services.sync_audio_assets(broadcast=False))
    except Exception:
        traceback.print_exc()
    threading.Thread(target=world_loop, name="olivia-world", daemon=True).start()
    threading.Thread(target=market_loop, name="olivia-markets", daemon=True).start()
    yield
    _stop.set()


app = FastAPI(title="OLIVIA Nightclubs", docs_url=None, redoc_url=None, lifespan=lifespan)


# ------------------------------------------------------------------
# Erreurs
# ------------------------------------------------------------------

@app.exception_handler(GameError)
async def game_error_handler(request: Request, exc: GameError):
    return JSONResponse(status_code=400, content={"error": exc.code, "message": exc.message, "payload": exc.payload})


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

def current_user(request: Request):
    token = request.cookies.get(auth.SESSION_COOKIE)
    user = auth.user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Non connecté.")
    return user


def current_admin(user=Depends(current_user)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Réservé à l'administration.")
    return user


def set_cookie(response: Response, token: str):
    # En production HTTPS, secure the session cookie. Local HTTP keeps it usable
    # during development. Set OLIVIA_SECURE_COOKIES=1 explicitly if desired.
    secure = os.environ.get("OLIVIA_SECURE_COOKIES", "").lower() in {"1", "true", "yes", "on"}
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=auth.SESSION_TTL,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


@app.post("/api/auth/register")
def api_register(request: Request, response: Response, body: dict = Body(...)):
    username = str(body.get("username", "")).strip().lower()
    display_name = str(body.get("display_name", "")).strip() or username
    password = str(body.get("password", ""))
    club_name = str(body.get("club_name", "")).strip()
    if not auth.valid_username(username):
        raise GameError("INVALID", "Nom d'utilisateur : 3 à 24 caractères (lettres, chiffres, _ . -).")
    if len(password) < 6:
        raise GameError("INVALID", "Mot de passe : 6 caractères minimum.")
    if not (2 <= len(club_name) <= 40):
        raise GameError("INVALID", "Nom de la boîte : 2 à 40 caractères.")
    local_admin = bool(body.get("local_admin"))
    if local_admin and not is_host_request(request):
        raise HTTPException(status_code=403, detail="Ouvrez le jeu sur cet ordinateur via localhost pour activer l'administration.")
    user = services.register(username, display_name[:24], auth.hash_password(password), club_name,
                             is_admin=local_admin)
    token = auth.new_session(db, user["id"])
    set_cookie(response, token)
    return services.build_state(user)


@app.post("/api/auth/login")
def api_login(response: Response, body: dict = Body(...)):
    username = str(body.get("username", "")).strip().lower()
    password = str(body.get("password", ""))
    user = db.get_user_by_username(username)
    if not user or not auth.verify_password(password, user["password_hash"]):
        raise GameError("BAD_LOGIN", "Identifiants incorrects, patron.")
    token = auth.new_session(db, user["id"])
    set_cookie(response, token)
    return services.build_state(user, with_recap=True)


@app.post("/api/auth/logout")
def api_logout(request: Request, response: Response):
    token = request.cookies.get(auth.SESSION_COOKIE)
    if token:
        with services.LOCK:
            db.begin()
            db.delete_session(token)
            db.commit()
    response.delete_cookie(auth.SESSION_COOKIE)
    return {"ok": True}


# ------------------------------------------------------------------
# État & club
# ------------------------------------------------------------------

@app.get("/api/state")
def api_state(request: Request, user=Depends(current_user)):
    with_recap = request.query_params.get("recap") == "1"
    return services.build_state(user, with_recap=with_recap)


@app.get("/api/config")
def api_config():
    return public_config(services.cfg())


@app.post("/api/club/create")
def api_create_club(body: dict = Body(...), user=Depends(current_user)):
    club_name = str(body.get("club_name", "")).strip()
    if not (2 <= len(club_name) <= 40):
        raise GameError("INVALID", "Nom de la boîte : 2 à 40 caractères.")
    services.create_club_for(user, club_name)
    return services.build_state(user)


def _with_state(user, result):
    state = services.build_state(user)
    state["result"] = result
    return state


@app.post("/api/club/entry-price")
def api_entry_price(body: dict = Body(...), user=Depends(current_user)):
    return _with_state(user, services.action_entry_price(user, body.get("price")))


@app.post("/api/club/rename")
def api_rename(body: dict = Body(...), user=Depends(current_user)):
    return _with_state(user, services.action_rename(user, body.get("name")))


@app.delete("/api/club")
def api_delete_club(user=Depends(current_user)):
    result = services.delete_club(user)
    return _with_state(user, result)


@app.post("/api/club/upgrade")
def api_upgrade(user=Depends(current_user)):
    return _with_state(user, services.action_upgrade(user))


@app.post("/api/club/equipment")
def api_equipment(body: dict = Body(...), user=Depends(current_user)):
    return _with_state(user, services.action_equipment(user, str(body.get("item_id", "")), body.get("expected_price")))


@app.post("/api/club/manager")
def api_hire_manager(body: dict = Body(...), user=Depends(current_user)):
    return _with_state(user, services.action_hire_manager(user, str(body.get("manager_id", ""))))


@app.delete("/api/club/manager")
def api_fire_manager(user=Depends(current_user)):
    return _with_state(user, services.action_fire_manager(user))


@app.post("/api/club/showcase")
def api_showcase(body: dict = Body(...), user=Depends(current_user)):
    return _with_state(user, services.action_showcase(user, str(body.get("artist", ""))))


@app.get("/api/club/estimate")
def api_estimate(price: Optional[float] = None, user=Depends(current_user)):
    club, _ = db.get_club(user["id"])
    if club is None:
        raise GameError("NO_CLUB", "Aucun établissement trouvé.")
    c = services.cfg()
    current = services.engine.estimate_service(c, club)
    proposed = services.engine.estimate_service(c, club, entry_price=price) if price is not None else current
    return {"current": current, "proposed": proposed}


# ------------------------------------------------------------------
# Activités / blackjack
# ------------------------------------------------------------------

@app.post("/api/activities/{activity_id}")
def api_activity(activity_id: str, user=Depends(current_user)):
    return _with_state(user, services.action_activity(user, activity_id))


@app.post("/api/blackjack/start")
def api_bj_start(body: dict = Body(...), user=Depends(current_user)):
    return _with_state(user, services.action_blackjack(user, "start", body.get("bet")))


@app.post("/api/blackjack/hit")
def api_bj_hit(user=Depends(current_user)):
    return _with_state(user, services.action_blackjack(user, "hit"))


@app.post("/api/blackjack/stand")
def api_bj_stand(user=Depends(current_user)):
    return _with_state(user, services.action_blackjack(user, "stand"))


# ------------------------------------------------------------------
# Boutique
# ------------------------------------------------------------------

@app.get("/api/markets")
def api_markets(user=Depends(current_user)):
    return services.market_view()


@app.post("/api/crypto/{op}")
def api_crypto(op: str, body: dict = Body(...), user=Depends(current_user)):
    if op not in ("buy", "sell"):
        raise GameError("INVALID", "Opération inconnue.")
    return _with_state(user, services.action_crypto(user, op, str(body.get("symbol", "")).upper(), body.get("quantity")))

@app.post("/api/shop/{op}")
def api_shop(op: str, body: dict = Body(...), user=Depends(current_user)):
    if op not in ("buy", "sell"):
        raise GameError("INVALID", "Opération inconnue.")
    return _with_state(user, services.action_shop(user, op, str(body.get("category", "")), str(body.get("item_id", "")), body.get("expected_price")))


@app.post("/api/bitcoin/{op}")
def api_bitcoin(op: str, body: dict = Body(...), user=Depends(current_user)):
    if op not in ("buy", "sell"):
        raise GameError("INVALID", "Opération inconnue.")
    return _with_state(user, services.action_bitcoin(user, op, body.get("quantity")))


# ------------------------------------------------------------------
# Banque / marché / braquage
# ------------------------------------------------------------------

@app.post("/api/bank/transfer")
def api_transfer(body: dict = Body(...), user=Depends(current_user)):
    return _with_state(user, services.action_transfer(user, body.get("target_id"), body.get("amount")))


@app.post("/api/bank/bottle")
def api_bottle(body: dict = Body(...), user=Depends(current_user)):
    return _with_state(user, services.action_bottle(user, body.get("target_id"), str(body.get("pack_id", ""))))


@app.post("/api/robbery")
def api_robbery(body: dict = Body(...), user=Depends(current_user)):
    return _with_state(user, services.action_robbery(user, body.get("target_id")))


@app.get("/api/trades")
def api_trades(user=Depends(current_user)):
    return {"trades": services.list_trades(user)}


@app.post("/api/trades")
def api_trade_propose(body: dict = Body(...), user=Depends(current_user)):
    result = services.action_trade_propose(user, body.get("target_id"), str(body.get("type", "")), body.get("value"))
    return _with_state(user, result)


@app.post("/api/trades/{trade_id}/{op}")
def api_trade_respond(trade_id: int, op: str, user=Depends(current_user)):
    if op == "accept":
        result = services.action_trade_respond(user, trade_id, True)
    elif op == "refuse":
        result = services.action_trade_respond(user, trade_id, False)
    elif op == "cancel":
        result = services.action_trade_cancel(user, trade_id)
    else:
        raise GameError("INVALID", "Opération inconnue.")
    return _with_state(user, result)


# ------------------------------------------------------------------
# Lecture
# ------------------------------------------------------------------

@app.get("/api/city")
def api_city(user=Depends(current_user)):
    return services.city_view()


@app.get("/api/clubs/{user_id}")
def api_club(user_id: int, user=Depends(current_user)):
    return services.club_view(user_id)


@app.get("/api/profile/{user_id}")
def api_profile(user_id: int, user=Depends(current_user)):
    return services.profile_view(user_id)


@app.get("/api/leaderboard")
def api_leaderboard(by: str = "cash", user=Depends(current_user)):
    return services.leaderboard(by)


@app.get("/api/finances")
def api_finances(user=Depends(current_user)):
    return services.finances_view(user)


@app.get("/api/feed")
def api_feed(user=Depends(current_user)):
    return {"feed": db.list_feed(40)}


@app.get("/api/notifications")
def api_notifications(user=Depends(current_user)):
    return {"notifications": db.list_notifications(user["id"], 100), "unread": db.unread_count(user["id"])}


@app.post("/api/notifications/read")
def api_notifications_read(body: dict = Body(default={}), user=Depends(current_user)):
    with services.LOCK:
        db.begin()
        db.mark_read(user["id"], body.get("ids"))
        db.commit()
    return {"unread": db.unread_count(user["id"])}


@app.get("/api/players")
def api_players(user=Depends(current_user)):
    with services.LOCK:
        entries = db.all_clubs()
    return {"players": [
        {"user_id": e["user_id"], "display_name": e["display_name"], "club": e["state"].get("name"),
         "avatar": e["avatar"], "level": int(e["state"].get("level", 0))}
        for e in entries if e["user_id"] != user["id"]
    ]}


# ------------------------------------------------------------------
# Audio
# ------------------------------------------------------------------

@app.get("/api/audio/manifest")
def api_audio_manifest(user=Depends(current_user)):
    return services.audio_manifest()


@app.get("/api/me/audio")
def api_audio_prefs_get(user=Depends(current_user)):
    return {"prefs": services.public_user(user)["audio_prefs"],
            "defaults": services.cfg()["audio"]["default_prefs"]}


@app.put("/api/me/audio")
def api_audio_prefs_put(body: dict = Body(...), user=Depends(current_user)):
    return {"prefs": services.set_audio_prefs(user, body.get("prefs") or body)}


@app.get("/api/showcases/active")
def api_active_showcases(user=Depends(current_user)):
    return {"showcases": services.active_showcases()}


@app.get("/api/clubs/{club_id}/showcase")
def api_club_screen(club_id: int, user=Depends(current_user)):
    return services.club_screen(club_id)


@app.get("/api/robberies")
def api_robberies(user=Depends(current_user)):
    return {"robberies": db.recent_robberies(20)}


@app.get("/api/admin/audio")
def api_admin_audio(admin=Depends(current_admin)):
    with services.LOCK:
        return {"assets": db.list_audio_assets()}


@app.post("/api/admin/audio/rescan")
def api_admin_audio_rescan(admin=Depends(current_admin)):
    return services.sync_audio_assets()


@app.put("/api/admin/audio/{asset_id}")
def api_admin_audio_put(asset_id: int, body: dict = Body(...), admin=Depends(current_admin)):
    with services.LOCK:
        db.begin()
        db.update_audio_asset(asset_id, body.get("enabled"), body.get("weight"))
        db.commit()
    hub.broadcast("audio_manifest", {"reason": "update"})
    return {"ok": True}


@app.post("/api/admin/audio/youtube")
def api_admin_audio_youtube(body: dict = Body(...), admin=Depends(current_admin)):
    """Ajoute des clips YouTube (URLs ou IDs) au showcase d'un artiste."""
    artist = str(body.get("artist", "")).strip()
    if artist not in services.cfg()["artists"]:
        raise GameError("INVALID", "Artiste inconnu.")
    # Les titres sont récupérés via oEmbed (réseau) HORS verrou, puis insérés sous verrou.
    ids = services.audio_assets.parse_youtube_ids(str(body.get("urls", "")))
    if not ids:
        raise GameError("INVALID", "Aucun lien ou identifiant YouTube reconnu.")
    titles = {}
    if bool(body.get("fetch_titles", True)):
        for vid in ids:
            titles[vid] = services.audio_assets.youtube_title(vid)
    with services.LOCK:
        db.begin()
        try:
            result = services.audio_assets.add_youtube_assets(db, artist, ids, titles, body.get("note"))
            db.commit()
        except Exception:
            db.rollback()
            raise
    hub.broadcast("audio_manifest", {"reason": "youtube"})
    return result


@app.delete("/api/admin/audio/{asset_id}")
def api_admin_audio_delete(asset_id: int, admin=Depends(current_admin)):
    with services.LOCK:
        db.begin()
        db.delete_audio_asset(asset_id)
        db.commit()
    hub.broadcast("audio_manifest", {"reason": "delete"})
    return {"ok": True}


# ------------------------------------------------------------------
# Temps réel (SSE)
# ------------------------------------------------------------------

@app.get("/api/events")
async def api_events(request: Request, user=Depends(current_user)):
    q = hub.subscribe(user["id"])

    async def stream():
        try:
            yield "event: hello\ndata: {}\n\n"
            last_beat = time.time()
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event, data = q.get_nowait()
                    yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                    continue
                except queue.Empty:
                    pass
                if time.time() - last_beat > 15:
                    yield "event: ping\ndata: {}\n\n"
                    last_beat = time.time()
                    with services.LOCK:
                        db.touch_user(user["id"])
                await asyncio.sleep(0.4)
        finally:
            hub.unsubscribe(user["id"], q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ------------------------------------------------------------------
# Administration
# ------------------------------------------------------------------

@app.get("/api/auth/local-admin")
def api_local_admin_available(request: Request):
    return {"available": is_host_request(request)}


@app.post("/api/auth/local-admin")
def api_claim_local_admin(request: Request, body: dict = Body(...), user=Depends(current_user)):
    if not is_host_request(request):
        raise HTTPException(status_code=403, detail="Cette action est réservée à l'ordinateur qui héberge le jeu (localhost).")
    with services.LOCK:
        db.begin()
        try:
            db.set_admin(user["id"], True)
            db.commit()
        except Exception:
            db.rollback()
            raise
    return services.build_state(db.get_user(user["id"]))


@app.delete("/api/admin/clubs/{user_id}")
def api_admin_delete_club(user_id: int, body: dict = Body(...), admin=Depends(current_admin)):
    return services.admin_delete_club(admin, user_id, str(body.get("confirm_name", "")))

@app.post("/api/admin/reset-server")
def api_admin_reset_server(request: Request, admin=Depends(current_admin)):
    """Réinitialise toutes les sauvegardes du serveur depuis le panneau admin."""
    token = request.cookies.get(auth.SESSION_COOKIE)
    with services.LOCK:
        db.reset_server(admin["id"], token)
        services.reload_config()
    # Force tous les clients à rafraîchir leur état. L'admin courant conserve
    # sa session ; les autres sessions ont été supprimées.
    for user_id in list(hub.online_ids()):
        if user_id == admin["id"]:
            hub.publish(user_id, "refresh", {"reason": "server_reset"})
        else:
            hub.publish(user_id, "logout", {"reason": "server_reset"})
    return {"ok": True, "message": "Serveur réinitialisé. Toutes les sauvegardes ont été supprimées."}


@app.get("/api/admin/config")
def api_admin_config(admin=Depends(current_admin)):
    return {"defaults": DEFAULT_CONFIG, "overrides": db.get_setting("config_overrides", {}), "effective": services.cfg()}


@app.put("/api/admin/config")
def api_admin_config_put(body: dict = Body(...), admin=Depends(current_admin)):
    overrides = body.get("overrides", {})
    if not isinstance(overrides, dict):
        raise GameError("INVALID", "Format invalide.")
    services.admin_set_config(overrides)
    return {"ok": True, "effective": services.cfg()}


@app.get("/api/admin/users")
def api_admin_users(admin=Depends(current_admin)):
    with services.LOCK:
        users = db.list_users()
        clubs = {e["user_id"]: e for e in db.all_clubs()}
    out = []
    for u in users:
        e = clubs.get(u["id"])
        out.append({"id": u["id"], "username": u["username"], "display_name": u["display_name"],
                    "is_admin": bool(u["is_admin"]), "discord_id": u["discord_id"], "last_seen": u["last_seen"],
                    "club": e["state"].get("name") if e else None,
                    "cash": int(e["state"].get("cash", 0)) if e else None,
                    "level": int(e["state"].get("level", 0)) if e else None})
    return {"users": out}


@app.post("/api/admin/grant")
def api_admin_grant(body: dict = Body(...), admin=Depends(current_admin)):
    return services.admin_grant(admin, body.get("user_id"), int(body.get("amount", 0)),
                                str(body.get("label") or "Ajustement administrateur"))


@app.post("/api/admin/promote")
def api_admin_promote(body: dict = Body(...), admin=Depends(current_admin)):
    with services.LOCK:
        db.begin()
        db.set_admin(int(body.get("user_id")), bool(body.get("is_admin", True)))
        db.commit()
    return {"ok": True}


@app.post("/api/admin/password")
def api_admin_password(body: dict = Body(...), admin=Depends(current_admin)):
    password = str(body.get("password", ""))
    if len(password) < 6:
        raise GameError("INVALID", "Mot de passe : 6 caractères minimum.")
    with services.LOCK:
        db.begin()
        db.update_user(int(body.get("user_id")), password_hash=auth.hash_password(password))
        db.commit()
    return {"ok": True}


@app.post("/api/admin/import-bot")
def api_admin_import(body: dict = Body(...), admin=Depends(current_admin)):
    data = body.get("data")
    if not isinstance(data, dict):
        raise GameError("INVALID", "Envoyez le contenu de nightclub_data.json.")
    return services.admin_import_bot(data, auth.hash_password)


@app.get("/api/admin/club/{user_id}")
def api_admin_club(user_id: int, admin=Depends(current_admin)):
    club, slot = db.get_club(user_id)
    if club is None:
        raise GameError("NOT_FOUND", "Club introuvable.")
    return {"club": club, "slot": slot}


@app.put("/api/admin/club/{user_id}")
def api_admin_club_put(user_id: int, body: dict = Body(...), admin=Depends(current_admin)):
    patch = body.get("patch", {})
    if not isinstance(patch, dict):
        raise GameError("INVALID", "Format invalide.")

    def fn(club):
        for k, v in patch.items():
            if k in club:
                club[k] = v
        return {"club": club}
    club, result = services.mutate(user_id, fn)
    hub.publish(user_id, "refresh", {"reason": "admin"})
    return result


# ------------------------------------------------------------------
# Health check pour les plateformes d'hébergement
# ------------------------------------------------------------------

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "olivia-nightclubs", "version": os.environ.get("RENDER_GIT_COMMIT", "local")}


# ------------------------------------------------------------------
# Statique
# ------------------------------------------------------------------

app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
