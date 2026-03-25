#!/bin/bash
# Update nasbot code from GitHub (using mirror for China)
set -e
CODE_DIR="/volume1/docker/my-nas-pt-media/nasbot/code"
MIRROR="https://ghfast.top/https://github.com/nickduan622/nasbot/archive/refs/heads/main.tar.gz"

cd "$CODE_DIR"
rm -rf bot
wget -qO- "$MIRROR" | tar xz
mv nasbot-main/bot .
rm -rf nasbot-main
echo "✅ Bot 代码已更新，请在 Docker UI 重启 nasbot 容器"
