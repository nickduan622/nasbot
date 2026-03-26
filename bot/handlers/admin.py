"""Admin command handlers: update, restart."""

import asyncio
import logging
import os
import subprocess

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
            await update.message.reply_text(
                "✅ 代码已更新，Bot 将在 3 秒后重启..."
            )
            # Give time for message to send, then exit.
            # Docker restart policy will restart the container.
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
        work_dir = "/tmp/nasbot_update"
        app_dir = "/app"

        # Clean up any previous attempt
        subprocess.run(["rm", "-rf", work_dir], check=True)
        os.makedirs(work_dir, exist_ok=True)

        # Download and extract
        proc = subprocess.run(
            ["wget", "-qO-", MIRROR],
            capture_output=True, timeout=60,
        )
        if proc.returncode != 0:
            return {"ok": False, "error": f"wget failed: {proc.stderr.decode()[:200]}"}

        # Extract tar
        proc2 = subprocess.run(
            ["tar", "xz", "--strip-components=2", "-C", work_dir],
            input=proc.stdout, capture_output=True, timeout=30,
        )
        if proc2.returncode != 0:
            return {"ok": False, "error": f"tar failed: {proc2.stderr.decode()[:200]}"}

        # Replace files (but keep data/)
        for item in os.listdir(work_dir):
            src = os.path.join(work_dir, item)
            dst = os.path.join(app_dir, item)
            if item == "data":
                continue  # Don't touch persistent data
            if os.path.isdir(dst):
                subprocess.run(["rm", "-rf", dst], check=True)
            subprocess.run(["cp", "-r", src, dst], check=True)

        subprocess.run(["rm", "-rf", work_dir], check=True)
        return {"ok": True}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "下载超时"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
