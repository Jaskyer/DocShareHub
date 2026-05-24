---
name: DocShareHub 文档托管平台
description: 基于 FastAPI + SQLite 的企业文档托管与分享平台，四级安全管控、飞书 OAuth、自定义 URL、回收站
type: project
---

**GitHub 仓库名:** DocShareHub

**项目描述:** 企业文档托管与分享平台，支持飞书 OAuth 登录、L1-L4 四级安全等级（L1/L2 公开、L3 密码保护、L4 审批制）、自定义 URL 重命名、文件可见性开关、回收站、目录列表、feishu 卡片消息审批等。

**技术栈:**
- FastAPI (async) + Starlette
- SQLAlchemy 2.0 (async) + aiosqlite
- SQLite (WAL 模式)
- JWT (python-jose) for session
- Jinja2 模板渲染
- bcrypt 密码哈希
- httpx (飞书 API)
- pydantic-settings + .env 配置

**入口:** `app/main.py` → `uvicorn app.main:app`

**目录结构:**
- `app/models/` — SQLAlchemy ORM 模型 (User, Project, Document, UrlMapping, AccessRequest, Favorite)
- `app/routers/` — API 路由 (auth, projects, documents, file_serve, url_mappings, access_requests, favorites, feishu_webhook, pages)
- `app/services/` — 业务逻辑层
- `app/schemas/` — Pydantic 请求/响应
- `app/middleware/` — AuthMiddleware, SecurityHeadersMiddleware
- `app/templates/` — Jinja2 模板
- `app/utils/` — 工具函数、异常、频率限制

**核心路由:** `file_serve.py` 的 catch-all `/{full_path:path}` 是核心，处理项目文件浏览/下载、权限校验、URL 重命名解析

**关键业务规则:**
- 项目各安全等级：L1/L2 公开 → L3 密码 → L4 审批
- 文件上传时自动创建 Document 记录（含目录结构）
- URL 重命名绑定到 Document，映射表 UrlMapping
- 删除文件软删除（is_deleted=True）+ 文件移至 .recycle/
- 文件可见性 is_visible 控制公开浏览是否显示
- 文档计数 document_count 在 project_to_response 中计算

**Why:** 企业内文档分享需要精细的安全管控，飞书生态集成
**How to apply:** 所有文件路径比较需 normalize backslash→slash（Windows兼容）。权限校验在 file_serve.py 中统一处理。
