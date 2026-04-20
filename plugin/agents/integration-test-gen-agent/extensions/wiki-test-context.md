---
extension-point: test-context
priority: 10
description: 从 code wiki 加载响应格式与请求链路，确保集成测试断言与项目接口规范一致
---

生成集成测试前，先读取以下 wiki 文件（若 `.wiki/` 不存在则跳过）：

**响应断言规范** — 读取 `.wiki/02-interfaces.md`：
- 成功响应：断言 `response.json()["code"] == 0`
- 权限失败：断言 `response.json()["code"] == 3019`，**禁止**断言 `status_code == 403`
- 业务错误：断言具体的 `code` 值，而非只断言 HTTP 状态码非 200
- 分页接口：断言 `result` 字段包含 `total`、`items`、`page_index`、`page_size`

**测试场景设计** — 读取 `.wiki/03-data-flow.md`：
- 了解请求完整链路，确保集成测试覆盖关键中间节点（如 AI 工作流场景需验证异步回调）
- 涉及多步骤业务流程时，按 wiki 中的数据流顺序设计测试前置条件

**场景覆盖要求**：
- 每个写操作接口必须包含权限校验场景（期望 code=3019）
- AI 工作流相关接口需覆盖触发→轮询→结果验证的完整流程
