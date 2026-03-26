"""Admin command handlers: update, restart."""

import io
import logging
import os
import shutil
import tarfile
import urllib.request

import asyncio
from telegram import Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)

MIRROR = "https://ghfast.top/https://github.com/nickduan622/nasbot/archive/refs/heads/main.tar.gz"


async def update_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /update — pull latest code from GitHub and restart bot."""
    await update.message.reply_text("⬇️ 正在从 GitHub 拉取最新代码...")

    try:
        result = await asyncio.to_thread(_do_update)
        if result["ok"]:
            await update.message.reply_text("✅ 代码已更新，Bot 将在 3 秒后重启...")
            await asyncio.sleep(3)
            os._exit(0)
        else:
            await update.message.reply_text(f"❌ 更新失败:\n{result['error']}")
    except Exception as e:
        log.error("Update error: %s", e, exc_info=True)
        await update.message.reply_text(f"❌ 更新异常: {e}")


def _do_update() -> dict:
    """Download latest code from GitHub and replace /app files."""
    try:
        app_dir = "/app"
        extract_dir = "/tmp/nasbot_update"

        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)

        data = urllib.request.urlopen(MIRROR, timeout=60).read()

        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(extract_dir)

        src_dir = os.path.join(extract_dir, "nasbot-main", "bot")

        for item in os.listdir(src_dir):
            src = os.path.join(src_dir, item)
            dst = os.path.join(app_dir, item)
            if item == "data":
                continue
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        shutil.rmtree(extract_dir)
        return {"ok": True}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"下载失败: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
