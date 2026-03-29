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
                in_library = await radarr.find_in_library(r["title"], r["year"])
                if in_library and in_library.get("has_file"):
                    await update.message.reply_text(f"✅ 「{r['title']} ({r['year']})」已在影音库中，无需添加")
                    return
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
                in_library = await sonarr.find_in_library(r["title"], r["year"])
                if in_library and in_library.get("has_episodes"):
                    await update.message.reply_text(f"✅ 「{r['title']} ({r['year']})」已在影音库中，无需添加")
                    return
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

    elif sub == "delete":
        if len(args) < 2:
            await update.message.reply_text("用法: /wishlist delete <片名>")
            return
        title_query = " ".join(args[1:]).lower()

        # Search both movies and tv
        matches = []
        for item in wishlist.get_all("movies"):
            if title_query in item["title"].lower():
                matches.append(("movies", item))
        for item in wishlist.get_all("tv"):
            if title_query in item["title"].lower():
                matches.append(("tv", item))

        # If no direct match, try Radarr/Sonarr to translate Chinese
        if not matches:
            results = await radarr.search_movie(title_query)
            if results:
                for r in results[:3]:
                    for item in wishlist.get_all("movies"):
                        if r["title"].lower() == item["title"].lower():
                            matches.append(("movies", item))
            if not matches:
                results = await sonarr.search_series(title_query)
                if results:
                    for r in results[:3]:
                        for item in wishlist.get_all("tv"):
                            if r["title"].lower() == item["title"].lower():
                                matches.append(("tv", item))

        if not matches:
            await update.message.reply_text(f"队列中没有匹配「{title_query}」的项目")
            return

        if len(matches) == 1:
            mt, item = matches[0]
            title, year = item["title"], item.get("year", 0)
            # Store for confirmation callback
            context.user_data["wishlist_delete_item"] = (mt, title, year)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            await update.message.reply_text(
                f"确认删除？\n{item['title']} ({year}) [{item.get('status', 'pending')}]",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ 确认删除", callback_data="wl_delete_yes"),
                     InlineKeyboardButton("❌ 取消", callback_data="wl_delete_no")],
                ]),
            )
        else:
            lines = [f"匹配到 {len(matches)} 个，请用更精确的名称："]
            for mt, item in matches[:10]:
                lines.append(f"  • {item['title']} ({item.get('year', '')}) [{mt}]")
            await update.message.reply_text("\n".join(lines))
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
        if len(args) < 2:
            await update.message.reply_text(
                "用法:\n"
                "/wishlist start movie [N] — 批量下载 N 部电影\n"
                "/wishlist start tv [N] — 批量下载 N 部剧集\n"
                "/wishlist start <片名> — 下载队列中指定的一部")
            return

        target = args[1]

        # /wishlist start movie [N]
        if target == "movie":
            limit = int(args[2]) if len(args) > 2 and args[2].isdigit() else 5
            await _batch_start_movies(update, limit)

        # /wishlist start tv [N]
        elif target == "tv":
            limit = int(args[2]) if len(args) > 2 and args[2].isdigit() else 3
            await _batch_start_tv(update, limit)

        # /wishlist start <title>
        else:
            title_query = " ".join(args[1:]).lower()

            # Search wishlist by title (English)
            found = None
            found_type = None
            for item in wishlist.get_pending("movies"):
                if title_query in item["title"].lower():
                    found = item
                    found_type = "movies"
                    break
            if not found:
                for item in wishlist.get_pending("tv"):
                    if title_query in item["title"].lower():
                        found = item
                        found_type = "tv"
                        break

            # If not found, try Chinese → English via Radarr/Sonarr search
            if not found:
                results = await radarr.search_movie(title_query)
                if results:
                    eng_title = results[0]["title"].lower()
                    for item in wishlist.get_pending("movies"):
                        if eng_title in item["title"].lower() or item["title"].lower() in eng_title:
                            found = item
                            found_type = "movies"
                            break
            if not found:
                results = await sonarr.search_series(title_query)
                if results:
                    eng_title = results[0]["title"].lower()
                    for item in wishlist.get_pending("tv"):
                        if eng_title in item["title"].lower() or item["title"].lower() in eng_title:
                            found = item
                            found_type = "tv"
                            break

            if not found:
                await update.message.reply_text(f"队列中没有匹配「{title_query}」的待下载项")
                return

            # Confirm before downloading
            title = found["title"]
            year = found.get("year", 0)
            context.user_data["wishlist_start_item"] = found
            context.user_data["wishlist_start_type"] = found_type

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            buttons = [
                [InlineKeyboardButton(f"✅ 下载 {title} ({year})", callback_data="wl_confirm_yes")],
                [InlineKeyboardButton("❌ 取消", callback_data="wl_confirm_no")],
            ]
            await update.message.reply_text(
                f"找到: {title} ({year}) [{found_type}]\n确认下载？",
                reply_markup=InlineKeyboardMarkup(buttons),
            )

    else:
        await update.message.reply_text(
            "用法:\n"
            "/wishlist — 队列摘要\n"
            "/wishlist add movie <片名> — 加入电影队列\n"
            "/wishlist add tv <剧名> — 加入剧集队列\n"
            "/wishlist list — 查看待下载电影\n"
            "/wishlist list tv — 查看待下载剧集\n"
            "/wishlist start movie [N] — 批量下载 N 部电影\n"
            "/wishlist start tv [N] — 批量下载 N 部剧集\n"
            "/wishlist start <片名> — 下载队列中指定的一部\n"
            "/wishlist delete <片名> — 从队列中删除"
        )


async def _batch_start_movies(update: Update, limit: int):
    await update.message.reply_text(f"🚀 批量下载电影 (最多 {limit} 部)...")
    pending = wishlist.get_pending("movies")[:limit]
    added, failed = [], []

    for m in pending:
        title, year = m["title"], m.get("year", 0)
        tmdb_id = m.get("tmdb_id", 0)
        wishlist.update_status("movies", title, "searching", year)

        if not tmdb_id:
            results = await radarr.search_movie(f"{title} {year}" if year else title)
            if results:
                tmdb_id = results[0]["tmdb_id"]

        if tmdb_id and await radarr.add_movie(tmdb_id):
            wishlist.update_status("movies", title, "downloading", year)
            added.append(f"{title} ({year})")
        else:
            wishlist.update_status("movies", title, "failed", year)
            failed.append(f"{title} ({year})")
        await asyncio.sleep(1)

    lines = ["📋 批量下载结果\n"]
    if added:
        lines.append(f"✅ 成功 ({len(added)}):")
        for n in added:
            lines.append(f"  • {n}")
    if failed:
        lines.append(f"\n❌ 失败 ({len(failed)}):")
        for n in failed:
            lines.append(f"  • {n}")
    lines.append(f"\n⏳ 剩余: {len(wishlist.get_pending('movies'))} 部电影")
    await update.message.reply_text("\n".join(lines))


async def _batch_start_tv(update: Update, limit: int):
    await update.message.reply_text(f"🚀 批量下载剧集 (最多 {limit} 部)...")
    pending = wishlist.get_pending("tv")[:limit]
    added, failed = [], []

    for s in pending:
        title, year = s["title"], s.get("year", 0)
        tvdb_id = s.get("tvdb_id", 0)
        wishlist.update_status("tv", title, "searching", year)

        if not tvdb_id:
            results = await sonarr.search_series(title)
            if results:
                tvdb_id = results[0]["tvdb_id"]

        if tvdb_id and await sonarr.add_series(tvdb_id):
            wishlist.update_status("tv", title, "downloading", year)
            added.append(f"{title} ({year})")
        else:
            wishlist.update_status("tv", title, "failed", year)
            failed.append(f"{title} ({year})")
        await asyncio.sleep(1)

    lines = ["📋 批量下载剧集结果\n"]
    if added:
        lines.append(f"✅ 成功 ({len(added)}):")
        for n in added:
            lines.append(f"  • {n}")
    if failed:
        lines.append(f"\n❌ 失败 ({len(failed)}):")
        for n in failed:
            lines.append(f"  • {n}")
    lines.append(f"\n⏳ 剩余: {len(wishlist.get_pending('tv'))} 部剧集")
    await update.message.reply_text("\n".join(lines))


async def wishlist_delete_callback(update: Update, context):
    """Handle delete confirmation."""
    query = update.callback_query
    await query.answer()

    if query.data == "wl_delete_no":
        await query.edit_message_text("已取消")
        return

    item = context.user_data.get("wishlist_delete_item")
    if not item:
        await query.edit_message_text("⚠️ 操作已过期")
        return

    mt, title, year = item
    if wishlist.remove(mt, title, year):
        await query.edit_message_text(f"🗑️ 已删除: {title} ({year})")
    else:
        await query.edit_message_text(f"⚠️ 删除失败，可能已被移除")


async def wishlist_confirm_callback(update: Update, context):
    """Handle confirm/cancel for wishlist start <title>."""
    query = update.callback_query
    await query.answer()

    if query.data == "wl_confirm_no":
        await query.edit_message_text("已取消")
        return

    found = context.user_data.get("wishlist_start_item")
    found_type = context.user_data.get("wishlist_start_type")
    if not found:
        await query.edit_message_text("⚠️ 操作已过期")
        return

    title = found["title"]
    year = found.get("year", 0)

    await query.edit_message_text(f"⏳ 正在下载: {title} ({year})...")

    if found_type == "movies":
        tmdb_id = found.get("tmdb_id", 0)
        if not tmdb_id:
            results = await radarr.search_movie(f"{title} {year}" if year else title)
            if results:
                tmdb_id = results[0]["tmdb_id"]
        if tmdb_id and await radarr.add_movie(tmdb_id):
            wishlist.update_status("movies", title, "downloading", year)
            await query.edit_message_text(f"✅ 「{title} ({year})」已开始下载\n用 /downloads 查看进度")
        else:
            wishlist.update_status("movies", title, "failed", year)
            await query.edit_message_text(f"❌ 下载失败")
    else:
        tvdb_id = found.get("tvdb_id", 0)
        if not tvdb_id:
            results = await sonarr.search_series(title)
            if results:
                tvdb_id = results[0]["tvdb_id"]
        if tvdb_id and await sonarr.add_series(tvdb_id):
            wishlist.update_status("tv", title, "downloading", year)
            await query.edit_message_text(f"✅ 「{title} ({year})」已开始下载\n用 /downloads 查看进度")
        else:
            wishlist.update_status("tv", title, "failed", year)
            await query.edit_message_text(f"❌ 下载失败")
