"""Auto ratio farming: scan Free torrents, download, seed, cleanup.

Lifecycle:
  1. scan_and_download: find Free torrents → add to qBittorrent
  2. protect_ratio: pause/remove torrents still downloading after Free expired
  3. cleanup_completed: remove seeded torrents that met targets (when disk tight)
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import config
from services import mteam, qbit

log = logging.getLogger(__name__)

STATE_FILE = os.path.join(config.DATA_DIR, "farm_state.json")


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"grabbed": {}}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _get_seed_disk_usage_gb() -> float:
    seed_path = Path(config.FARM_SAVE_PATH)
    if not seed_path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in seed_path.rglob("*") if f.is_file())
    return total / (1024 ** 3)


# ─── 1. Scan & Download ───

async def scan_and_download() -> list[str]:
    """Find Free torrents on M-Team and add to qBittorrent.

    Returns list of newly added torrent names.
    """
    state = _load_state()
    grabbed = state.get("grabbed", {})
    # Migrate old format
    if "grabbed_ids" in state:
        for tid in state.pop("grabbed_ids", []):
            grabbed.setdefault(tid, {})
        state["grabbed"] = grabbed
    added = []

    # Check torrent count limit
    current_torrents = await qbit.qbit.get_torrents(category="seed")
    if len(current_torrents) >= config.FARM_MAX_TORRENTS:
        log.info("Farm torrent limit reached: %d / %d", len(current_torrents), config.FARM_MAX_TORRENTS)
        return added

    disk_gb = _get_seed_disk_usage_gb()
    if disk_gb >= config.FARM_MAX_DISK_GB:
        log.info("Farm disk limit reached: %.1f / %d GB", disk_gb, config.FARM_MAX_DISK_GB)
        return added

    torrents = await mteam.search_free_torrents(page_size=50)
    if not torrents:
        log.info("No Free torrents found")
        return added

    for t in torrents:
        if t["id"] in grabbed:
            continue

        if t["size"] < 100 * 1024 * 1024:
            continue

        if t["seeders"] < 1 and t["leechers"] < 1:
            continue

        # Check Free remaining time
        discount_end = t.get("discount_end", "")
        if discount_end:
            try:
                end_time = datetime.strptime(discount_end, "%Y-%m-%d %H:%M:%S")
                remaining_hours = (end_time - datetime.now()).total_seconds() / 3600
                min_hours = 2 if t["size"] < 5 * 1024 ** 3 else 6
                if remaining_hours < min_hours:
                    log.info("Skip %s: Free expires in %.1fh", t["name"][:40], remaining_hours)
                    continue
            except (ValueError, TypeError):
                pass

        remaining_gb = config.FARM_MAX_DISK_GB - disk_gb
        torrent_gb = t["size"] / (1024 ** 3)
        if torrent_gb > remaining_gb:
            continue

        dl_url = await mteam.get_download_url(t["id"])
        if not dl_url:
            log.warning("No download URL for %s", t["name"][:60])
            continue

        ok = await qbit.qbit.add_torrent_url(dl_url, config.FARM_SAVE_PATH, category="seed")
        if ok:
            added.append(t["name"])
            grabbed[t["id"]] = {
                "name": t["name"],
                "size": t["size"],
                "discount_end": discount_end,
                "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            disk_gb += torrent_gb
            log.info("Farm added: %s (%.1fGB, S:%d L:%d, Free until %s)",
                     t["name"][:50], torrent_gb, t["seeders"], t["leechers"], discount_end or "unknown")

        if len(added) >= 10:
            break

    state["grabbed"] = grabbed
    _save_state(state)
    return added


# ─── 2. Protect Ratio ───

async def protect_ratio() -> list[str]:
    """Pause/remove seed torrents still downloading after Free expired.

    Returns list of protected (paused/removed) torrent names.
    """
    protected = []
    state = _load_state()
    grabbed = state.get("grabbed", {})

    torrents = await qbit.qbit.get_torrents(category="seed")
    now = datetime.now()

    for t in torrents:
        qbit_state = t.get("state", "")
        is_downloading = qbit_state in ("downloading", "stalledDL", "metaDL", "forcedDL")

        if not is_downloading:
            continue  # Already completed or seeding — safe

        name = t.get("name", "")
        torrent_hash = t["hash"]

        # Find discount_end from our state
        discount_end_str = None
        for tid, info in grabbed.items():
            if isinstance(info, dict) and info.get("name", "") == name:
                discount_end_str = info.get("discount_end", "")
                break

        if not discount_end_str:
            continue  # Unknown expiry, can't check

        try:
            end_time = datetime.strptime(discount_end_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue

        if now > end_time:
            # Free expired, still downloading → DANGER, remove it
            progress = t.get("progress", 0) * 100
            await qbit.qbit.delete_torrent(torrent_hash, delete_files=True)
            protected.append(name)
            log.warning("RATIO PROTECT: Removed %s (%.1f%% done, Free expired %s)", name[:50], progress, discount_end_str)

    return protected


# ─── 3. Cleanup Completed ───

async def cleanup_completed() -> list[str]:
    """Remove seeding torrents that met ratio/time targets when disk is tight.

    Returns list of cleaned up torrent names.
    """
    cleaned = []
    disk_gb = _get_seed_disk_usage_gb()

    # Only clean up when disk is above 80% of limit
    if disk_gb < config.FARM_MAX_DISK_GB * 0.8:
        return cleaned

    torrents = await qbit.qbit.get_torrents(category="seed")

    # Sort: most "done" first (highest ratio + longest seed time)
    torrents.sort(key=lambda t: -(t.get("ratio", 0) + t.get("seeding_time", 0) / 86400))

    for t in torrents:
        ratio = t.get("ratio", 0)
        seed_time_min = t.get("seeding_time", 0) / 60

        ratio_met = ratio >= config.FARM_SEED_RATIO_TARGET
        time_met = seed_time_min >= config.FARM_SEED_TIME_TARGET

        if ratio_met or time_met:
            name = t.get("name", "unknown")
            size_gb = t.get("total_size", 0) / (1024 ** 3)
            await qbit.qbit.delete_torrent(t["hash"], delete_files=True)
            cleaned.append(name)
            disk_gb -= size_gb
            log.info("Cleanup: %s (ratio=%.2f, seed=%.0fmin)", name[:50], ratio, seed_time_min)

            if disk_gb < config.FARM_MAX_DISK_GB * 0.6:
                break  # Freed enough space

    return cleaned


# ─── 4. Status ───

async def get_farm_status() -> dict:
    torrents = await qbit.qbit.get_torrents(category="seed")
    disk_gb = _get_seed_disk_usage_gb()

    seeding = 0
    downloading = 0
    total_uploaded = 0
    total_downloaded = 0

    for t in torrents:
        st = t.get("state", "")
        if st in ("uploading", "stalledUP", "forcedUP"):
            seeding += 1
        elif st in ("downloading", "stalledDL", "metaDL", "forcedDL"):
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
