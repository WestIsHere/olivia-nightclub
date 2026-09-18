"""Authentification : mots de passe (scrypt, stdlib) + sessions cookie."""

import hashlib
import hmac
import os
import re
import secrets

from .db import LOCK

SESSION_COOKIE = "olivia_session"
SESSION_TTL = 60 * 60 * 24 * 30  # 30 jours

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,24}$")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, digest_hex = stored.split("$")
        if algo != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def new_session(db, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with LOCK:
        db.begin()
        db.purge_sessions()
        db.create_session(token, user_id, SESSION_TTL)
        db.commit()
    return token


def user_from_token(db, token):
    if not token:
        return None
    with LOCK:
        return db.get_session_user(token)


def valid_username(username: str) -> bool:
    return bool(USERNAME_RE.match(username or ""))
