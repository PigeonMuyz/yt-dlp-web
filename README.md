# yt-dlp Web

视频下载管理平台，支持 YouTube / B站，专为 NAS 用户设计。

## ✨ 功能

- 📥 视频下载 — 支持 YouTube、Bilibili，单视频/播放列表/频道
- 🎬 双编码策略 — 同时下载 VP9 + AV1 / HEVC，双版本归档
- 📺 订阅管理 — 频道/UP主订阅，自动检查新视频
- 📋 任务队列 — 并行下载、实时进度、格式自动降级
- 📝 Emby/Jellyfin — 自动生成 NFO、刮削元数据、触发库刷新
- 🍪 Cookie 管理 — 导入浏览器 cookies 绕过登录限制
- 📱 移动端适配 — 手机/平板友好的响应式界面
- 🔄 一键更新 — GitHub 版本检查 + 一键热更新

## 🚀 群晖 / NAS 部署

### 1. 下载配置文件

```bash
mkdir -p /volume1/docker/ytdlp-web && cd /volume1/docker/ytdlp-web
wget https://raw.githubusercontent.com/PigeonMuyz/yt-dlp-web/main/docker-compose.nas.yml -O docker-compose.yml
```

### 2. 修改配置

编辑 `docker-compose.yml`，修改：
- **下载目录**：将 `./ytdlp-media:/media` 改为你的媒体库路径
- **密码**：修改 `YTDLP_ADMIN_PASSWORD`
- **代理**（可选）：取消注释 `YTDLP_PROXY` 行
- **Emby**（可选）：取消注释 Emby 相关行

### 3. 启动

```bash
docker compose up -d
```

### 4. 访问

浏览器打开 `http://群晖IP:8686`

### 5. 更新

```bash
docker compose pull
docker compose up -d
```

## 🛠 本地开发

```bash
git clone https://github.com/PigeonMuyz/yt-dlp-web.git
cd yt-dlp-web

# 前端
cd frontend && npm install && npm run build && cd ..

# 启动
docker compose up -d --build
```

## 📦 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy + APScheduler |
| 前端 | Vue 3 + Naive UI |
| 下载 | yt-dlp |
| 数据库 | PostgreSQL |
| 缓存 | Redis |
| 部署 | Docker Compose |

## 📄 License

MIT
