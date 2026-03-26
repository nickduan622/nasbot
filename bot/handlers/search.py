"""Search and download command handlers — unified through wishlist."""

import logging

from services import mteam, radarr, sonarr, wishlist
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler

log = logging.getLogger(__name__)

PICK_RESULT = 1


async def movie_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /movie <name> — search, add to wishlist, trigger download."""
    if not context.args:
        await update.message.reply_text("用法: /movie 电影名称\n例如: /movie 盗梦空间")
        return ConversationHandler.END

    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 搜索电影: {query}...")

    results = await radarr.search_movie(query)
    if not results:
        await update.message.reply_text("❌ 没有找到匹配的电影")
        return ConversationHandler.END

    context.user_data["search_results"] = results
    context.user_data["search_type"] = "movie"

    buttons = []
    for i, m in enumerate(results[:5]):
        label = f"{m['title']} ({m['year']})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"pick_{i}")])
    buttons.append([InlineKeyboardButton("❌ 取消", callback_data="pick_cancel")])

    await update.message.reply_text(
        "找到以下结果，请选择：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return PICK_RESULT


async def tv_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tv <name> — search, add to wishlist, trigger download."""
    if not context.args:
        await update.message.reply_text("用法: /tv 剧名\n例如: /tv 三体")
        return ConversationHandler.END

    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 搜索剧集: {query}...")

    results = await sonarr.search_series(query)
    if not results:
        await update.message.reply_text("❌ 没有找到匹配的剧集")
        return ConversationHandler.END

    context.user_data["search_results"] = results
    context.user_data["search_type"] = "tv"

    buttons = []
    for i, s in enumerate(results[:5]):
        label = f"{s['title']} ({s['year']}) - {s['season_count']}季"
        buttons.append([InlineKeyboardButton(label, callback_data=f"pick_{i}")])
    buttons.append([InlineKeyboardButton("❌ 取消", callback_data="pick_cancel")])

    await update.message.reply_text(
        "找到以下结果，请选择：",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return PICK_RESULT


async def pick_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle result selection callback."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "pick_cancel":
        await query.edit_message_text("已取消")
        return ConversationHandler.END

    idx = int(data.split("_")[1]) if "_" in data else -1
    results = context.user_data.get("search_results", [])
    search_type = context.user_data.get("search_type")

    if idx < 0 or idx >= len(results):
        await query.edit_message_text("选择无效")
        return ConversationHandler.END

    item = results[idx]

    # Ratio safety check before downloading
    profile = await mteam.get_profile()
    ratio_safe = True
    if profile and profile["downloaded"] > 0:
        # Estimate: a typical movie ~20GB, TV season ~50GB
        est_size = 50 * 1024 ** 3 if search_type == "tv" else 20 * 1024 ** 3
        projected_ratio = profile["uploaded"] / (profile["downloaded"] + est_size)
        if projected_ratio < 1.0:
            ratio_safe = False

    if search_type == "movie":
        wishlist.add_movie(
            title=item["title"],
            year=item["year"],
            tmdb_id=item["tmdb_id"],
            source="bot_search",
        )

        if not ratio_safe:
            current_ratio = f"{profile['ratio']:.2f}" if profile else "?"
            await query.edit_message_text(
                f"⚠️ 分享率保护！\n"
                f"「{item['title']} ({item['year']})」已加入队列但未下载\n"
                f"当前分享率: {current_ratio}，下载后可能低于 1.0\n"
                f"建议等 Free 活动期间用 /wishlist start 下载"
            )
            return ConversationHandler.END

        await query.edit_message_text(
            f"✅ 「{item['title']} ({item['year']})」已加入队列\n"
            f"⏳ 正在搜索最佳资源..."
        )

        result = await radarr.add_movie(item["tmdb_id"])
        if result:
            wishlist.update_status("movies", item["title"], "downloading", item["year"])
            await query.edit_message_text(
                f"✅ 「{item['title']} ({item['year']})」已开始搜索下载\n"
                f"质量目标: Bluray-2160p > Bluray-1080p\n"
                f"用 /downloads 查看进度"
            )
        else:
            wishlist.update_status("movies", item["title"], "failed", item["year"])
            await query.edit_message_text(f"⚠️ 添加失败，可能已存在或配置问题")

    elif search_type == "tv":
        wishlist.add_tv(
            title=item["title"],
            year=item["year"],
            tvdb_id=item["tvdb_id"],
            source="bot_search",
        )

        if not ratio_safe:
            current_ratio = f"{profile['ratio']:.2f}" if profile else "?"
            await query.edit_message_text(
                f"⚠️ 分享率保护！\n"
                f"「{item['title']} ({item['year']})」已加入队列但未下载\n"
                f"当前分享率: {current_ratio}，下载后可能低于 1.0\n"
                f"建议等 Free 活动期间用 /wishlist start-tv 下载"
            )
            return ConversationHandler.END

        await query.edit_message_text(
            f"✅ 「{item['title']} ({item['year']})」已加入下载队列\n"
            f"⏳ 正在搜索所有剧集..."
        )

        result = await sonarr.add_series(item["tvdb_id"])
        if result:
            wishlist.update_status("tv", item["title"], "downloading", item["year"])
            await query.edit_message_text(
                f"✅ 「{item['title']} ({item['year']})」全{item['season_count']}季已开始下载\n"
                f"用 /downloads 查看进度"
            )
        else:
            wishlist.update_status("tv", item["title"], "failed", item["year"])
            await query.edit_message_text(f"⚠️ 添加失败，可能已存在或配置问题")

    return ConversationHandler.END


def get_search_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("movie", movie_cmd),
            CommandHandler("tv", tv_cmd),
        ],
        states={
            PICK_RESULT: [CallbackQueryHandler(pick_result, pattern=r"^pick_")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        per_message=False,
    )
