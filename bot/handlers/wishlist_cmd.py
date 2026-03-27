"""Wishlist command handlers."""

import asyncio
import logging

from services import mteam, radarr, sonarr, wishlist
from telegram import Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)


async def wishlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wishlist command."""
    args = context.args or []
    sub = args[0] if args else "summary"

    if sub == "add":
        # /wishlist add movie 盗梦空间  or  /wishlist add tv 三体
        if len(args) < 3:
            await update.message.reply_text("用法: /wishlist add movie 电影名\n       /wishlist add tv 剧名")
            return
        media_type = args[1]  # "movie" or "tv"
        title = " ".join(args[2:])

        if media_type == "movie":
            results = await radarr.search_movie(title)
            if results:
                r = results[0]
                existing = wishlist.find("movies", r["title"], r["year"])
                if existing:
                    await update.message.reply_text(
                        f"「{r['title']} ({r['year']})」已在队列中\n状态: {existing['status']}")
                    return
                wishlist.add_movie(title=r["title"], year=r["year"], tmdb_id=r["tmdb_id"], source="wishlist_add")
                pending = len(wishlist.get_pending("movies"))
                await update.message.reply_text(
                    f"📋 已加入队列: {r['title']} ({r['year']})\n"
                    f"待下载: {pending} 部\n"
                    f"用 /wishlist start 批量下载"
                )
            else:
                wishlist.add_movie(title=title, source="wishlist_add")
                await update.message.reply_text(f"📋 已加入队列: {title}\n⚠️ 未匹配到 TMDB，标题可能需要调整")

        elif media_type == "tv":
            results = await sonarr.search_series(title)
            if results:
                r = results[0]
                existing = wishlist.find("tv", r["title"], r["year"])
                if existing:
                    await update.message.reply_text(
                        f"「{r['title']} ({r['year']})」已在队列中\n状态: {existing['status']}")
                    return
                wishlist.add_tv(title=r["title"], year=r["year"], tvdb_id=r["tvdb_id"], source="wishlist_add")
                pending = len(wishlist.get_pending("tv"))
                await update.message.reply_text(
                    f"📋 已加入队列: {r['title']} ({r['year']}) {r['season_count']}季\n"
                    f"待下载: {pending} 部\n"
                    f"用 /wishlist start-tv 批量下载"
                )
            else:
                wishlist.add_tv(title=title, source="wishlist_add")
                await update.message.reply_text(f"📋 已加入队列: {title}\n⚠️ 未匹配到 TVDB")
        else:
            await update.message.reply_text("类型只支持 movie 或 tv")
        return

    elif sub == "summary":
        summary = wishlist.get_summary()
        m = summary["movies"]
        t = summary["tv"]
        m_total = sum(m.values())
        t_total = sum(t.values())

        text = "📋 下载队列\n\n"
        text += f"🎬 电影 ({m_total})\n"
        for status in ("pending", "searching", "downloading", "completed", "failed"):
            count = m.get(status, 0)
            if count:
                icon = {"pending": "⏳", "searching": "🔍", "downloading": "⬇️", "completed": "✅", "failed": "❌"}[status]
                text += f"  {icon} {status}: {count}\n"

        text += f"\n📺 剧集 ({t_total})\n"
        if t_total:
            for status in ("pending", "searching", "downloading", "completed", "failed"):
                count = t.get(status, 0)
                if count:
                    icon = {"pending": "⏳", "searching": "🔍", "downloading": "⬇️", "completed": "✅", "failed": "❌"}[status]
                    text += f"  {icon} {status}: {count}\n"
        else:
            text += "  无\n"

        await update.message.reply_text(text)

    elif sub == "list":
        # Show ALL items grouped by status
        media_type = args[1] if len(args) > 1 else "movies"
        all_items = wishlist.get_all(media_type)
        if not all_items:
            await update.message.reply_text(f"队列为空")
            return

        icon_map = {"pending": "⏳", "searching": "🔍", "downloading": "⬇️", "completed": "✅", "failed": "❌"}
        grouped = {}
        for m in all_items:
            s = m.get("status", "pending")
            grouped.setdefault(s, []).append(m)

        lines = [f"📋 {media_type} 完整列表 ({len(all_items)}):\n"]
        for status in ("downloading", "searching", "pending", "completed", "failed"):
            items = grouped.get(status, [])
            if not items:
                continue
            icon = icon_map.get(status, "")
            lines.append(f"\n{icon} {status} ({len(items)}):")
            for m in items:
                year = f" ({m['year']})" if m.get('year') else ""
                lines.append(f"  {m['title']}{year}")

        # Split into chunks for Telegram message limit
        text = "\n".join(lines)
        for i in range(0, len(text), 4000):
            await update.message.reply_text(text[i:i+4000])

    elif sub == "start":
        limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 5
        await update.message.reply_text(f"🚀 开始批量下载 (每次 {limit} 部)...")

        pending_movies = wishlist.get_pending("movies")[:limit]
        added = []
        failed = []

        for m in pending_movies:
            title = m["title"]
            year = m.get("year", 0)
            tmdb_id = m.get("tmdb_id", 0)

            wishlist.update_status("movies", title, "searching", year)

            # Search if no tmdb_id
            if not tmdb_id:
                search_term = f"{title} {year}" if year else title
                results = await radarr.search_movie(search_term)
                if results:
                    tmdb_id = results[0]["tmdb_id"]

            if tmdb_id:
                result = await radarr.add_movie(tmdb_id)
                if result:
                    wishlist.update_status("movies", title, "downloading", year)
                    added.append(f"{title} ({year})")
                else:
                    wishlist.update_status("movies", title, "failed", year)
                    failed.append(f"{title} ({year})")
            else:
                wishlist.update_status("movies", title, "failed", year)
                failed.append(f"{title} ({year}) — 未找到")

            # Small delay to avoid API rate limits
            await asyncio.sleep(1)

        lines = ["📋 批量下载结果\n"]
        if added:
            lines.append(f"✅ 成功 ({len(added)}):")
            for name in added:
                lines.append(f"  • {name}")
        if failed:
            lines.append(f"\n❌ 失败 ({len(failed)}):")
            for name in failed:
                lines.append(f"  • {name}")

        remaining = len(wishlist.get_pending("movies"))
        lines.append(f"\n⏳ 剩余待下载: {remaining} 部")

        await update.message.reply_text("\n".join(lines))

    elif sub == "start-tv":
        limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 3
        await update.message.reply_text(f"🚀 开始批量下载剧集 (每次 {limit} 部)...")

        pending_tv = wishlist.get_pending("tv")[:limit]
        added = []
        failed = []

        for s in pending_tv:
            title = s["title"]
            year = s.get("year", 0)
            tvdb_id = s.get("tvdb_id", 0)

            wishlist.update_status("tv", title, "searching", year)

            if not tvdb_id:
                results = await sonarr.search_series(title)
                if results:
                    tvdb_id = results[0]["tvdb_id"]

            if tvdb_id:
                result = await sonarr.add_series(tvdb_id)
                if result:
                    wishlist.update_status("tv", title, "downloading", year)
                    added.append(f"{title} ({year})")
                else:
                    wishlist.update_status("tv", title, "failed", year)
                    failed.append(f"{title} ({year})")
            else:
                wishlist.update_status("tv", title, "failed", year)
                failed.append(f"{title} ({year}) — 未找到")

            await asyncio.sleep(1)

        lines = ["📋 批量下载剧集结果\n"]
        if added:
            lines.append(f"✅ 成功 ({len(added)}):")
            for name in added:
                lines.append(f"  • {name}")
        if failed:
            lines.append(f"\n❌ 失败 ({len(failed)}):")
            for name in failed:
                lines.append(f"  • {name}")

        await update.message.reply_text("\n".join(lines))

    else:
        await update.message.reply_text(
            "用法:\n"
            "/wishlist — 队列摘要\n"
            "/wishlist add movie 片名 — 加入电影队列（不下载）\n"
            "/wishlist add tv 剧名 — 加入剧集队列（不下载）\n"
            "/wishlist list — 查看待下载电影\n"
            "/wishlist list tv — 查看待下载剧集\n"
            "/wishlist start [N] — 批量下载 N 部电影 (默认5)\n"
            "/wishlist start-tv [N] — 批量下载 N 部剧集 (默认3)"
        )
