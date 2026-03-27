"""Radarr API client."""

import logging

import aiohttp

import config

log = logging.getLogger(__name__)


async def _api(method: str, path: str, **kwargs) -> dict | list | None:
    headers = {"X-Api-Key": config.RADARR_API_KEY}
    url = f"{config.RADARR_URL}/api/v3{path}"
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, **kwargs) as resp:
            if resp.status not in (200, 201):
                log.error("Radarr %s %s -> %s", method, path, resp.status)
                return None
            return await resp.json()


async def search_movie(term: str) -> list[dict]:
    """Search for a movie by name."""
    data = await _api("GET", "/movie/lookup", params={"term": term})
    if not data:
        return []
    results = []
    for m in data[:10]:
        results.append({
            "tmdb_id": m.get("tmdbId"),
            "title": m.get("title", ""),
            "year": m.get("year", 0),
            "overview": m.get("overview", "")[:100],
            "quality_profile_id": m.get("qualityProfileId"),
            "images": m.get("images", []),
        })
    return results


async def add_movie(tmdb_id: int, quality_profile_id: int = 0) -> dict | None:
    """Add a movie to Radarr and trigger search."""
    # First lookup to get full movie info
    movies = await _api("GET", "/movie/lookup", params={"term": f"tmdb:{tmdb_id}"})
    if not movies:
        return None
    movie = movies[0]

    # Get default quality profile if not specified
    if not quality_profile_id:
        profiles = await _api("GET", "/qualityprofile")
        if profiles:
            quality_profile_id = profiles[0]["id"]

    movie["qualityProfileId"] = quality_profile_id
    movie["rootFolderPath"] = "/media/movies"
    movie["monitored"] = True
    movie["addOptions"] = {"searchForMovie": True}

    return await _api("POST", "/movie", json=movie)


async def get_queue() -> list[dict]:
    """Get current download queue."""
    data = await _api("GET", "/queue", params={"pageSize": 50})
    if not data:
        return []
    records = data.get("records", [])
    results = []
    for r in records:
        results.append({
            "title": r.get("title", ""),
            "status": r.get("status", ""),
            "progress": round((1 - r.get("sizeleft", 0) / max(r.get("size", 1), 1)) * 100, 1),
            "size": r.get("size", 0),
            "timeleft": r.get("timeleft", ""),
        })
    return results


async def find_in_library(title: str, year: int = 0) -> dict | None:
    """Check if a movie already exists in Radarr library."""
    data = await _api("GET", "/movie")
    if not data:
        return None
    for m in data:
        if m.get("title", "").lower() == title.lower() and (year == 0 or m.get("year", 0) == year):
            return {"title": m["title"], "year": m.get("year", 0), "has_file": m.get("hasFile", False)}
    return None


async def get_movies() -> list[dict]:
    """Get all monitored movies."""
    data = await _api("GET", "/movie")
    if not data:
        return []
    return [
        {
            "title": m.get("title", ""),
            "year": m.get("year", 0),
            "has_file": m.get("hasFile", False),
            "monitored": m.get("monitored", False),
        }
        for m in data
    ]
