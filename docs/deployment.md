# 文档托管平台部署文档

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | >= 3.11 |
| SQLite | 内置（无需额外安装） |
| 操作系统 | Windows / Linux / macOS |

---

## 快速部署（本地运行）

### 1. 克隆 / 获取代码

```bash
cd 文档托管平台
```

### 2. 创建配置文件

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入飞书应用信息：

```ini
# 从飞书开发者后台获取
FEISHU_APP_ID=cli_a1234567890
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OAuth 回调地址（需与飞书后台配置一致）
FEISHU_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/callback

# JWT 加密密钥（务必修改为随机字符串）
JWT_SECRET=your-random-secret-at-least-32-chars-long

# 可选：修改监听端口
PORT=8000
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问 `http://localhost:8000` 即可打开平台。

---

## Docker 部署

### 1. 创建配置文件

```bash
cp .env.example .env
# 编辑 .env 填入飞书应用信息（同上）
```

### 2. 构建并启动

```bash
docker-compose -f docker/docker-compose.yml up -d
```

首次启动会自动构建镜像，之后访问 `http://localhost:80`。

### 3. 查看日志

```bash
docker-compose -f docker/docker-compose.yml logs -f
```

### 4. 停止服务

```bash
docker-compose -f docker/docker-compose.yml down
```

---

## 飞书应用配置

### 创建飞书应用

1. 登录 [飞书开发者后台](https://open.feishu.cn/app)
2. 创建企业自建应用
3. 获取 **App ID** 和 **App Secret**，填入 `.env`

### 配置 OAuth 2.0

在飞书应用后台 → 安全设置 → **OAuth 2.0 重定向 URI**：

```
http://{你的域名或IP}:{端口}/api/auth/callback
```

示例：`http://localhost:8000/api/auth/callback`

### 配置权限

在飞书应用后台 → 权限管理，开启以下权限：

| 权限 | 用途 |
|------|------|
| `contact:user.base:readonly` | 读取用户基本信息 |
| `contact:user.employee_id:readonly` | 读取用户 employee_id |
| `im:message` | 发送消息（L4审批通知） |
| `im:message:send_as_bot` | 以机器人身份发送消息 |

### 发布应用

1. 在飞书开发者后台 → 版本管理与发布中创建版本
2. 添加审核说明（如"用于内部文档平台登录认证"）
3. 提交审核并由管理员审批

### 配置 Webhook（用于 L4 审批卡片回调）

在飞书应用后台 → 事件与回调 → **请求网址**：

```
http://{你的域名或IP}:{端口}/api/feishu/webhook/card-action
```

> **注意**：本地开发时 Webhook 需要公网可达。可使用 [ngrok](https://ngrok.com/) 进行内网穿透：
> ```bash
> ngrok http 8000
> ```
> 将生成的公网 URL 分别配置到飞书的 OAuth 重定向 URI 和 Webhook 地址中。

---

## 文件存储

上传的文件默认保存在项目根目录的 `uploads/` 文件夹中：

```
uploads/
  {project_id}/
    files/
      index.html
      css/style.css
      images/logo.png
```

- 数据库文件位于 `data/app.db`
- 建议定期备份 `data/` 和 `uploads/` 目录

---

## 配置说明

### 完整配置项（.env）

| 配置项 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `HOST` | 否 | `0.0.0.0` | 监听地址 |
| `PORT` | 否 | `8000` | 监听端口 |
| `DEBUG` | 否 | `true` | 调试模式（生产环境建议设为 false） |
| `FEISHU_APP_ID` | **是** | - | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | **是** | - | 飞书应用 App Secret |
| `FEISHU_OAUTH_REDIRECT_URI` | **是** | - | OAuth 回调地址 |
| `JWT_SECRET` | **是** | - | JWT 加密密钥 |
| `JWT_EXPIRY_HOURS` | 否 | `168` | 登录会话有效期（小时） |
| `DATABASE_URL` | 否 | `sqlite+aiosqlite:///data/app.db` | 数据库连接地址 |
| `UPLOAD_DIR` | 否 | `./uploads` | 文件上传目录 |
| `MAX_UPLOAD_SIZE_MB` | 否 | `100` | 单次上传最大大小 |

---

## 生产环境建议

1. **修改 JWT_SECRET**：使用足够长的随机字符串
2. **关闭 DEBUG**：设置 `DEBUG=false`
3. **反向代理**：建议使用 Nginx 反向代理，配置 SSL 证书启用 HTTPS
4. **定期备份**：备份 `data/` 和 `uploads/` 目录
5. **目录列表**：敏感项目关闭"允许目录列表"防文件遍历
6. **防火墙**：限制非必要端口的对外暴露
