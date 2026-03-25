"""Auto ratio farming: scan Free torrents, download, seed, cleanup."""

import json
import logging
import os
import shutil
from pathlib import Path

import config
from services import mteam, qbit

log = logging.getLogger(__name__)

# Persistent state: track which torrents we've already grabbed
STATE_FILE = os.path.join(config.DATA_DIR, "farm_state.json")


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"grabbed_ids": []}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def _get_seed_disk_usage_gb() -> float:
    """Get disk usage of the seed directory in GB."""
    seed_path = Path(config.FARM_SAVE_PATH)
    if not seed_path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in seed_path.rglob("*") if f.is_file())
    return total / (1024 ** 3)


async def scan_and_download() -> list[str]:
    """Scan M-Team for Free torrents and download new ones.

    Returns list of newly added torrent names.
    """
    state = _load_state()
    grabbed = set(state.get("grabbed_ids", []))
    added = []

    # Check disk usage
    disk_gb = _get_seed_disk_usage_gb()
    if disk_gb >= config.FARM_MAX_DISK_GB:
        log.info("Farm disk limit reached: %.1f GB / %d GB", disk_gb, config.FARM_MAX_DISK_GB)
        return added

    # Search for Free torrents
    torrents = await mteam.search_free_torrents(page_size=50)
    if not torrents:
        log.info("No Free torrents found")
        return added

    for t in torrents:
        if t["id"] in grabbed:
            continue

        # Skip tiny files (< 500MB) — not worth the overhead
        if t["size"] < 500 * 1024 * 1024:
            continue

        # Skip if no leechers (nobody downloading = can't upload to anyone)
        if t["leechers"] < 1:
            continue

        # Check remaining disk budget
        remaining_gb = config.FARM_MAX_DISK_GB - disk_gb
        torrent_gb = t["size"] / (1024 ** 3)
        if torrent_gb > remaining_gb:
            continue

        # Get download URL
        dl_url = await mteam.get_download_url(t["id"])
        if not dl_url:
            log.warning("Failed to get download URL for %s", t["name"][:60])
            continue

        # Add to qBittorrent
        ok = await qbit.qbit.add_torrent_url(dl_url, config.FARM_SAVE_PATH, category="seed")
        if ok:
            added.append(t["name"])
            grabbed.add(t["id"])
            disk_gb += torrent_gb
            log.info("Farm added: %s (%.1f GB, %d leechers)", t["name"][:60], torrent_gb, t["leechers"])

        # Limit to 5 new additions per scan
        if len(added) >= 5:
            break

    state["grabbed_ids"] = list(grabbed)
    _save_state(state)
    return added


async def cleanup_completed() -> list[str]:
    """Remove seed torrents that have met their seeding targets.

    Returns list of cleaned up torrent names.
    """
    cleaned = []
    torrents = await qbit.qbit.get_torrents(category="seed")

    for t in torrents:
        ratio = t.get("ratio", 0)
        seed_time_min = t.get("seeding_time", 0) / 60

        # Check if seeding targets met
        ratio_met = ratio >= config.FARM_SEED_RATIO_TARGET
        time_met = seed_time_min >= config.FARM_SEED_TIME_TARGET

        if ratio_met or time_met:
            # Only clean up if we need disk space
            disk_gb = _get_seed_disk_usage_gb()
            if disk_gb > config.FARM_MAX_DISK_GB * 0.8:
                name = t.get("name", "unknown")
                await qbit.qbit.delete_torrent(t["hash"], delete_files=True)
                cleaned.append(name)
                log.info("Farm cleanup: %s (ratio=%.2f, seed_time=%.0f min)", name[:60], ratio, seed_time_min)

    return cleaned


async def get_farm_status() -> dict:
    """Get current farming status."""
    torrents = await qbit.qbit.get_torrents(category="seed")
    disk_gb = _get_seed_disk_usage_gb()

    seeding = 0
    downloading = 0
    total_uploaded = 0
    total_downloaded = 0

    for t in torrents:
        state = t.get("state", "")
        if "upload" in state.lower() or state in ("stalledUP", "uploading", "forcedUP"):
            seeding += 1
        elif "download" in state.lower() or state in ("stalledDL", "downloading"):
            downloading += 1
        total_uploaded += t.get("uploaded", 0)
        total_downloaded += t.get("downloaded", 0)

    return {
        "total_torrents": len(torrents),
        "seeding": seeding,
        "downloading": downloading,
        "disk_usage_gb": round(disk_gb, 1),
        "disk_limit_gb": config.FARM_MAX_DISK_GB,
        "total_uploaded_gb": round(total_uploaded / (1024 ** 3), 2),
        "total_downloaded_gb": round(total_downloaded / (1024 ** 3), 2),
    }
