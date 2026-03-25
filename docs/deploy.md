# 部署指南

## 网络说明

云开发机无法直连 NAS（家庭内网）。部署方式：
- **推荐**：回家后 SSH 到 NAS 执行以下命令
- **远程**：通过绿联 Docker 管理器或 Portainer Web UI

---

## 前置准备

### Step 0: 确认 NAS 用户 ID

SSH 到 NAS 后执行：

```bash
id
```

记下 `uid` 和 `gid` 的数字（通常是 1000），填入 `.env` 文件。

### Step 1: 创建目录结构

```bash
# 媒体库目录
mkdir -p /volume1/Media-PT/downloads/movies
mkdir -p /volume1/Media-PT/downloads/tv
mkdir -p /volume1/Media-PT/movies
mkdir -p /volume1/Media-PT/tv

# 容器配置目录
mkdir -p /volume1/docker/media-stack/qbittorrent
mkdir -p /volume1/docker/media-stack/prowlarr
mkdir -p /volume1/docker/media-stack/radarr
mkdir -p /volume1/docker/media-stack/sonarr
mkdir -p /volume1/docker/media-stack/chinesesubfinder
```

### Step 2: 上传配置文件

将 `docker-compose.yml` 和 `.env` 上传到 NAS：

```bash
# 在 NAS 上创建项目目录
mkdir -p /volume1/docker/media-stack

# 从云开发机 scp 到 NAS（回家后在云开发机上执行）
scp /home/ubuntu/nas/docker-compose.yml root@192.168.1.187:/volume1/docker/media-stack/
scp /home/ubuntu/nas/.env root@192.168.1.187:/volume1/docker/media-stack/
```

### Step 3: 启动所有服务

```bash
cd /volume1/docker/media-stack
docker compose up -d
```

等待所有镜像拉取完毕（首次可能需要 10-20 分钟）。

---

## 服务配置（全部通过浏览器 Web UI）

启动后，所有服务的 Web UI：

| 服务 | 地址 | 用途 |
|------|------|------|
| qBittorrent | `http://192.168.1.187:8092` | 下载客户端 |
| Prowlarr | `http://192.168.1.187:9696` | 搜索源管理 |
| Radarr | `http://192.168.1.187:7878` | 电影管理 |
| Sonarr | `http://192.168.1.187:8989` | 剧集管理 |
| ChineseSubFinder | `http://192.168.1.187:19035` | 中文字幕 |
| FlareSolverr | `http://192.168.1.187:8191` | 反爬（无UI，被Prowlarr调用） |

### Step 4: 配置 qBittorrent

1. 打开 `http://192.168.1.187:8092`
2. 默认密码在日志里：`docker logs qbit-pt` 查看
3. Settings → Downloads：
   - Default Save Path: `/media/downloads`
4. Settings → Web UI：
   - 修改密码为你想要的密码
5. Settings → BitTorrent：
   - Seeding Limits → 按 PT 站要求设置（建议做种比率 2.0 或做种时间 72h）

### Step 5: 配置 Prowlarr

1. 打开 `http://192.168.1.187:9696`
2. 首次进入设置认证方式和密码
3. Settings → Indexers → Add Indexer：
   - **PT 站**：搜索 "M-Team" 或你注册的 PT 站名，填入 passkey
   - **公开站**（备选）：添加 1337x、TorrentGalaxy 等
4. Settings → Apps → Add Application：
   - 添加 Radarr：URL = `http://radarr:7878`，API Key 从 Radarr 获取
   - 添加 Sonarr：URL = `http://sonarr:8989`，API Key 从 Sonarr 获取
5. Settings → Tags → FlareSolverr：
   - Tag 设为 `flaresolverr`
   - URL = `http://flaresolverr:8191`（仅公开站需要）

### Step 6: 配置 Radarr（电影）

1. 打开 `http://192.168.1.187:7878`
2. Settings → Media Management：
   - Root Folder: 添加 `/media/movies`
   - Movie Naming: 开启，格式用默认（`{Movie Title} ({Release Year})/{Movie Title} ({Release Year}) [{Quality Full}]`）
   - 勾选 "Use Hardlinks instead of Copy"（重要！PT 做种需要保留原文件）
3. Settings → Quality → Quality Profiles：
   - 编辑 "HD - 1080p" 或创建自定义 profile
   - 勾选想要的质量：Remux-2160p > Bluray-2160p > Remux-1080p > Bluray-1080p > WEB-DL 1080p
   - 拖动排序，最高质量在最上面
4. Settings → Download Clients → Add：
   - qBittorrent
   - Host: `qbit-pt`，Port: `8092`
   - Username/Password: 你设的密码
   - Category: `radarr`
5. Settings → General → 记下 API Key（Prowlarr 和 Telegram Bot 要用）

### Step 7: 配置 Sonarr（剧集）

同 Radarr，区别：
- Root Folder: `/media/tv`
- Category: `sonarr`
- Series Naming: `{Series Title} ({Year})/Season {season:00}/{Series Title} - S{season:00}E{episode:00}`

### Step 8: 配置 ChineseSubFinder

1. 打开 `http://192.168.1.187:19035`
2. 首次设置管理员密码
3. 设置 → 字幕源：开启 assrt、SubHD、OpenSubtitles
4. 设置 → 媒体库路径：确认 `/media/movies` 和 `/media/tv`
5. 设置 → 扫描间隔：建议 6 小时

---

## Telegram Bot（Phase 2，核心跑通后再做）

Telegram Bot Token 已创建，后续对接 Radarr/Sonarr API。

---

## 目录结构说明

```
/volume1/Media-PT/                ← MEDIA_DIR（所有容器共享挂载为 /media）
├── downloads/                    ← qBittorrent 下载目录
│   ├── movies/                   ← Radarr 分类下载
│   └── tv/                       ← Sonarr 分类下载
├── movies/                       ← 整理后的电影库（播放器读这里）
│   └── 电影名 (年份)/
│       ├── 电影名 (年份).mkv
│       └── 电影名 (年份).zh.srt
└── tv/                           ← 整理后的剧集库
    └── 剧名 (年份)/
        └── Season 01/
            ├── 剧名 - S01E01.mkv
            └── 剧名 - S01E01.zh.srt

/volume1/docker/media-stack/      ← CONFIG_DIR（容器配置数据）
├── docker-compose.yml
├── .env
├── qbittorrent/
├── prowlarr/
├── radarr/
├── sonarr/
└── chinesesubfinder/
```

**关键设计**：所有容器把 `/volume1/Media-PT` 挂载为 `/media`，路径一致 → hardlink 生效 → 下载的文件和整理后的文件共享磁盘空间，不会占双份。PT 做种时原文件在 downloads/ 里继续做种，movies/tv/ 里的是硬链接，播放器正常读取。
