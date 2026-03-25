"""Farm command handlers."""

import config
from services import farmer
from telegram import Update
from telegram.ext import ContextTypes


def _fmt_bytes(b: float) -> str:
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.1f} GB"
    if b >= 1024 ** 2:
        return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024:.0f} KB"


async def farm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /farm command."""
    args = context.args or []
    sub = args[0] if args else "status"

    if sub == "status":
        status = await farmer.get_farm_status()
        text = (
            "🌱 *养号状态*\n\n"
            f"做种中: {status['seeding']} 个\n"
            f"下载中: {status['downloading']} 个\n"
            f"总种子: {status['total_torrents']} 个\n\n"
            f"磁盘用量: {status['disk_usage_gb']} / {status['disk_limit_gb']} GB\n"
            f"总上传: {status['total_uploaded_gb']} GB\n"
            f"总下载: {status['total_downloaded_gb']} GB\n\n"
            f"自动养号: {'✅ 开启' if config.FARM_ENABLED else '❌ 关闭'}\n"
            f"扫描间隔: 每 {config.FARM_SCAN_INTERVAL} 分钟"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    elif sub == "scan":
        await update.message.reply_text("🔍 正在扫描 M-Team Free 种子...")
        added = await farmer.scan_and_download()
        if added:
            names = "\n".join(f"  • {n[:60]}" for n in added)
            await update.message.reply_text(f"✅ 新增 {len(added)} 个种子：\n{names}")
        else:
            await update.message.reply_text("没有找到新的合适 Free 种子")

    elif sub == "cleanup":
        cleaned = await farmer.cleanup_completed()
        if cleaned:
            names = "\n".join(f"  • {n[:60]}" for n in cleaned)
            await update.message.reply_text(f"🧹 清理 {len(cleaned)} 个已达标种子：\n{names}")
        else:
            await update.message.reply_text("没有需要清理的种子")

    else:
        await update.message.reply_text(
            "用法:\n"
            "/farm status — 养号状态\n"
            "/farm scan — 立即扫描下载\n"
            "/farm cleanup — 清理已达标种子"
        )
