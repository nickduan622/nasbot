"""Scheduled tasks: farm scanning, download monitoring, daily report."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from services import farmer, mteam, qbit, wishlist
from utils import fmt_bytes

log = logging.getLogger(__name__)

_bot = None
_chat_id = None


async def _send(text: str):
    if _bot and _chat_id:
        try:
            await _bot.send_message(chat_id=_chat_id, text=text)
        except Exception as e:
            log.error("Failed to send message: %s", e)


async def farm_scan_job():
    """Periodic farm scan — find and download Free torrents."""
    if not config.FARM_ENABLED:
        return

    try:
        rotated = await farmer.rotate_underperformers()
        added = await farmer.scan_and_download()
        cleaned = await farmer.cleanup_completed()
        status = await farmer.get_farm_status()

        # Only notify when something actually happened
        has_changes = rotated or added or cleaned
        if has_changes:
            lines = ["🌱 养号扫描"]

            if rotated:
                for info in rotated:
                    lines.append(f"  🔄 {info}")
            if added:
                for info in added:
                    lines.append(f"  ➕ {info}")
            if cleaned:
                for info in cleaned:
                    lines.append(f"  🗑️ {info}")

            lines.append(f"\n📊 {status['seeding']}做种 {status['downloading']}下载 | "
                         f"↑{status['total_uploaded_gb']}GB | "
                         f"磁盘 {status['disk_usage_gb']}/{status['disk_limit_gb']}GB")

            await _send("\n".join(lines))
    except Exception as e:
        log.error("Farm scan error: %s", e)


async def ratio_protect_job():
    """Check every 5 min: remove downloading torrents whose Free expired."""
    try:
        protected = await farmer.protect_ratio()
        if protected:
            lines = ["🛡️ 分享率保护"]
            for info in protected:
                lines.append(f"  🗑️ {info}")
            await _send("\n".join(lines))
    except Exception as e:
        log.error("Ratio protect error: %s", e)


async def download_monitor_job():
    """Check for completed downloads and notify."""
    try:
        torrents = await qbit.qbit.get_torrents()
        for t in torrents:
            state = t.get("state", "")
            category = t.get("category", "")
            name = t.get("name", "")

            if category == "seed":
                continue

            if state in ("uploading", "stalledUP", "forcedUP"):
                tags = t.get("tags", "")
                if "notified" not in tags:
                    size = fmt_bytes(t.get("total_size", 0))
                    await _send(f"✅ 下载完成！\n📁 {name}\n💾 {size}")
                    async with qbit.qbit._session() as session:
                        await session.post(
                            f"{config.QBIT_URL}/api/v2/torrents/addTags",
                            data={"hashes": t["hash"], "tags": "notified"},
                        )

            progress = t.get("progress", 0)
            tags = t.get("tags", "")
            if progress >= 0.75 and "p75" not in tags and state == "downloading":
                await _send(f"⬇️ {name[:40]}\n{'█' * 7}{'░' * 3} 75%")
                async with qbit.qbit._session() as session:
                    await session.post(
                        f"{config.QBIT_URL}/api/v2/torrents/addTags",
                        data={"hashes": t["hash"], "tags": "p75"},
                    )
            elif progress >= 0.50 and "p50" not in tags and state == "downloading":
                await _send(f"⬇️ {name[:40]}\n{'█' * 5}{'░' * 5} 50%")
                async with qbit.qbit._session() as session:
                    await session.post(
                        f"{config.QBIT_URL}/api/v2/torrents/addTags",
                        data={"hashes": t["hash"], "tags": "p50"},
                    )
    except Exception as e:
        log.error("Download monitor error: %s", e)


async def daily_report_job():
    """Send daily ratio/farm report."""
    try:
        profile = await mteam.get_profile()
        farm_status = await farmer.get_farm_status()

        if profile:
            ratio_str = f"{profile['ratio']:.2f}" if profile['ratio'] else "∞"
            text = (
                "📊 每日报告\n\n"
                f"🌐 M-Team\n"
                f"  分享率: {ratio_str}\n"
                f"  上传: {fmt_bytes(profile['uploaded'])}\n"
                f"  下载: {fmt_bytes(profile['downloaded'])}\n"
                f"  魔力值: {profile['bonus']:,.1f}\n\n"
                f"🌱 养号\n"
                f"  做种: {farm_status['seeding']} 个\n"
                f"  磁盘: {farm_status['disk_usage_gb']}/{farm_status['disk_limit_gb']} GB\n"
                f"  养号上传: {farm_status['total_uploaded_gb']} GB"
            )

            if profile['ratio'] and profile['ratio'] < 0.5:
                text += "\n\n⚠️ 分享率低于 0.5，请注意！"

            await _send(text)
    except Exception as e:
        log.error("Daily report error: %s", e)


async def wishlist_sync_job():
    """Sync wishlist status with Radarr/Sonarr every 10 minutes."""
    try:
        updated = await wishlist.sync_status()
        if updated:
            await _send(f"📋 队列更新: {updated} 部影视下载完成，已标记 ✅")
    except Exception as e:
        log.error("Wishlist sync error: %s", e)


async def ratio_alert_job():
    """Check ratio and auto-pause non-seed downloads if ratio drops near 1.0."""
    try:
        profile = await mteam.get_profile()
        if not profile or not profile['ratio']:
            return

        ratio = profile['ratio']

        # Level 1: ratio < 1.2 → warning + pause non-seed downloads
        if ratio < 1.2:
            # Pause all non-seed downloading torrents
            torrents = await qbit.qbit.get_torrents()
            paused = []
            for t in torrents:
                cat = t.get("category", "")
                state = t.get("state", "")
                if cat != "seed" and state in ("downloading", "stalledDL", "metaDL", "forcedDL"):
                    async with qbit.qbit._session() as session:
                        await session.post(
                            f"{config.QBIT_URL}/api/v2/torrents/pause",
                            data={"hashes": t["hash"]},
                        )
                    paused.append(t.get("name", "")[:30])

            msg = (
                f"⚠️ 分享率熔断！\n"
                f"当前分享率: {ratio:.2f}（接近 1.0）\n"
                f"↑{fmt_bytes(profile['uploaded'])} ↓{fmt_bytes(profile['downloaded'])}\n"
            )
            if paused:
                msg += f"\n已暂停 {len(paused)} 个非养号下载:\n"
                msg += "\n".join(f"  • {n}" for n in paused)
            msg += "\n\n分享率恢复到 1.5 以上后会自动恢复下载"
            await _send(msg)

        # Level 2: ratio < 0.5 → critical alert
        elif ratio < 0.5:
            await _send(
                f"🚨 分享率危险！\n"
                f"当前分享率: {ratio:.2f}\n"
                f"低于 0.3 将被封号！"
            )

        # Auto-resume: ratio recovered above 1.5
        elif ratio > 1.5:
            torrents = await qbit.qbit.get_torrents()
            resumed = []
            for t in torrents:
                cat = t.get("category", "")
                state = t.get("state", "")
                if cat != "seed" and state == "pausedDL":
                    async with qbit.qbit._session() as session:
                        await session.post(
                            f"{config.QBIT_URL}/api/v2/torrents/resume",
                            data={"hashes": t["hash"]},
                        )
                    resumed.append(t.get("name", "")[:30])
            if resumed:
                await _send(
                    f"✅ 分享率恢复 ({ratio:.2f})，已恢复 {len(resumed)} 个下载"
                )
    except Exception as e:
        log.error("Ratio alert error: %s", e)


def setup_scheduler(bot, chat_id: str) -> AsyncIOScheduler:
    """Set up all scheduled jobs."""
    global _bot, _chat_id
    _bot = bot
    _chat_id = chat_id

    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    scheduler.add_job(farm_scan_job, "interval", minutes=config.FARM_SCAN_INTERVAL, id="farm_scan")
    scheduler.add_job(ratio_protect_job, "interval", minutes=5, id="ratio_protect")
    scheduler.add_job(download_monitor_job, "interval", minutes=2, id="download_monitor")
    scheduler.add_job(wishlist_sync_job, "interval", minutes=10, id="wishlist_sync")
    scheduler.add_job(daily_report_job, "cron", hour=9, minute=0, id="daily_report")
    scheduler.add_job(ratio_alert_job, "interval", minutes=10, id="ratio_alert")

    return scheduler
