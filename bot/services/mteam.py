"""M-Team API client."""

import logging
from typing import Any

import aiohttp

import config

log = logging.getLogger(__name__)

# M-Team API uses api.m-team.cc for API calls
API_BASE = "https://api.m-team.cc"


async def _request(method: str, path: str, json_body: dict | None = None) -> dict | None:
    headers = {
        "x-api-key": config.MT_API_TOKEN,
        "Content-Type": "application/json",
    }
    url = f"{API_BASE}{path}"
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, json=json_body or {}) as resp:
            if resp.status != 200:
                text = await resp.text()
                log.error("M-Team API %s %s -> %s: %s", method, path, resp.status, text[:500])
                return None
            return await resp.json()


async def get_profile() -> dict[str, Any] | None:
    """Get current user profile: ratio, upload, download, bonus."""
    data = await _request("POST", "/api/member/profile")
    if not data or "data" not in data:
        return None
    p = data["data"]
    return {
        "username": p.get("username", ""),
        "ratio": float(p.get("ratio", 0)),
        "uploaded": int(p.get("uploaded", 0)),
        "downloaded": int(p.get("downloaded", 0)),
        "bonus": float(p.get("bonus", 0)),
        "seeding": int(p.get("seeding", 0)),
        "leeching": int(p.get("leeching", 0)),
        "user_class": p.get("role", ""),
    }


async def search_free_torrents(
    page: int = 1,
    page_size: int = 50,
    categories: list[str] | None = None,
) -> list[dict]:
    """Search for Free/2xFree torrents on M-Team."""
    results = []
    for discount in ["FREE", "2XFREE", "_2X_FREE"]:
        body = {
            "mode": "normal",
            "visible": 1,
            "pageNumber": page,
            "pageSize": page_size,
            "sortField": "CREATED_DATE",
            "sortDirection": "DESC",
            "discount": discount,
        }
        if categories:
            body["categories"] = categories

        data = await _request("POST", "/api/torrent/search", body)
        if not data:
            log.warning("M-Team search returned None for discount=%s", discount)
            continue

        log.info("M-Team search discount=%s response keys=%s", discount, list(data.keys()) if isinstance(data, dict) else type(data))

        if "data" not in data:
            log.warning("M-Team search no 'data' key, full response: %s", str(data)[:500])
            continue

        torrents_data = data["data"]
        log.info("M-Team torrents_data type=%s keys=%s", type(torrents_data).__name__, list(torrents_data.keys()) if isinstance(torrents_data, dict) else f"len={len(torrents_data)}" if isinstance(torrents_data, list) else "?")

        # Handle both list and paginated response
        torrent_list = torrents_data if isinstance(torrents_data, list) else torrents_data.get("data", [])

        if torrent_list:
            log.info("M-Team first torrent sample: %s", str(torrent_list[0])[:500])

        for t in torrent_list:
            # Try multiple possible field names for size/seeders/leechers
            size = int(t.get("size", 0) or 0)
            status = t.get("status", {}) or {}
            seeders = int(status.get("seeders", 0) if isinstance(status, dict) else 0)
            leechers = int(status.get("leechers", 0) if isinstance(status, dict) else 0)

            results.append({
                "id": str(t.get("id", "")),
                "name": t.get("name", t.get("title", "")),
                "size": size,
                "seeders": seeders,
                "leechers": leechers,
                "discount": discount,
                "category": t.get("category", ""),
                "created": t.get("createdDate", ""),
            })

    # Sort: prefer 2xFree first, then by leechers (more leechers = more upload opportunity)
    results.sort(key=lambda x: (x["discount"] != "2XFREE", -x["leechers"], -x["size"]))
    return results


async def get_download_url(torrent_id: str) -> str | None:
    """Get download URL for a torrent."""
    data = await _request("POST", "/api/torrent/genDlToken", {"id": torrent_id})
    if not data or "data" not in data:
        return None
    return data["data"]


async def search_torrents(keyword: str, page: int = 1, page_size: int = 20) -> list[dict]:
    """Search torrents by keyword (for movie/tv search)."""
    body = {
        "mode": "normal",
        "visible": 1,
        "keyword": keyword,
        "pageNumber": page,
        "pageSize": page_size,
        "sortField": "CREATED_DATE",
        "sortDirection": "DESC",
    }
    data = await _request("POST", "/api/torrent/search", body)
    if not data or "data" not in data:
        return []

    torrents_data = data["data"]
    torrent_list = torrents_data if isinstance(torrents_data, list) else torrents_data.get("data", [])

    results = []
    for t in torrent_list:
        results.append({
            "id": str(t.get("id", "")),
            "name": t.get("name", ""),
            "size": int(t.get("size", 0)),
            "seeders": int(t.get("status", {}).get("seeders", 0)),
            "leechers": int(t.get("status", {}).get("leechers", 0)),
            "discount": t.get("status", {}).get("discount", "NORMAL"),
            "category": t.get("category", ""),
        })
    return results
