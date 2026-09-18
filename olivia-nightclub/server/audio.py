"""
Assets audio : scan du dossier web/audio → table audio_assets → manifeste client.

Arborescence :
  web/audio/robbery/*.mp3|ogg|wav          FX de braquage (global)
  web/audio/showcases/<artiste>/*          extraits de showcase (local à la vue du club)
  web/audio/showcases/_placeholder/*       secours tant qu'un dossier d'artiste est vide
  web/audio/ambient/*                      ambiance de club
  web/audio/ui/<nom>.*                     sons d'interface / notifications
  web/audio/events/<nom>.*                 événements

La base (audio_assets) reste la référence : l'admin peut désactiver un asset ou
changer son poids ; le scan ne touche pas à ces réglages.
"""

import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
import wave

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "web", "audio")
EXTENSIONS = (".mp3", ".ogg", ".wav", ".m4a", ".webm")
CATEGORIES = ("robbery", "showcases", "ambient", "ui", "events")


def slug(name):
    """'Boro 700' → 'boro_700', 'Bello&Dallas' → 'bello_dallas' (même règle que le générateur)."""
    n = unicodedata.normalize("NFD", str(name)).encode("ascii", "ignore").decode().lower()
    return "".join(c if c.isalnum() else "_" for c in n).strip("_")


def _duration(path):
    if path.lower().endswith(".wav"):
        try:
            with wave.open(path, "rb") as w:
                return round(w.getnframes() / float(w.getframerate()), 3)
        except Exception:
            return None
    return None


def scan_files():
    """Liste (category, key, url, duration) pour chaque fichier audio présent."""
    found = []
    if not os.path.isdir(AUDIO_DIR):
        return found
    for category in CATEGORIES:
        root = os.path.join(AUDIO_DIR, category)
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for name in sorted(files):
                if not name.lower().endswith(EXTENSIONS):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, os.path.join(BASE_DIR, "web")).replace(os.sep, "/")
                sub = os.path.relpath(dirpath, root).replace(os.sep, "/")
                if category == "showcases":
                    key = sub.split("/")[0] if sub != "." else "_placeholder"
                elif category in ("ui", "events"):
                    key = os.path.splitext(name)[0].lower()
                else:
                    key = category
                found.append({"category": category, "key": key, "file_url": rel, "duration": _duration(full)})
    return found


YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
YT_URL_PATTERNS = [
    re.compile(r"(?:v=|/shorts/|/embed/|youtu\.be/|/live/)([A-Za-z0-9_-]{11})"),
]


def parse_youtube_ids(text):
    """Extrait les identifiants vidéo YouTube d'un texte (URLs ou IDs bruts, un par ligne/espace)."""
    ids = []
    for token in re.split(r"[\s,;]+", str(text or "")):
        token = token.strip()
        if not token:
            continue
        found = None
        for pat in YT_URL_PATTERNS:
            m = pat.search(token)
            if m:
                found = m.group(1)
                break
        if not found and YT_ID_RE.match(token):
            found = token
        if found and found not in ids:
            ids.append(found)
    return ids


def youtube_title(video_id, timeout=4.0):
    """Titre + chaîne via oEmbed (aucune clé API nécessaire). Best-effort."""
    try:
        url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(
            f"https://www.youtube.com/watch?v={video_id}", safe="")
        req = urllib.request.Request(url, headers={"User-Agent": "OliviaNightclubs/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("title"), data.get("author_name")
    except Exception:
        return None, None


def add_youtube_assets(db, artist, video_ids, titles=None, note=None):
    """
    Ajoute des clips YouTube pour un artiste (category=showcases, key=slug(artiste), kind=youtube).
    `titles` : {video_id: (title, author)} récupéré AVANT (hors verrou) via youtube_title().
    """
    key = slug(artist)
    titles = titles or {}
    added, skipped = [], []
    for vid in video_ids:
        url = f"yt:{vid}"
        if db.get_audio_asset_by_url(url):
            skipped.append(vid)
            continue
        title, author = titles.get(vid, (None, None))
        full_note = note or (f"chaîne : {author}" if author else None)
        aid = db.add_audio_asset("showcases", key, url, None, kind="youtube", title=title, note=full_note)
        added.append({"id": aid, "video_id": vid, "title": title, "author": author})
    return {"artist": artist, "key": key, "added": added, "skipped": skipped}


def sync_assets(db):
    """Met la table audio_assets en phase avec le disque (conserve enabled/weight, ignore YouTube)."""
    files = scan_files()
    urls = {f["file_url"] for f in files}
    existing = {a["file_url"]: a for a in db.list_audio_assets() if a.get("kind", "file") == "file"}
    added = 0
    for f in files:
        if f["file_url"] in existing:
            db.update_audio_asset_meta(existing[f["file_url"]]["id"], f["duration"])
        else:
            db.add_audio_asset(f["category"], f["key"], f["file_url"], f["duration"])
            added += 1
    removed = 0
    for url, a in existing.items():
        if url not in urls:
            db.delete_audio_asset(a["id"])
            removed += 1
    return {"added": added, "removed": removed, "total": len(files)}


def build_manifest(db, cfg):
    """Manifeste envoyé au client (assets activés uniquement)."""
    audio_cfg = cfg.get("audio", {})
    yt_enabled = bool(audio_cfg.get("youtube_enabled", True))
    assets = [a for a in db.list_audio_assets() if a["enabled"]]
    out = {"robbery": [], "showcases": {}, "ambient": [], "ui": {}, "events": {}}
    for a in assets:
        kind = a.get("kind") or "file"
        if kind == "youtube":
            if not yt_enabled:
                continue
            item = {"id": a["id"], "type": "youtube", "video_id": a["file_url"][3:], "title": a.get("title"),
                    "weight": a["weight"], "duration": audio_cfg.get("youtube_clip_seconds", 30)}
        else:
            item = {"id": a["id"], "type": "file", "url": a["file_url"], "duration": a["duration"], "weight": a["weight"]}
        cat = a["category"]
        if cat == "robbery":
            out["robbery"].append(item)
        elif cat == "ambient":
            out["ambient"].append(item)
        elif cat == "showcases":
            out["showcases"].setdefault(a["key"], []).append(item)
        elif cat in ("ui", "events"):
            out[cat].setdefault(a["key"], []).append(item)
    artist_keys = {name: slug(name) for name in cfg["artists"].keys()}
    artist_keys["Saisai"] = "saisai"
    return {
        "assets": out,
        "artist_keys": artist_keys,
        "showcase_fallback": bool(audio_cfg.get("showcase_fallback_placeholder", True)),
        "fallback_key": "_placeholder",
        "settings": {
            "ducking": audio_cfg.get("ambient_ducking", 0.35),
            "clip_gap": audio_cfg.get("showcase_clip_gap", [4, 9]),
            "fx_window": audio_cfg.get("fx_spam_window", 10),
            "fx_max": audio_cfg.get("fx_spam_max", 3),
            "fx_volumes": audio_cfg.get("fx_spam_volumes", [1.0, 0.7, 0.5]),
            "fx_gap": audio_cfg.get("fx_min_gap", 1.2),
            "fade": audio_cfg.get("fade_seconds", 0.35),
            "youtube_enabled": yt_enabled,
            "youtube_clip_seconds": audio_cfg.get("youtube_clip_seconds", 30),
            "youtube_start_range": audio_cfg.get("youtube_start_range", [20, 75]),
        },
        "defaults": audio_cfg.get("default_prefs", {}),
    }
