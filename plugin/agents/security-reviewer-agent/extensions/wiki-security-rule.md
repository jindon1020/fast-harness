---
extension-point: security-rule
priority: 10
description: 从 code wiki 加载项目权限模式，用于识别鉴权绕过漏洞
---

审查鉴权安全时，先读取 `.wiki/05-patterns.md` 获取本项目的权限校验模式（若 `.wiki/` 不存在则跳过）：

**项目鉴权约定**：
- 每个需要权限控制的 Router 函数必须调用 `auth_*` 系列函数（如 `auth_project`、`auth_episode` 等）
- 鉴权结果检查：`if not auth_result.success` → 返回 `BizResponseSchemaFactory.custom_error(...)`
- 禁止在 Service 层做权限判断（权限必须在 Router 层完成）
- 权限校验失败返回 HTTP 200 + 错误码 3019，若代码返回 HTTP 403/401 则为规范违反

**鉴权绕过判定**：
- 新增的写操作接口（POST/PUT/DELETE）若缺少 `auth_*` 调用 → **Critical: 鉴权绕过**
- `auth_result.success` 检查后未提前返回直接继续执行 → **Critical: 鉴权逻辑缺陷**
