# 项目状态 & 后续 TODO

> 上次更新: 2026-03-26

## 当前状态

### 已完成
- [x] Docker Compose 部署 8 个服务 (qBit, Prowlarr, Radarr, Sonarr, ChineseSubFinder, FlareSolverr, Clash, nasbot)
- [x] qBittorrent PT 优化配置 (关 DHT/PeX/LSD/匿名, 端口 55000)
- [x] Prowlarr → M-Team 索引器 + 同步到 Radarr/Sonarr
- [x] Radarr/Sonarr 下载客户端 + 根目录 + 质量策略 (4K > 1080p)
- [x] Clash 代理 (仅 Telegram 流量)
- [x] Telegram Bot 核心: /movie, /tv, /status, /ratio, /downloads, /farm
- [x] 自动养号: 扫描 Free 种子 → 下载 → 做种 → 保护 → 清理
- [x] 分享率保护: 每 5 分钟检查, Free 过期未下完自动删除
- [x] 生命周期通知: 下载进度/完成/日报/分享率预警
- [x] GitHub 仓库 + 更新脚本 (ghfast.top 镜像)
- [x] M-Team 账号注册 (bignickeye, 2026-03-25), 2FA 已开

### 运行中
- 自动养号 Bot 24/7 运行中, 每 15 分钟扫描, 上限 50 种子 / 500GB
- M-Team 新手考核中 (截止 ~2026-04-22), 条件三选一: 上传 > 20GB / 下载 > 15GB / 魔力值 > 4500
- 4 月 1 日全站 Free 活动 3 天 — 关键养号窗口

## 后续 TODO

### 高优先级 (下次 session)
- [ ] 测试 `/movie` 搜索下载电影 (端到端)
- [ ] 测试 `/tv` 搜索下载剧集 (端到端)
- [ ] 测试 `/status` 综合面板
- [ ] 配置 ChineseSubFinder (`http://NAS_IP:19035`)
- [ ] 绿联影视中心绑定 `/volume1/Media-PT/movies` 和 `/volume1/Media-PT/tv`
- [ ] 端到端验证: TG 发名字 → 下载 → 字幕匹配 → 影视中心可播放

### 中优先级
- [ ] **路由器端口转发 55000** (最大瓶颈! 提升做种上传速度, 中国移动光猫可能需要超级管理员)
- [ ] 端口转发后: 观察上传速度变化, 如仍不理想再启用养号策略优化 (commit e8e4b96 已回退, 内容: 按 leechers/(seeders+1) 排序 + 3h零上传自动淘汰 + 必须有seeder)
- [ ] 旧资源迁移脚本 (从 `/volume1/Media/Movies` 迁移到新库, 重命名+字幕)

### 低优先级 / 后续增强
- [ ] 4 月 1 日全站 Free 活动策略 (可能需要临时调大参数)
- [ ] Radarr/Sonarr 下载时的分享率保护 (非 Free 种子风险)
- [ ] 部署 Jellyfin/Emby 替代绿联影视中心
- [ ] cross-seed 跨站做种 (如果有多个 PT 站)

## 关键配置速查

| 项目 | 值 |
|------|-----|
| NAS IP | 192.168.1.187 |
| Docker 项目 | my-nas-pt-media |
| Compose 路径 | /volume1/docker/my-nas-pt-media/docker-compose.yaml |
| 媒体根目录 | /volume1/Media-PT/ |
| Bot 代码 | /volume1/docker/my-nas-pt-media/nasbot/code/bot/ |
| Bot .env | /volume1/docker/my-nas-pt-media/nasbot/.env |
| Clash 配置 | /volume1/docker/my-nas-pt-media/clash/config.yaml |
| GitHub | github.com/nickduan622/nasbot |
| 更新脚本 | /volume1/docker/my-nas-pt-media/nasbot/update.sh |
| qBit 端口 | WebUI 8092, BT 55000 |
| M-Team 用户 | bignickeye |
| M-Team 考核截止 | ~2026-04-22 |
