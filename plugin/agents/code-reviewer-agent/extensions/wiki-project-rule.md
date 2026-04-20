---
extension-point: project-rule
priority: 10
description: 从 code wiki 加载项目架构规则，作为架构合规性审查的判断基准
---

审查架构合规性时，先读取以下 wiki 文件获取项目特定规则（若 `.wiki/` 不存在则跳过）：

**分层与调用规则** — 读取 `.wiki/05-patterns.md`：
- Router 不得直接访问 DAO，必须经过 Service 层
- Service 不得导入其他 Router（循环依赖）
- DAO 不包含业务逻辑，只做数据库 CRUD
- Session 由 Router 通过 `get_db_session` 创建并向下传递，Service/DAO 不自行创建
- Router → Service 调用必须通过 `handle_service_call` 包装（统一异常处理）
- 错误处理：业务异常用 `raise BizException(ErrorCode.XXX)`，禁止 `raise HTTPException`

**接口规范** — 读取 `.wiki/02-interfaces.md`：
- 所有接口返回值必须使用 `BizResponseSchema[T]` 包装
- 权限校验失败必须返回 HTTP 200 + 业务错误码，禁止返回 HTTP 403/401
- 依赖注入使用 `get_db_session`、`get_user_id`，禁止绕过依赖注入自建 Session

将以上规则作为"维度 1：架构合规性"的项目特定判断标准，违反即标记为 Critical。
