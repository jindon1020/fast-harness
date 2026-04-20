---
extension-point: diagnosis-strategy
priority: 5
description: 从 code wiki 加载请求链路与模块边界，辅助定位 Bug 根因
---

开始诊断前，先从 code wiki 建立调用链路认知（若 `.wiki/` 不存在则跳过）：

**请求生命周期** — 读取 `.wiki/03-data-flow.md`：
- 了解一次请求从入口到响应的完整链路（中间件 → Router → Service → DAO → DB）
- 掌握 AI 工作流链路（workflow_service → algo_manager_gateway → 异步回调）
- 定位 Bug 时沿着此链路逐层排查，而不是盲猜

**模块边界** — 读取 `.wiki/01-modules.md`：
- 确认出问题的接口属于哪个模块（episodes/shots/canvas/workflow 等）
- 了解该模块的 Service 与 DAO 的职责边界，判断 Bug 是在业务层还是数据层
- 跨模块调用异常时，确认调用方向是否符合架构约定

将以上链路知识作为 `@diagnosis-strategy` 的额外诊断维度：
优先沿 wiki 中描述的调用链路逐层验证，缩小根因范围后再读源码。
