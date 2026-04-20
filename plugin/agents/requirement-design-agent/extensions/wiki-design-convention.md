---
extension-point: design-convention
priority: 5
description: 从 code wiki 加载接口设计规范，确保新 API 与现有契约对齐
---

设计 API 和数据模型前，先读取以下 wiki 文件作为设计基准（若 `.wiki/` 不存在则跳过整个步骤）：

**接口契约对齐** — 读取 `.wiki/02-interfaces.md`：
- 新 API 必须使用 BizResponseSchema[T] 包装响应，禁止自定义响应格式
- 权限校验失败统一返回 HTTP 200 + 业务错误码，禁止返回 HTTP 403
- 依赖注入遵循 get_db_session + get_user_id 模式

**模块边界确认** — 读取 `.wiki/01-modules.md`：
- 设计前确认目标模块的现有功能边界，避免重复实现已有接口
- 跨模块数据获取须通过目标模块的 Service 层，不直接访问其他模块的 DAO

**架构约束** — 读取 `.wiki/00-overview.md`：
- 新设计须与现有技术栈保持一致（框架、ORM、认证方式）
- 外部服务调用通过 gateways/ 封装，不在 Service 层直接发起 HTTP 调用
