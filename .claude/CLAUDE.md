# NAS PT Media Bot

## 项目概述
绿联 NAS 上的全自动影视下载管理系统。通过 Telegram Bot 交互, Docker Compose 部署。

## Workspace
- 开发路径: `/home/ubuntu/nas`
- NAS 路径: `/volume1/docker/my-nas-pt-media/`
- GitHub: `github.com/nickduan622/nasbot`

## 项目结构
```
nas/
├── .claude/CLAUDE.md    ← 你在读的这个文件
├── PLAN.md              ← 当前状态 + TODO (每次 session 先读这个)
├── README.md            ← 用户文档, 部署指南
├── docker-compose.yml          ← 通用 compose
├── docker-compose-ugos.yml     ← 绿联 NAS 专用 compose
├── .env.template               ← 环境变量模板
├── scripts/
│   └── update.sh               ← NAS 代码更新脚本
├── bot/                        ← Telegram Bot 代码
│   ├── SPEC.md                 ← Bot 功能规格
│   ├── main.py                 ← 入口
│   ├── config.py               ← 配置
│   ├── scheduler.py            ← 定时任务
│   ├── handlers/{farm,search,status}.py  ← TG 命令
│   └── services/{mteam,qbit,radarr,sonarr,farmer}.py  ← API 客户端
└── docs/                       ← 参考文档
    ├── directory-structure.md   ← NAS 目录结构说明
    ├── deploy.md               ← 部署操作记录
    ├── pt-guide.md             ← M-Team 新手指南
    └── requirements.md         ← 原始需求
```

## 开发约定
- NAS 上没有 git, 代码更新流程: push to GitHub → NAS 上运行 update.sh (用 ghfast.top 镜像) → 重启 nasbot 容器
- M-Team API: 搜索用 JSON, genDlToken 用 form data
- Telegram API 需要走 Clash 代理 (http://clash:7890), 其他服务直连
- 密钥不入 git (.env, clash/config.yaml)
- Git author: nickduan622 <nick.duan19961212@gmail.com>, 不加 Co-Authored-By
- **新增/修改 Bot 命令时，必须同步更新 main.py 里的 start_cmd help 文本和 set_my_commands 列表**

## 恢复 Session 检查清单
1. 读 `PLAN.md` 了解当前状态和 TODO
2. 读 `bot/SPEC.md` 了解 Bot 功能设计
3. 如需部署, 参考 `README.md` 的配置步骤
4. 如需改 M-Team API, 参考 `docs/pt-guide.md`