---
extension-point: test-pattern
priority: 10
description: 从 code wiki 加载响应格式约定，确保单元测试断言与项目接口规范一致
---

生成单元测试时，先读取 `.wiki/02-interfaces.md` 获取响应格式约定（若 `.wiki/` 不存在则跳过）：

**响应断言规范**：
- 成功响应：断言 `response.json()["code"] == 0`，不得断言 HTTP 200 作为唯一成功标准
- 业务错误：断言 `response.json()["code"] == <具体错误码>`，HTTP 状态码仍为 200
- 权限失败：断言 `response.json()["code"] == 3019`，**禁止**断言 `response.status_code == 403`
- 分页接口：断言 `result` 中包含 `total`、`items`、`page_index`、`page_size` 字段

**测试用例构建**：
- 用 `BizResponseSchema` 的结构验证响应，而非只检查 HTTP 状态码
- 写操作接口必须同时覆盖"有权限"和"无权限"两个用例（无权限期望 code=3019）
