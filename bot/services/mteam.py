"""M-Team API client.

M-Team API uses form-encoded POST data (not JSON).
"""

import logging
from typing import Any

import aiohttp

import config

log = logging.getLogger(__name__)

API_BASE = "https://api.m-team.cc"


async def _request(path: str, body: dict | None = None, use_form: bool = False) -> dict | None:
    """POST to M-Team API. JSON by default, form-encoded when use_form=True."""
    headers = {"x-api-key": config.MT_API_TOKEN}
    url = f"{API_BASE}{path}"
    kwargs = {"data": body or {}} if use_form else {"json": body or {}}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, **kwargs) as resp:
            if resp.status != 200:
                text = await resp.text()
                log.error("M-Team API %s -> %s: %s", path, resp.status, text[:500])
                return None
            result = await resp.json()
            if result.get("code") != "0":
                log.warning("M-Team API %s code=%s msg=%s", path, result.get("code"), result.get("message"))
                return None
            return result


async def get_profile() -> dict[str, Any] | None:
    """Get current user profile: ratio, upload, download, bonus."""
    data = await _request("/api/member/profile")
    if not data or "data" not in data:
        return None
    p = data["data"]
    mc = p.get("memberCount", {}) or {}
    return {
        "username": p.get("username", ""),
        "ratio": float(mc.get("shareRate", 0) or 0),
        "uploaded": int(mc.get("uploaded", 0) or 0),
        "downloaded": int(mc.get("downloaded", 0) or 0),
        "bonus": float(mc.get("bonus", 0) or 0),
        "seedtime": int(p.get("seedtime", 0) or 0),
        "leechtime": int(p.get("leechtime", 0) or 0),
        "user_class": p.get("role", ""),
    }


async def search_free_torrents(
    page: int = 1,
    page_size: int = 100,
) -> list[dict]:
    """Search for Free/2xFree torrents on M-Team."""
    results = []

    body = {
        "mode": "normal",
        "visible": "1",
        "pageNumber": str(page),
        "pageSize": str(page_size),
        "sortField": "LEECHERS",
        "sortDirection": "DESC",
        "discount": "FREE",
    }

    data = await _request("/api/torrent/search", body)
    if not data or "data" not in data:
        log.warning("M-Team free search returned no data")
        return results

    torrents_data = data["data"]
    torrent_list = torrents_data.get("data", []) if isinstance(torrents_data, dict) else torrents_data

    log.info("M-Team free search: total=%s, returned=%d", torrents_data.get("total", "?") if isinstance(torrents_data, dict) else "?", len(torrent_list))

    for t in torrent_list:
        status = t.get("status", {}) or {}
        results.append({
            "id": str(t.get("id", "")),
            "name": t.get("name", ""),
            "smallDescr": t.get("smallDescr", ""),
            "size": int(t.get("size", 0) or 0),
            "seeders": int(status.get("seeders", 0) or 0),
            "leechers": int(status.get("leechers", 0) or 0),
            "discount": status.get("discount", "NORMAL"),
            "discount_end": status.get("discountEndTime", ""),
            "category": t.get("category", ""),
            "created": t.get("createdDate", ""),
        })

    # Sort by upload potential: leechers / (seeders + 1) = demand per seeder
    # Higher = less competition per leecher = more upload for you
    # Tiebreak by size (bigger = more magic points)
    results.sort(key=lambda x: -(x["leechers"] / max(x["seeders"] + 1, 1) * x["size"]))
    return results


async def get_download_url(torrent_id: str) -> str | None:
    """Get .torrent download URL for a torrent."""
    data = await _request("/api/torrent/genDlToken", {"id": torrent_id}, use_form=True)
    if not data or "data" not in data:
        return None
    return data["data"]


async def search_torrents(keyword: str, page: int = 1, page_size: int = 20) -> list[dict]:
    """Search torrents by keyword (for movie/tv search)."""
    body = {
        "mode": "normal",
        "visible": "1",
        "keyword": keyword,
        "pageNumber": str(page),
        "pageSize": str(page_size),
        "sortField": "CREATED_DATE",
        "sortDirection": "DESC",
    }
    data = await _request("/api/torrent/search", body)
    if not data or "data" not in data:
        return []

    torrents_data = data["data"]
    torrent_list = torrents_data.get("data", []) if isinstance(torrents_data, dict) else torrents_data

    results = []
    for t in torrent_list:
        status = t.get("status", {}) or {}
        results.append({
            "id": str(t.get("id", "")),
            "name": t.get("name", ""),
            "smallDescr": t.get("smallDescr", ""),
            "size": int(t.get("size", 0) or 0),
            "seeders": int(status.get("seeders", 0) or 0),
            "leechers": int(status.get("leechers", 0) or 0),
            "discount": status.get("discount", "NORMAL"),
            "category": t.get("category", ""),
        })
    return results
