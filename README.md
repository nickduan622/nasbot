# NAS PT Media Bot

全自动影视资源下载管理系统，运行在绿联 NAS (Docker) 上，通过 Telegram Bot 交互。

## 功能

- **Telegram 搜索下载** — 发 `/movie 盗梦空间` 或 `/tv 三体`，自动搜索最佳质量资源并下载
- **自动养号** — 定时扫描 M-Team Free 种子，自动下载做种，维护分享率
- **状态监控** — `/status` 查看下载进度、M-Team 分享率、养号状态
- **生命周期通知** — 下载开始/进度/完成/字幕就绪，自动推送到 Telegram
- **中文字幕** — ChineseSubFinder 自动匹配下载中文字幕
- **质量策略** — 优先 4K Bluray > 1080p Bluray > 1080p WEB，逐级降级

## 架构

```
Telegram Bot ←→ Clash(代理,仅TG流量)
     ↕
Radarr(电影) + Sonarr(剧集) ←→ Prowlarr(索引) ←→ M-Team PT
     ↕
qBittorrent(下载) → ChineseSubFinder(字幕) → 媒体库
```

所有组件 Docker 部署，通过 docker-compose 管理。

## 前置要求

- 绿联 NAS（或其他支持 Docker 的 NAS）
- M-Team 账号 + 存取令牌
- Telegram Bot Token（通过 @BotFather 创建）
- 翻墙代理订阅链接（中国大陆需要，用于 Telegram 连接）

## 目录结构

```
/volume1/Media-PT/                  ← 媒体根目录
├── movies/                         ← 电影库（绑定到影视中心）
├── tv/                             ← 剧集库（绑定到影视中心）
└── downloads/
    ├── movies/                     ← Radarr 下载临时目录
    ├── tv/                         ← Sonarr 下载临时目录
    └── seed/                       ← 养号做种（不进媒体库）

/volume1/docker/my-nas-pt-media/    ← Docker 配置根目录
├── docker-compose.yaml             ← 绿联 Docker 项目 compose 文件
├── qbittorrent/                    ← qBittorrent 配置
├── prowlarr/                       ← Prowlarr 配置
├── radarr/                         ← Radarr 配置
├── sonarr/                         ← Sonarr 配置
├── chinesesubfinder/               ← ChineseSubFinder 配置
├── clash/
│   └── config.yaml                 ← Clash 代理配置（含订阅链接，不进 git）
└── nasbot/
    ├── .env                        ← Bot 环境变量（含密钥，不进 git）
    ├── data/                       ← Bot 运行数据（chat_id、farm state）
    └── code/                       ← Bot 代码（从 GitHub 拉取）
        └── bot/
            ├── main.py
            ├── config.py
            ├── handlers/
            ├── services/
            └── ...
```

## 部署步骤

### 1. 创建 NAS 目录

```bash
# 媒体目录
mkdir -p /volume1/Media-PT/{movies,tv,downloads/movies,downloads/tv,downloads/seed}

# Docker 配置目录
mkdir -p /volume1/docker/my-nas-pt-media/{qbittorrent,prowlarr,radarr,sonarr,chinesesubfinder}
mkdir -p /volume1/docker/my-nas-pt-media/{clash,nasbot/data}
```

### 2. 部署基础服务

在绿联 Docker 管理界面创建项目 `my-nas-pt-media`，存放路径 `/volume1/docker/my-nas-pt-media`，粘贴 `docker-compose-ugos.yml` 的内容（需要补充实际密钥）。

### 3. 配置 Clash 代理（中国大陆）

```bash
cat > /volume1/docker/my-nas-pt-media/clash/config.yaml << 'EOF'
mixed-port: 7890
allow-lan: true
mode: rule
log-level: warning

proxy-providers:
  provider:
    type: http
    url: "<你的代理订阅链接>"
    interval: 86400
    path: ./providers/sub.yaml
    health-check:
      enable: true
      url: https://www.gstatic.com/generate_204
      interval: 300

proxy-groups:
  - name: PROXY
    type: url-test
    use:
      - provider
    url: https://www.gstatic.com/generate_204
    interval: 300

rules:
  - DOMAIN-SUFFIX,telegram.org,PROXY
  - DOMAIN-SUFFIX,t.me,PROXY
  - DOMAIN-SUFFIX,telesco.pe,PROXY
  - DOMAIN-SUFFIX,tg.dev,PROXY
  - DOMAIN,api.telegram.org,PROXY
  - MATCH,DIRECT
EOF
```

只有 Telegram 流量走代理，其他全部直连。

### 4. 下载 Bot 代码

```bash
cd /volume1/docker/my-nas-pt-media/nasbot
wget https://github.com/nickduan622/nasbot/archive/refs/heads/main.tar.gz -O nasbot.tar.gz
tar xzf nasbot.tar.gz && mv nasbot-main code && rm nasbot.tar.gz
```

### 5. 创建 .env 文件

```bash
cat > /volume1/docker/my-nas-pt-media/nasbot/.env << 'EOF'
TG_BOT_TOKEN=<Telegram Bot Token>
TG_PROXY=http://clash:7890
RADARR_URL=http://radarr:7878
RADARR_API_KEY=<Radarr API Key>
SONARR_URL=http://sonarr:8989
SONARR_API_KEY=<Sonarr API Key>
QBIT_URL=http://qbit-pt:8092
QBIT_USER=admin
QBIT_PASS=<qBittorrent 密码>
MT_API_TOKEN=<M-Team 存取令牌>
MT_BASE_URL=https://kp.m-team.cc
FARM_ENABLED=true
FARM_SCAN_INTERVAL=30
FARM_MAX_DISK_GB=500
FARM_SEED_RATIO_TARGET=2.0
FARM_SEED_TIME_TARGET=4320
EOF
```

### 6. 配置各服务

#### qBittorrent (`http://NAS_IP:8092`)
- Downloads > Default Save Path: `/media/downloads`
- BitTorrent: 关闭 DHT、PeX、LSD、匿名模式
- Seeding: ratio 2.0 / time 4320 min → Pause

#### Prowlarr (`http://NAS_IP:9696`)
- Indexers: 添加 M-Team，Base URL `https://kp.m-team.cc`，填入存取令牌
- Settings > Apps: 添加 Radarr (`http://radarr:7878`) 和 Sonarr (`http://sonarr:8989`)
- Settings > Download Clients: 添加 qBittorrent (`qbit-pt:8092`)

#### Radarr (`http://NAS_IP:7878`)
- Settings > Download Clients: qBittorrent, host `qbit-pt`, port 8092, category `radarr`
- Settings > Media Management: Use Hardlinks, Root Folder `/media/movies`
- Settings > Profiles: 优先 Bluray-2160p > WEB-2160p > Bluray-1080p > WEB-1080p

#### Sonarr (`http://NAS_IP:8989`)
- 同 Radarr，category `sonarr`，Root Folder `/media/tv`

#### 绿联影视中心
- 创建新影音库，绑定 `/volume1/Media-PT/movies` 和 `/volume1/Media-PT/tv`

### 7. 部署完成后

在 Telegram 中搜索你的 Bot，发送 `/start`，Bot 会自动记录你的 Chat ID 并启动调度器。

## Bot 命令

| 命令 | 说明 |
|------|------|
| `/movie <名称>` | 搜索下载电影 |
| `/tv <名称>` | 搜索下载剧集 |
| `/status` | 综合状态面板 |
| `/downloads` | 当前下载详情 |
| `/ratio` | M-Team 账户详情 |
| `/farm status` | 养号状态 |
| `/farm scan` | 立即扫描 Free 种子 |
| `/farm cleanup` | 清理已达标种子 |

## 更新 Bot 代码

```bash
/volume1/docker/my-nas-pt-media/nasbot/update.sh
# 然后在绿联 Docker UI 重启 nasbot 容器
```

> update.sh 使用 ghfast.top 镜像加速 GitHub 下载 (中国大陆)

## M-Team 养号策略

- **28 天新手考核**：上传 > 20GB / 下载 > 15GB / 魔力值 > 4500（三选一）
- **分享率红线**：下载超 10GB 后，分享率 < 0.3 = 封号
- **自动养号**：Bot 每 30 分钟扫描 Free 种子，自动下载做种到 `/media/downloads/seed/`
- **全站 Free 活动**：关注 M-Team 公告，活动期间大量下载刷上传量
- **日报推送**：每日 9:00 自动推送分享率、魔力值、做种状态

## 注意事项

- `.env` 和 `clash/config.yaml` 包含密钥和订阅链接，**不要提交到 git**
- qBittorrent PT 必须关闭 DHT/PeX/LSD/匿名模式
- 硬链接要求下载目录和媒体库在同一文件系统（都在 `/volume1/Media-PT` 下）
- Clash 只代理 Telegram 域名，不影响其他流量
