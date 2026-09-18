"""Programme vidéo partagé d'une boîte. Les liens restent chez YouTube."""
import json
import math
import random
import re
from pathlib import Path

DEFAULT_VIDEOS = json.loads(Path(__file__).with_name("showcase_videos.json").read_text(encoding="utf-8"))
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def choose_playlist(cfg, artist, assets, previous=None, rng=None):
    if not cfg.get("audio", {}).get("youtube_enabled", True):
        return []
    from .audio import slug
    clips = list(cfg.get("audio", {}).get("showcase_videos", {}).get(artist, []))
    disabled = {a["file_url"][3:] for a in assets if a.get("kind") == "youtube" and not a["enabled"]}
    clips += [{"video_id": a["file_url"][3:], "title": a.get("title") or artist,
               "duration": a.get("duration") or 240}
              for a in assets if a.get("kind") == "youtube" and a["enabled"] and a["key"] == slug(artist)]
    valid = {}
    for clip in clips:
        vid = str(clip.get("video_id", ""))
        if VIDEO_ID.fullmatch(vid) and vid not in disabled:
            try:
                duration = float(clip.get("duration", 240))
            except (TypeError, ValueError):
                duration = 240
            valid[vid] = {"video_id": vid, "title": str(clip.get("title") or artist),
                          "duration": max(30, min(1800, duration)) if math.isfinite(duration) else 240}
    playlist = list(valid.values())
    rng = rng or random.SystemRandom()
    rng.shuffle(playlist)
    if len(playlist) > 1 and playlist[0]["video_id"] == previous:
        playlist.append(playlist.pop(0))
    return playlist


def screen_payload(row, now):
    if not row or row["status"] != "active" or now >= row["ends_at"]:
        return None
    out = {"showcase_id": row["id"], "club_id": row["club_id"], "artist": row["artist"],
           "started_at": row["started_at"], "ends_at": row["ends_at"], "video": None}
    playlist = json.loads(row.get("screen_playlist") or "[]")
    if not playlist:
        return out
    duration = sum(c["duration"] for c in playlist)
    elapsed = max(0, now - row["started_at"])
    cycle = int(elapsed // duration)
    offset = elapsed % duration
    start = row["started_at"] + cycle * duration
    for index, clip in enumerate(playlist):
        if offset < clip["duration"]:
            out["video"] = {**clip, "key": f'{row["id"]}:{cycle}:{index}',
                            "started_at": start, "ends_at": min(start + clip["duration"], row["ends_at"])}
            break
        offset -= clip["duration"]
        start += clip["duration"]
    return out
