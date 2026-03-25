# NAS PT Media Bot — 功能规格

## 概述

自定义 Telegram Bot，作为整个媒体系统的唯一交互入口。
用户通过 Telegram 对话完成所有操作：搜索下载、状态监控、养号管理。

## 命令列表

### 📥 搜索下载

| 命令 | 说明 | 示例 |
|------|------|------|
| `/movie <名称>` | 搜索电影 | `/movie 盗梦空间` |
| `/tv <名称>` | 搜索剧集 | `/tv 三体` |

**交互流程：**
```
用户: /movie 盗梦空间
Bot:  🔍 搜索中...
Bot:  找到 3 个结果：
      1. Inception (2010) - Christopher Nolan
      2. Inception: The Cobol Job (2010)
      3. ...
      请选择（回复数字）
用户: 1
Bot:  ✅ 已添加「Inception (2010)」到下载队列
      质量目标：Bluray-2160p > Bluray-1080p
      ⏳ 搜索种子中...
Bot:  📦 找到种子：Inception.2010.2160p.BluRay (18.5GB) FREE
      ⬇️ 开始下载...
      [进度条会定时更新]
Bot:  ✅ 下载完成！
      📁 Inception (2010) / Inception (2010).mkv
      🔤 字幕：中文字幕已匹配
      🎬 可以在影视中心播放了
```

### 📊 状态查询

| 命令 | 说明 |
|------|------|
| `/status` | 综合状态面板 |
| `/downloads` | 当前下载任务详情 |
| `/ratio` | M-Team 账户详情 |

**`/status` 输出示例：**
```
📊 系统状态

🌐 M-Team
  分享率: 1.25 ↑12.3GB ↓9.8GB
  魔力值: 2,850
  做种数: 47

⬇️ 下载中 (2)
  Inception (2010) ████████░░ 82% ↓15.2MB/s
  三体 S01E03      ██░░░░░░░░ 20% ↓8.1MB/s

✅ 最近完成 (3)
  星际穿越 (2014) - 2小时前
  三体 S01E01 - 5小时前
  三体 S01E02 - 5小时前
```

### 🌱 养号管理

| 命令 | 说明 |
|------|------|
| `/farm status` | 养号状态：当前做种数、预估魔力收入 |
| `/farm start` | 开启自动养号 |
| `/farm stop` | 暂停自动养号 |

**自动养号逻辑：**
1. 每 30 分钟扫描 M-Team Free/2xFree 种子
2. 自动选择：优先大文件 + 下载者多的
3. 下载到 `/media/downloads/seed/`（不进媒体库）
4. 做种直到分享率达标（单种 2.0 或做种 48h+）
5. 达标后如果磁盘空间不足，自动清理最老的已达标种子
6. 磁盘空间保护：养号区总量不超过可配置上限（默认 500GB）

### 🔔 生命周期通知（被动推送）

Bot 自动发送，不需要用户触发：

| 事件 | 通知内容 |
|------|---------|
| 搜索到种子 | 种子名称、大小、是否 Free |
| 下载开始 | 文件大小、预估时间 |
| 下载进度 | 每 25% 进度更新一次（25%/50%/75%） |
| 下载完成 | 文件路径、耗时 |
| 字幕就绪 | 匹配的字幕语言和来源 |
| 导入完成 | 最终文件路径，可以播放 |
| 养号日报 | 每日一次：新增上传量、当前分享率、魔力值变化 |
| ⚠️ 分享率预警 | 分享率低于 0.5 时立即告警 |

## 技术方案

### 依赖的 API

| 服务 | API | 用途 |
|------|-----|------|
| Radarr | REST API :7878 | 电影搜索、添加、状态 |
| Sonarr | REST API :8989 | 剧集搜索、添加、状态 |
| qBittorrent | WebUI API :8092 | 下载进度、做种状态、添加种子 |
| M-Team | Web API (kp.m-team.cc) | 账户状态、Free 种子列表 |
| ChineseSubFinder | API :19035 | 字幕状态 |

### 技术栈

- Python 3.12
- python-telegram-bot（异步）
- aiohttp（API 调用）
- APScheduler（定时任务：养号扫描、进度检查、日报）
- Docker 部署

### 配置项（环境变量）

```env
# Telegram
TG_BOT_TOKEN=<your-telegram-bot-token>
TG_CHAT_ID=<your-telegram-chat-id>

# Radarr / Sonarr
RADARR_URL=http://radarr:7878
RADARR_API_KEY=<your-radarr-api-key>
SONARR_URL=http://sonarr:8989
SONARR_API_KEY=<your-sonarr-api-key>

# qBittorrent
QBIT_URL=http://qbit-pt:8092
QBIT_USER=admin
QBIT_PASS=<your-qbit-password>

# M-Team
MT_API_TOKEN=<your-mteam-api-token>
MT_BASE_URL=https://kp.m-team.cc

# 养号配置
FARM_ENABLED=true
FARM_SCAN_INTERVAL=30         # 分钟
FARM_MAX_DISK_GB=500          # 养号区磁盘上限
FARM_SEED_RATIO_TARGET=2.0    # 单种目标分享率
FARM_SEED_TIME_TARGET=4320    # 单种目标做种时间（分钟）
```
