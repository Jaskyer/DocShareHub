---
name: 架构决策记录
description: DocShareHub 的关键架构决策、已知问题和平台兼容性
type: project
---

**Known Windows Issues (已修复):**
- `storage_service.py` 中 `stored_path.split(os.sep)[0]` → `split("/")[0]`，因为 DB 中 stored_path 统一使用 `/`，但 Windows 的 os.sep 是 `\`，导致 project_id 解析为完整路径
- `file_serve.py` 中所有 `doc.stored_path` 与 `os.path.join` 生成的路径比较时需 normalize：`.replace("\\", "/")`，发生在 _render_directory（renamed_paths/doc_map 构建）和 _serve_path（is_renamed 检查）

**Auth 状态传播 (Starlette 0.38.6):**
- `BaseHTTPMiddleware` 创建的 `Request` 对象不会向路由处理器传播 `request.state`，但 ASGI scope dict 是共享的
- 解决方式：中间件往 `request.scope["user"]` 写，路由从 `request.scope.get("user")` 读
- 涉及文件：`auth_middleware.py`, 所有 routers 中的 `require_user()`

**数据库迁移:**
- `database.py` 的 `init_db()` 中包含增量迁移（`alter table add column if not exists`），启动时自动执行
- 已有迁移字段：`allow_listing`(projects)，`description`, `is_deleted`, `is_visible`(documents)

**URL 路由:**
- `file_serve.py` 的 catch-all `/{full_path:path}` 必须最后注册（已在 main.py 中最后 include_router），否则会吃掉所有路由
- 已移除 `/project/` 路径前缀，直接 `/{visible_path}`
- URL 重命名是 project 级（全局唯一 url_name），非目录级

**Why:** 解决 Starlette 旧版本的 request.state 不传播问题和 Windows 路径兼容
**How to apply:** 勿用 `request.state`，始终用 `request.scope`。Windows 路径用 `.replace("\\", "/")` normalize。
