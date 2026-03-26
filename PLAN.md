# 项目状态 & 后续 TODO

> 上次更新: 2026-03-26

## 当前状态

### 已完成
- [x] Docker Compose 部署 8 个服务 (qBit, Prowlarr, Radarr, Sonarr, ChineseSubFinder, FlareSolverr, Clash, nasbot)
- [x] qBittorrent PT 优化配置 (关 DHT/PeX/LSD/匿名, 端口 55000)
- [x] Prowlarr → M-Team 索引器 + 同步到 Radarr/Sonarr
- [x] Radarr/Sonarr 下载客户端 + 根目录 + 质量策略 (4K > 1080p)
- [x] Clash 代理 (仅 Telegram 流量)
- [x] Telegram Bot 核心: /movie, /tv, /status, /ratio, /downloads, /farm, /update
- [x] 自动养号: 扫描 Free 种子 → 下载 → 做种 → 保护 → 清理 → 轮换
- [x] 分享率保护: 每 5 分钟检查, Free 过期未下完自动删除
- [x] 生命周期通知: 有变更时推送, 下载完成通知, 日报, 分享率预警
- [x] GitHub 仓库 + /update 远程自更新 + update.sh (ghfast.top 镜像)
- [x] M-Team 账号注册 (bignickeye, 2026-03-25), 2FA 已开
- [x] 代码审查 & 清理 (统一 fmt_bytes, 修复调度器双启动, context.bot)
- [x] 端口转发已设置 (55000 TCP/UDP) — 但因 CGNAT 无效
- [x] 旧资源盘点完成 (docs/migration-plan.md)

### 运行中
- 自动养号 Bot 24/7 运行中, 每 15 分钟扫描, 上限 25 种子 / 500GB
- CGNAT 优化策略: 智能排序 leechers/(seeders+1), 2h 零上传轮换
- M-Team 新手考核中 (截止 ~2026-04-22), 条件三选一: 上传 > 20GB / 下载 > 15GB / 魔力值 > 4500
- 当前: 分享率 5.56, 上传 ~37GB (已过考核线)

### 已知限制
- CGNAT (中国移动内网 IP 100.99.x.x), 端口转发无效, 上传速度受限
- 可尝试: 打 10086 要公网 IPv4, 或使用 IPv6

## 后续 TODO

### 紧急：3/31 前必须完成（为 4/1 活动做准备）
- [ ] 测试 `/movie` 搜索下载电影 (端到端)
- [ ] 测试 `/tv` 搜索下载剧集 (端到端)
- [ ] 测试 `/status` 综合面板
- [ ] 配置 ChineseSubFinder (`http://192.168.1.187:19035`)
- [ ] 绿联影视中心绑定 `/volume1/Media-PT/movies` 和 `/volume1/Media-PT/tv`
- [ ] 端到端验证: TG 发名字 → 下载 → 字幕匹配 → 影视中心可播放

### 4/1 全站 Free 活动计划（关键！详见 docs/migration-plan.md）

**时间线:**
- **3/31 晚**: 确认 /movie 能用, 准备好片单
- **4/1 00:00**: 活动开始, 批量添加 Temp 老片升级 4K
- **4/1 - 4/3**: 持续下载 (Free 不扣下载量, 上传照常计 = 纯赚 ratio)
- **4/3 之后**: 做种冲上传量

**下载优先级:**
1. 你最想看但还没有的新片
2. Temp 里的经典片升级 4K (~100 部, 通过 /movie 批量添加)
3. Download 里少量需升级的 (Cloud Atlas, Zootopia 2 等)

**活动前临时调参:**
- `FARM_ENABLED=false` (暂停养号, 把带宽让给正片下载)
- 或 `FARM_MAX_TORRENTS=10` (缩小养号, 留大部分带宽)

### 4/1 之后：旧资源迁移
- [ ] Download 里的高清资源 → Radarr/Sonarr Manual Import → 重命名整理到新库
- [ ] Download 里的剧集分类导入 Sonarr
- [ ] Temp 里已有 4K 新版本的 → 删除旧低清文件
- [ ] Movies 里的 6 部 → 导入新库
- [ ] 编写/使用迁移辅助脚本

### 中优先级
- [ ] 尝试打 10086 要公网 IPv4（提升做种上传）
- [ ] 养号策略持续观察调优

### 低优先级
- [ ] Radarr/Sonarr 非 Free 下载时的分享率保护
- [ ] 部署 Jellyfin/Emby 替代绿联影视中心
- [ ] cross-seed 跨站做种

## 旧资源概况

| 位置 | 大小 | 内容 | 质量 |
|------|------|------|------|
| /Media/Download/ | 2.3TB | 56项, 电影+剧集混放 | ⭐⭐⭐ 大部分 4K/1080p |
| /Media/Movies/ | 188GB | 6 部已整理电影 | ⭐⭐⭐ 高 |
| /Media/Temp/Movies/ | ~380GB | ~100 部经典老片按类型分 | ⭐~⭐⭐ 720p/rmvb 低清 |
| /Media/Temp/Series/ | 空 | - | - |
| /Media-PT/ | 500GB | 养号种子 | 不管 |

> 详细清单见 docs/migration-plan.md

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
| CGNAT | 是 (100.99.x.x), 端口转发无效 |
