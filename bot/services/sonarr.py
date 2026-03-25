"""Sonarr API client."""

import logging

import aiohttp

import config

log = logging.getLogger(__name__)


async def _api(method: str, path: str, **kwargs) -> dict | list | None:
    headers = {"X-Api-Key": config.SONARR_API_KEY}
    url = f"{config.SONARR_URL}/api/v3{path}"
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, **kwargs) as resp:
            if resp.status not in (200, 201):
                log.error("Sonarr %s %s -> %s", method, path, resp.status)
                return None
            return await resp.json()


async def search_series(term: str) -> list[dict]:
    """Search for a TV series by name."""
    data = await _api("GET", "/series/lookup", params={"term": term})
    if not data:
        return []
    results = []
    for s in data[:10]:
        results.append({
            "tvdb_id": s.get("tvdbId"),
            "title": s.get("title", ""),
            "year": s.get("year", 0),
            "overview": s.get("overview", "")[:100],
            "season_count": s.get("statistics", {}).get("seasonCount", 0),
        })
    return results


async def add_series(tvdb_id: int, quality_profile_id: int = 0) -> dict | None:
    """Add a TV series to Sonarr and trigger search."""
    series_list = await _api("GET", "/series/lookup", params={"term": f"tvdb:{tvdb_id}"})
    if not series_list:
        return None
    series = series_list[0]

    if not quality_profile_id:
        profiles = await _api("GET", "/qualityprofile")
        if profiles:
            quality_profile_id = profiles[0]["id"]

    series["qualityProfileId"] = quality_profile_id
    series["rootFolderPath"] = "/media/tv"
    series["monitored"] = True
    series["addOptions"] = {"searchForMissingEpisodes": True}

    return await _api("POST", "/series", json=series)


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
            "episode": r.get("episode", {}).get("title", ""),
        })
    return results
