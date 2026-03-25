# NAS 自动化影视下载系统 — 需求整理

## 一、用户故事

**当前流程（手动）：**
手动找 torrent → qBittorrent 下载 → 手动找字幕 → 手动重命名

**目标流程（自动）：**
发消息给 Bot「电影名/剧名」→ 系统全自动完成 → 播放器直接看

---

## 二、功能需求

### 2.1 触发方式
- 通过 Telegram Bot / Discord Bot / Webhook 发送资源名称
- 支持电影和电视剧
- **推荐 Telegram Bot**：在国内外都能用，生态成熟，API 简单

### 2.2 资源搜索
- 收到资源名后，自动在多个 torrent 站点搜索
- 搜索源分两类：
  - **公开站点**：1337x, RARBG (已关), TorrentGalaxy, EZTV, Nyaa 等
  - **PT 站点（私有）**：如果后续买到 PT 账号，可接入（馒头、海盗、观众等）
- 搜索结果按质量排序

### 2.3 质量优先策略
- 优先级：4K Remux > 4K HDR > 4K > 1080p Remux > 1080p BluRay > 1080p WEB-DL > 720p
- 同质量下优先选 seed 数多的
- 允许同时最多 **10 个 torrent 并行尝试下载**
- 从中选取实际下载速度最好、质量最高的

### 2.4 下载管理
- 下载客户端：qBittorrent（已有）
- 「无法下载」的判定规则：
  - 超过 X 分钟下载速度为 0（可配置，默认 30 分钟）
  - 下载进度长时间卡住不动
  - 超过总超时时间（可配置，默认 4 小时）
- 当最佳资源成功下载完成后：
  - 自动删除其他未完成的下载任务
  - 清理对应的临时文件

### 2.5 字幕匹配
- 下载完成后自动搜索匹配的 **中文字幕**（简体优先）
- 字幕来源：射手网(assrt)、SubHD、OpenSubtitles、字幕组等
- 字幕文件命名与视频文件对齐

### 2.6 文件整理与重命名
- 按统一格式重命名，便于播放器（Emby/Jellyfin/Plex）刮削：
  - 电影：`/Movies/电影名 (年份)/电影名 (年份).mkv`
  - 电视剧：`/TV/剧名 (年份)/Season XX/剧名 - SXXEXX.mkv`
- 字幕文件放在同目录，命名一致：`电影名 (年份).zh.srt`

---

## 三、非功能需求

- 所有服务跑在 Docker 上（绿联 NAS 支持 Docker）
- 权限隔离：各容器用最小权限，共享目录通过 volume 挂载
- Web UI 管理：可通过浏览器查看状态、调整设置
- 通知：下载完成 / 失败时通过 Bot 回复通知

---

## 四、技术方案概览

### 核心架构（全部 Docker 容器化）

```
[Telegram Bot / Overseerr]     ← 用户入口
        │
        ▼
[Radarr (电影) / Sonarr (电视剧)]  ← 资源管理 & 质量策略
        │
        ▼
[Prowlarr]                     ← 搜索引擎聚合（对接多个 torrent 站点）
        │
        ▼
[qBittorrent]                  ← 下载客户端
        │
        ▼
[ChineseSubFinder]             ← 中文字幕自动匹配
        │
        ▼
[Emby / Jellyfin]              ← 播放器（可选）
```

### 组件说明

| 组件 | 作用 | 说明 |
|------|------|------|
| **Prowlarr** | Torrent 索引聚合器 | 统一管理公开/PT 站点，给 Radarr/Sonarr 提供搜索 |
| **Radarr** | 电影自动化 | 搜索、质量筛选、下载管理、重命名、整理 |
| **Sonarr** | 电视剧自动化 | 同上，针对剧集 |
| **qBittorrent** | 下载客户端 | 实际执行 torrent 下载 |
| **Overseerr** | 请求管理前端 | 美观的 Web UI + 支持用户请求（可对接 Bot） |
| **Requestrr** | Bot 桥接 | 把 Telegram/Discord 消息转发给 Overseerr/Radarr/Sonarr |
| **ChineseSubFinder** | 中文字幕 | 专门针对中文字幕的自动下载工具 |

### 关于「同时 10 个 torrent 尝试」

Radarr/Sonarr 默认行为是选最优的一个下载。要实现「同时试 10 个」有两种方式：
1. **方案 A（推荐先用）**：信任 Radarr/Sonarr 的排序逻辑，它会按 seed 数 + 质量打分选最优的，如果失败会自动抓下一个。实际体验已经很好。
2. **方案 B（进阶）**：写自定义脚本，通过 Radarr/Sonarr API 手动触发多个下载，监控速度，保留最佳，删除其余。需要额外开发。

**建议先用方案 A 跑起来，体验不满意再做方案 B。**

---

## 五、关于 PT（Private Tracker）

**结论：非常推荐，优先级高于公开站点。**

PT 的优势：
- 资源质量远高于公开站（原盘、Remux 资源丰富）
- 下载速度快（做种率有保障）
- 资源存活时间长
- Prowlarr 原生支持 PT 站点

闲鱼买 PT 邀请/号的注意事项：
- 大部分 PT 站规则禁止买卖邀请，有封号风险
- 建议买「合租账号」或「独立邀请码」，风险不同
- 推荐站点优先级：馒头(M-Team) > 海盗(PTH) > 观众(AUDIENCES) > 其他
- 买到后在 Prowlarr 中添加 indexer 即可接入，无需改其他配置

---

## 六、权限与安全（绿联 NAS）

- 所有容器使用非 root 用户运行（PUID/PGID 配置）
- 下载目录、媒体目录分开挂载
- qBittorrent Web UI 设置强密码
- Telegram Bot Token 存环境变量，不硬编码
- 如果暴露外网，用反向代理 + HTTPS
