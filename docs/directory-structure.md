# 目录结构与管理指南

## NAS 目录结构总览

```
/volume1/Media-PT/
│
├── movies/                ← 🎬 电影库（Radarr 自动整理到这里）
│   ├── 盗梦空间 (2010)/
│   │   ├── 盗梦空间 (2010).mkv
│   │   └── 盗梦空间 (2010).zh.srt      ← ChineseSubFinder 自动匹配
│   └── ...
│
├── tv/                    ← 📺 剧集库（Sonarr 自动整理到这里）
│   ├── 三体 (2023)/
│   │   ├── Season 01/
│   │   │   ├── S01E01.mkv
│   │   │   └── S01E01.zh.srt
│   │   └── ...
│   └── ...
│
├── downloads/             ← ⬇️ 下载临时区（qBittorrent 下载到这里）
│   ├── movies/            ← Radarr 下载的电影（下完后硬链接到 movies/）
│   ├── tv/                ← Sonarr 下载的剧集（下完后硬链接到 tv/）
│   └── seed/              ← 🌱 养号专用（只为做种，不进媒体库）
│
/volume1/docker/my-nas-pt-media/   ← ⚙️ 各服务的配置数据（不用管）
    ├── qbittorrent/
    ├── prowlarr/
    ├── radarr/
    ├── sonarr/
    └── chinesesubfinder/
```

## 关键概念

### 1. 媒体库 vs 下载区 vs 养号区

| 区域 | 路径 | 用途 | 绑定到影视中心？ |
|------|------|------|-----------------|
| **电影库** | `/volume1/Media-PT/movies` | 整理好的电影，命名规范，有字幕 | ✅ 是 |
| **剧集库** | `/volume1/Media-PT/tv` | 整理好的剧集，命名规范，有字幕 | ✅ 是 |
| **下载区** | `/volume1/Media-PT/downloads/movies` 和 `tv` | 临时下载目录，下完后自动整理走 | ❌ 否 |
| **养号区** | `/volume1/Media-PT/downloads/seed` | 纯粹为了做种提高分享率的资源 | ❌ 否 |

### 2. 绿联影视中心绑定路径

创建新影音库时，**只绑定这两个路径**：
- `/volume1/Media-PT/movies`
- `/volume1/Media-PT/tv`

**不要绑定** `/volume1/Media-PT/downloads`，那里面是未整理的原始文件。

### 3. 文件怎么从「下载区」到「媒体库」？

```
你在 TG 发 "盗梦空间"
     ↓
Radarr 在 M-Team 搜索，找到最佳质量种子
     ↓
qBittorrent 下载到 /media/downloads/movies/
     ↓
下载完成 → Radarr 自动：
  1. 重命名文件（标准命名：电影名 (年份).mkv）
  2. 硬链接到 /media/movies/盗梦空间 (2010)/
  3. 原文件留在 downloads/ 继续做种
     ↓
ChineseSubFinder 扫描 /media/movies/，自动下载中文字幕
     ↓
绿联影视中心自动刷新，可以播放了
```

**硬链接**：同一个文件在两个位置出现，但只占一份磁盘空间。下载区的文件继续做种，媒体库的文件用来播放，互不影响。

### 4. 养号资源怎么管理？

养号区 `/media/downloads/seed/` 里的文件：
- 不会被 Radarr/Sonarr 管理
- 不会出现在影视中心
- 唯一目的：保持做种，积累上传量和魔力值
- Bot 会自动管理：定期清理已达到做种目标的资源

### 5. 各服务做什么？

| 服务 | 端口 | 职责 |
|------|------|------|
| **qBittorrent** | 8092 | BT 下载客户端 |
| **Prowlarr** | 9696 | 索引聚合器 — 统一管理 M-Team 等搜索源 |
| **Radarr** | 7878 | 电影管理 — 搜索、下载、重命名、整理 |
| **Sonarr** | 8989 | 剧集管理 — 同上，针对电视剧 |
| **ChineseSubFinder** | 19035 | 自动搜索匹配中文字幕 |
| **FlareSolverr** | 8191 | 反爬绕过（辅助 Prowlarr 访问被 Cloudflare 保护的站点） |
| **TG Bot** | - | Telegram 交互入口（搜索、下载、状态查询、养号自动化） |
