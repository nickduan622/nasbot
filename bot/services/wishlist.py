"""Wishlist service: persistent queue for movies and TV shows."""

import json
import logging
import os
from datetime import datetime

import config

log = logging.getLogger(__name__)

WISHLIST_FILE = os.path.join(config.DATA_DIR, "wishlist.json")


def _load() -> dict:
    if os.path.exists(WISHLIST_FILE):
        with open(WISHLIST_FILE) as f:
            return json.load(f)
    return {"movies": [], "tv": []}


def _save(data: dict):
    os.makedirs(os.path.dirname(WISHLIST_FILE), exist_ok=True)
    with open(WISHLIST_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_movie(title: str, year: int = 0, tmdb_id: int = 0, source: str = "manual") -> dict:
    """Add a movie to wishlist. Returns the entry."""
    data = _load()
    entry = {
        "title": title,
        "year": year,
        "tmdb_id": tmdb_id,
        "source": source,
        "status": "pending",
        "added": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data["movies"].append(entry)
    _save(data)
    log.info("Wishlist add movie: %s (%d)", title, year)
    return entry


def add_tv(title: str, year: int = 0, tvdb_id: int = 0, source: str = "manual") -> dict:
    """Add a TV show to wishlist. Returns the entry."""
    data = _load()
    entry = {
        "title": title,
        "year": year,
        "tvdb_id": tvdb_id,
        "source": source,
        "status": "pending",
        "added": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data["tv"].append(entry)
    _save(data)
    log.info("Wishlist add tv: %s (%d)", title, year)
    return entry


def update_status(media_type: str, title: str, status: str, year: int = 0):
    """Update status of a wishlist entry."""
    data = _load()
    items = data.get(media_type, [])
    for item in items:
        if item["title"] == title and (year == 0 or item.get("year", 0) == year):
            item["status"] = status
            _save(data)
            return True
    return False


def get_pending(media_type: str) -> list[dict]:
    """Get all pending entries for a media type."""
    data = _load()
    return [m for m in data.get(media_type, []) if m.get("status") == "pending"]


def get_all(media_type: str) -> list[dict]:
    """Get all entries for a media type."""
    data = _load()
    return data.get(media_type, [])


def get_summary() -> dict:
    """Get counts by status."""
    data = _load()
    summary = {"movies": {}, "tv": {}}
    for mt in ("movies", "tv"):
        for item in data.get(mt, []):
            s = item.get("status", "pending")
            summary[mt][s] = summary[mt].get(s, 0) + 1
    return summary


def remove(media_type: str, title: str, year: int = 0) -> bool:
    """Remove an entry from wishlist."""
    data = _load()
    items = data.get(media_type, [])
    before = len(items)
    data[media_type] = [
        m for m in items
        if not (m["title"] == title and (year == 0 or m.get("year", 0) == year))
    ]
    if len(data[media_type]) < before:
        _save(data)
        return True
    return False
