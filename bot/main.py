"""NAS PT Media Bot — Telegram bot for media management."""

import logging
import os
import sys

from telegram import Update, BotCommand
from telegram.error import NetworkError, TimedOut
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

import config
from handlers.search import get_search_handler
from handlers.status import status_cmd, ratio_cmd, downloads_cmd
from handlers.farm import farm_cmd
from handlers.wishlist_cmd import wishlist_cmd
from handlers.admin import update_cmd
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("nasbot")

_scheduler_started = False


async def start_cmd(update: Update, context):
    await update.message.reply_text(
        "🎬 NAS PT Media Bot\n\n"
        "命令列表:\n"
        "/movie <名称> — 搜索下载电影\n"
        "/tv <名称> — 搜索下载剧集\n"
        "/status — 综合状态面板\n"
        "/downloads — 当前下载详情\n"
        "/ratio — M-Team 账户详情\n"
        "/farm status — 养号状态\n"
        "/farm check — 完整检查（=定时任务）\n"
        "/farm scan — 仅扫描新种子\n"
        "/farm audit — 检查清理不合适种子\n"
        "/farm cleanup — 清理已达标种子\n"
        "/wishlist — 下载队列摘要\n"
        "/wishlist list — 查看待下载列表\n"
        "/wishlist start [N] — 批量下载 N 部电影\n"
        "/update — 远程更新 Bot 代码\n"
        "/help — 显示此帮助"
    )


async def post_init(app):
    """Run after bot initialization — set up scheduler and commands."""
    global _scheduler_started

    if not config.TG_CHAT_ID:
        log.warning("TG_CHAT_ID not set — will use first message sender as chat ID")

    await app.bot.set_my_commands([
        BotCommand("movie", "搜索下载电影"),
        BotCommand("tv", "搜索下载剧集"),
        BotCommand("status", "综合状态面板"),
        BotCommand("downloads", "当前下载详情"),
        BotCommand("ratio", "M-Team 账户详情"),
        BotCommand("farm", "养号管理"),
        BotCommand("wishlist", "下载队列"),
        BotCommand("update", "远程更新 Bot"),
        BotCommand("help", "帮助"),
    ])

    chat_id = config.TG_CHAT_ID
    if chat_id and not _scheduler_started:
        scheduler = setup_scheduler(app.bot, chat_id)
        scheduler.start()
        _scheduler_started = True
        log.info("Scheduler started with chat_id=%s", chat_id)
        try:
            await app.bot.send_message(chat_id=chat_id, text="✅ Bot 已上线，所有服务正常运行")
        except Exception as e:
            log.warning("Failed to send startup message: %s", e)
    elif not chat_id:
        log.warning("Scheduler not started — TG_CHAT_ID not configured")


async def error_handler(update, context):
    """Handle errors — log network issues, don't crash polling."""
    err = context.error
    if isinstance(err, (NetworkError, TimedOut)):
        log.warning("Network error (polling will retry): %s", err)
        return
    log.error("Unhandled exception:", exc_info=context.error)


async def any_message(update: Update, context):
    """Capture chat ID from any message if not configured."""
    global _scheduler_started

    if not config.TG_CHAT_ID and update.effective_chat:
        chat_id = str(update.effective_chat.id)
        config.TG_CHAT_ID = chat_id
        os.makedirs(config.DATA_DIR, exist_ok=True)
        with open(os.path.join(config.DATA_DIR, "chat_id"), "w") as f:
            f.write(chat_id)
        log.info("Auto-detected chat_id: %s", chat_id)

        if not _scheduler_started:
            scheduler = setup_scheduler(context.application.bot, chat_id)
            scheduler.start()
            _scheduler_started = True
            await update.message.reply_text(f"✅ 已记录你的 Chat ID: {chat_id}\n调度器已启动！")


def main():
    chat_id_file = os.path.join(config.DATA_DIR, "chat_id")
    if not config.TG_CHAT_ID and os.path.exists(chat_id_file):
        with open(chat_id_file) as f:
            config.TG_CHAT_ID = f.read().strip()

    log.info("Starting NAS PT Media Bot...")

    builder = ApplicationBuilder().token(config.TG_BOT_TOKEN).post_init(post_init)
    if config.TG_PROXY:
        log.info("Using Telegram proxy: %s", config.TG_PROXY)
        builder = builder.proxy(config.TG_PROXY).get_updates_proxy(config.TG_PROXY)
    app = builder.build()

    app.add_handler(get_search_handler())
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("ratio", ratio_cmd))
    app.add_handler(CommandHandler("downloads", downloads_cmd))
    app.add_handler(CommandHandler("farm", farm_cmd))
    app.add_handler(CommandHandler("wishlist", wishlist_cmd))
    app.add_handler(CommandHandler("update", update_cmd))
    app.add_handler(MessageHandler(filters.ALL, any_message), group=1)
    app.add_error_handler(error_handler)

    log.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        poll_interval=1.0,
    )


if __name__ == "__main__":
    main()
