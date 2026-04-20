---
extension-point: coding-convention
priority: 10
description: 从 code wiki 加载编码规范，确保生成代码与项目现有模式一致
---

生成代码时严格遵循以下来自 code wiki 的规范（若 `.wiki/` 不存在则跳过整个步骤）：

**架构与分层规范** — 读取 `.wiki/05-patterns.md`，应用其中定义的：
- 分层架构约定（Router → Service → DAO → Model，禁止��层调用）
- 错误处理模式（BizException + handle_service_call，禁止 raise HTTPException）
- 权限校验模式（auth_* 函数调用方式）

**接口与响应规范** — 读取 `.wiki/02-interfaces.md`，应用其中定义的：
- 统一响应格式（BizResponseSchema[T] 包装，禁止自定义格式）
- 分页响应（BasePageResponse[T]）
- 权限校验失败返回 HTTP 200 + 错误码，禁止返回 HTTP 403
- 依赖注入契约（get_db_session、get_user_id，不自行创建 Session）
