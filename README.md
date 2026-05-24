# 文档托管平台

基于 FastAPI 的企业文档托管与分享平台，支持飞书 OAuth 登录、多级安全管控、自定义 URL 重命名、回收站等特性。

## 功能特性

- **飞书 OAuth 登录** — 通过飞书账号一键登录，JWT Session 维持身份
- **项目管理** — 创建项目，设置 L1~L4 安全等级、独立 URL 路径、目录列表开关
- **文件上传与管理** — 上传文件/文件夹，编辑描述，显示/隐藏切换
- **URL 重命名** — 将文件映射为自定义 URL（如 `report-2024` 代替原始文件名）
- **四级安全管控**
  - L1/L2 — 公开访问
  - L3 — 密码保护（bcrypt 加密）
  - L4 — 申请审批制（飞书卡片消息推送给项目所有者审批）
- **回收站** — 删除的文件移至项目回收站目录，可恢复
- **收藏系统** — 用户可收藏项目/文档
- **错误尝试限制** — L3 密码尝试次数限制，防暴力破解

## 技术栈

| 分类 | 技术 |
|------|------|
| 框架 | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async) + aiosqlite |
| 数据库 | SQLite (WAL 模式) |
| 认证 | 飞书 OAuth 2.0 + JWT (python-jose) |
| 模板 | Jinja2 |
| 密码哈希 | bcrypt |
| HTTP 客户端 | httpx |
| 配置 | pydantic-settings + .env |

## 快速开始

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd 文档托管平台
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入飞书应用凭据：

```env
FEISHU_APP_ID=cli_xxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/callback
JWT_SECRET=替换为随机字符串（至少32位）
```

> 飞书应用需在[飞书开放平台](https://open.feishu.cn)创建，开启「网页应用」能力并配置回调地址。

### 4. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000

首次启动会自动创建 SQLite 数据库和表结构。

## 项目结构

```
├── app/
│   ├── main.py                 # FastAPI 应用入口，中间件和路由注册
│   ├── config.py               # 配置管理（pydantic-settings）
│   ├── database.py             # 数据库引擎、会话、初始化及迁移
│   ├── template_setup.py       # Jinja2 模板配置
│   ├── models/                 # SQLAlchemy ORM 模型
│   │   ├── user.py             # 用户（飞书信息）
│   │   ├── project.py          # 项目（安全等级、密码、路径）
│   │   ├── document.py         # 文档（文件/目录、可见性、软删除）
│   │   ├── url_mapping.py      # URL 重命名映射
│   │   ├── access_request.py   # L4 访问申请
│   │   └── favorite.py         # 用户收藏
│   ├── routers/                # API 路由
│   │   ├── auth.py             # 飞书 OAuth 登录/回调/登出
│   │   ├── projects.py         # 项目 CRUD、密码验证
│   │   ├── documents.py        # 文件上传、列表、删除、重命名
│   │   ├── url_mappings.py     # URL 映射列表
│   │   ├── access_requests.py  # L4 申请/审批
│   │   ├── favorites.py        # 收藏管理
│   │   ├── feishu_webhook.py   # 飞书卡片消息回调
│   │   ├── file_serve.py       # 核心：权限校验 + 文件/目录服务
│   │   └── pages.py            # HTML 页面路由
│   ├── services/               # 业务逻辑层
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── middleware/              # 认证中间件、安全头中间件
│   ├── utils/                  # 工具函数、异常定义、频率限制
│   ├── templates/              # Jinja2 模板（15个页面）
│   └── static/                 # 静态资源（运行时自动创建）
├── data/                       # SQLite 数据库文件
├── uploads/                    # 用户上传文件（按项目分目录）
├── docs/                       # 文档
├── docker/                     # Docker 相关
├── requirements.txt
├── .env.example                # 环境变量模板
└── README.md
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/login` | 飞书 OAuth 登录跳转 |
| GET | `/api/auth/callback` | 飞书 OAuth 回调 |
| GET | `/api/auth/status` | 当前登录状态 |
| GET | `/api/projects` | 我的项目列表 |
| GET | `/api/projects/public` | 公开项目列表 |
| POST | `/api/projects` | 创建项目 |
| PUT | `/api/projects/{id}` | 编辑项目 |
| DELETE | `/api/projects/{id}` | 删除项目 |
| POST | `/api/projects/{id}/verify-password` | 验证 L3 密码 |
| POST | `/api/projects/{id}/documents/upload` | 上传文件 |
| GET | `/api/projects/{id}/documents` | 文档列表 |
| PUT | `/api/projects/{id}/documents/{doc_id}` | 更新文档（描述/可见性） |
| DELETE | `/api/projects/{id}/documents/{doc_id}` | 删除文档（移入回收站） |
| POST | `/api/projects/{id}/documents/{doc_id}/rename` | 设置 URL 重命名 |
| DELETE | `/api/projects/{id}/documents/{doc_id}/rename` | 清除 URL 重命名 |
| GET | `/api/projects/{id}/url-mappings` | 获取 URL 映射列表 |
| POST | `/api/projects/{id}/access-requests` | 提交 L4 访问申请 |
| GET/POST | `/api/feishu/webhook` | 飞书卡片回调 |
| GET | `/{visible_path}` | 浏览项目文件 |

## 安全等级说明

| 等级 | 名称 | 访问规则 |
|------|------|---------|
| L1 | 完全公开 | 任何人可访问 |
| L2 | 公开 | 任何人可访问 |
| L3 | 密码保护 | 需输入项目密码，错误尝试受频率限制 |
| L4 | 申请审批 | 需提交申请，项目所有者通过飞书卡片消息审批 |

## License

MIT
