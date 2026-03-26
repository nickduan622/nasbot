"""Wishlist command handlers."""

import asyncio
import logging

from services import wishlist, radarr, sonarr
from telegram import Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)


async def wishlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wishlist command."""
    args = context.args or []
    sub = args[0] if args else "summary"

    if sub == "summary":
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
        # Show pending movies
        media_type = args[1] if len(args) > 1 else "movies"
        items = wishlist.get_pending(media_type)
        if not items:
            await update.message.reply_text(f"没有 pending 的{media_type}")
            return

        # Split into chunks of 50 for Telegram message limit
        chunks = []
        for i in range(0, len(items), 50):
            chunk = items[i:i+50]
            lines = []
            if i == 0:
                lines.append(f"⏳ 待下载 {media_type} ({len(items)}):\n")
            for j, m in enumerate(chunk):
                year = f" ({m['year']})" if m.get('year') else ""
                lines.append(f"{i+j+1}. {m['title']}{year}")
            chunks.append("\n".join(lines))
        for chunk in chunks:
            await update.message.reply_text(chunk)

    elif sub == "start":
        # Batch trigger download for pending items
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
            "/wishlist list — 查看待下载电影\n"
            "/wishlist list tv — 查看待下载剧集\n"
            "/wishlist start [N] — 批量下载 N 部电影 (默认5)\n"
            "/wishlist start-tv [N] — 批量下载 N 部剧集 (默认3)"
        )
