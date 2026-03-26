"""NAS PT Media Bot — Telegram bot for media management."""

import logging
import os
import sys

from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler

import config
from handlers.search import get_search_handler
from handlers.status import status_cmd, ratio_cmd, downloads_cmd
from handlers.farm import farm_cmd
from handlers.admin import update_cmd
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("nasbot")


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
        "/farm scan — 立即扫描 Free 种子\n"
        "/farm audit — 检查清理不合适种子\n"
        "/farm cleanup — 清理已达标种子\n"
        "/update — 远程更新 Bot 代码\n"
        "/help — 显示此帮助"
    )


async def help_cmd(update: Update, context):
    await start_cmd(update, context)


async def post_init(app):
    """Run after bot initialization — set up scheduler and commands."""
    # Auto-detect chat ID from first message if not configured
    if not config.TG_CHAT_ID:
        log.warning("TG_CHAT_ID not set — will use first message sender as chat ID")

    # Set bot commands for Telegram menu
    await app.bot.set_my_commands([
        BotCommand("movie", "搜索下载电影"),
        BotCommand("tv", "搜索下载剧集"),
        BotCommand("status", "综合状态面板"),
        BotCommand("downloads", "当前下载详情"),
        BotCommand("ratio", "M-Team 账户详情"),
        BotCommand("farm", "养号管理"),
        BotCommand("update", "远程更新 Bot"),
        BotCommand("help", "帮助"),
    ])

    # Set up scheduler and send startup notification
    chat_id = config.TG_CHAT_ID
    if chat_id:
        scheduler = setup_scheduler(app.bot, chat_id)
        scheduler.start()
        try:
            await app.bot.send_message(chat_id=chat_id, text="✅ Bot 已上线，所有服务正常运行")
        except Exception:
            pass
        log.info("Scheduler started with chat_id=%s", chat_id)
    else:
        log.warning("Scheduler not started — TG_CHAT_ID not configured")


async def any_message(update: Update, context):
    """Capture chat ID from any message if not configured."""
    if not config.TG_CHAT_ID and update.effective_chat:
        chat_id = str(update.effective_chat.id)
        config.TG_CHAT_ID = chat_id
        # Save to file for persistence
        os.makedirs(config.DATA_DIR, exist_ok=True)
        with open(os.path.join(config.DATA_DIR, "chat_id"), "w") as f:
            f.write(chat_id)
        log.info("Auto-detected chat_id: %s", chat_id)
        # Start scheduler now
        scheduler = setup_scheduler(context.bot, chat_id)
        scheduler.start()
        await update.message.reply_text(f"✅ 已记录你的 Chat ID: {chat_id}\n调度器已启动！")


def main():
    # Try to load saved chat_id
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

    # Command handlers
    app.add_handler(get_search_handler())
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("ratio", ratio_cmd))
    app.add_handler(CommandHandler("downloads", downloads_cmd))
    app.add_handler(CommandHandler("farm", farm_cmd))
    app.add_handler(CommandHandler("update", update_cmd))

    # Fallback to capture chat ID
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.ALL, any_message), group=1)

    log.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
