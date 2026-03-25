"""Status command handlers."""

from services import mteam, qbit, radarr, sonarr, farmer
from telegram import Update
from telegram.ext import ContextTypes


def _fmt_bytes(b: int | float) -> str:
    if b >= 1024 ** 4:
        return f"{b / 1024 ** 4:.2f} TB"
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.2f} GB"
    if b >= 1024 ** 2:
        return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024:.0f} KB"


def _progress_bar(pct: float, width: int = 10) -> str:
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status — comprehensive status panel."""
    # M-Team profile
    profile = await mteam.get_profile()
    mt_text = "🌐 *M\\-Team*\n"
    if profile:
        ratio_str = f"{profile['ratio']:.2f}" if profile['ratio'] else "∞"
        mt_text += (
            f"  分享率: {ratio_str}  "
            f"↑{_fmt_bytes(profile['uploaded'])} ↓{_fmt_bytes(profile['downloaded'])}\n"
            f"  魔力值: {profile['bonus']:,.0f}\n"
            f"  做种: {profile['seeding']}  下载: {profile['leeching']}\n"
        )
    else:
        mt_text += "  ⚠️ 无法连接\n"

    # Download queue
    radarr_q = await radarr.get_queue()
    sonarr_q = await sonarr.get_queue()
    all_q = radarr_q + sonarr_q

    dl_text = f"\n⬇️ *下载中* \\({len(all_q)}\\)\n"
    if all_q:
        for item in all_q[:5]:
            bar = _progress_bar(item["progress"])
            dl_text += f"  {item['title'][:30]}\n  {bar} {item['progress']}%\n"
    else:
        dl_text += "  无活动任务\n"

    # Farm status
    farm = await farmer.get_farm_status()
    farm_text = (
        f"\n🌱 *养号*\n"
        f"  做种: {farm['seeding']} 个  "
        f"磁盘: {farm['disk_usage_gb']}/{farm['disk_limit_gb']} GB\n"
        f"  养号上传: {farm['total_uploaded_gb']} GB\n"
    )

    await update.message.reply_text(mt_text + dl_text + farm_text, parse_mode="MarkdownV2")


async def ratio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ratio — M-Team account details."""
    profile = await mteam.get_profile()
    if not profile:
        await update.message.reply_text("⚠️ 无法获取 M-Team 信息")
        return

    ratio_str = f"{profile['ratio']:.2f}" if profile['ratio'] else "∞"
    text = (
        f"🌐 M-Team 账户\n\n"
        f"用户名: {profile['username']}\n"
        f"等级: {profile['user_class']}\n"
        f"分享率: {ratio_str}\n"
        f"上传量: {_fmt_bytes(profile['uploaded'])}\n"
        f"下载量: {_fmt_bytes(profile['downloaded'])}\n"
        f"魔力值: {profile['bonus']:,.0f}\n"
        f"做种数: {profile['seeding']}\n"
        f"下载数: {profile['leeching']}"
    )
    await update.message.reply_text(text)


async def downloads_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /downloads — current download details."""
    torrents = await qbit.qbit.get_torrents()
    active = [t for t in torrents if t.get("state") in (
        "downloading", "stalledDL", "metaDL", "forcedDL",
    )]

    if not active:
        await update.message.reply_text("没有活动下载任务")
        return

    lines = ["⬇️ 当前下载任务:\n"]
    for t in active[:10]:
        progress = t.get("progress", 0) * 100
        bar = _progress_bar(progress)
        speed = _fmt_bytes(t.get("dlspeed", 0))
        name = t.get("name", "")[:40]
        lines.append(f"{name}\n{bar} {progress:.1f}% ↓{speed}/s\n")

    await update.message.reply_text("\n".join(lines))
