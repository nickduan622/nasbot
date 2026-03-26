"""Farm command handlers."""

import logging

import config
from services import farmer
from telegram import Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)


async def farm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /farm command."""
    args = context.args or []
    sub = args[0] if args else "status"

    if sub == "status":
        status = await farmer.get_farm_status()
        text = (
            "🌱 养号状态\n\n"
            f"做种中: {status['seeding']} 个\n"
            f"下载中: {status['downloading']} 个\n"
            f"总种子: {status['total_torrents']} 个\n\n"
            f"磁盘用量: {status['disk_usage_gb']} / {status['disk_limit_gb']} GB\n"
            f"总上传: {status['total_uploaded_gb']} GB\n"
            f"总下载: {status['total_downloaded_gb']} GB\n\n"
            f"自动养号: {'✅ 开启' if config.FARM_ENABLED else '❌ 关闭'}\n"
            f"扫描间隔: 每 {config.FARM_SCAN_INTERVAL} 分钟"
        )
        await update.message.reply_text(text)

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

    elif sub == "audit":
        await update.message.reply_text("🔍 正在检查所有养号种子...")
        result = await farmer.audit_seeds()
        text = f"🔍 审计结果\n\n"
        text += f"总种子: {result['total']} 个\n"
        text += f"正常 (Free/做种中): {result['healthy']} 个\n"
        if result['removed']:
            names = "\n".join(f"  • {n[:60]}" for n in result['removed'])
            text += f"\n🗑️ 已删除 {len(result['removed'])} 个不合适种子：\n{names}"
        else:
            text += f"\n✅ 没有需要删除的种子"
        await update.message.reply_text(text)

    elif sub == "check":
        await update.message.reply_text("🔄 执行完整养号检查...")
        lines = ["🌱 手动养号检查"]

        protected = await farmer.protect_ratio()
        if protected:
            for info in protected:
                lines.append(f"  🛡️ {info}")

        added = await farmer.scan_and_download()
        if added:
            for info in added:
                lines.append(f"  ➕ {info}")

        cleaned = await farmer.cleanup_completed()
        if cleaned:
            for info in cleaned:
                lines.append(f"  🗑️ {info}")

        if not protected and not added and not cleaned:
            lines.append("  无变更")

        status = await farmer.get_farm_status()
        lines.append(f"\n📊 {status['seeding']}做种 {status['downloading']}下载 | "
                     f"↑{status['total_uploaded_gb']}GB | "
                     f"磁盘 {status['disk_usage_gb']}/{status['disk_limit_gb']}GB")

        await update.message.reply_text("\n".join(lines))

    else:
        await update.message.reply_text(
            "用法:\n"
            "/farm status — 养号状态\n"
            "/farm check — 完整检查（=定时任务）\n"
            "/farm scan — 仅扫描新种子\n"
            "/farm audit — 检查清理不合适种子\n"
            "/farm cleanup — 清理已达标种子"
        )
