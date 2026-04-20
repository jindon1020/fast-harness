---
extension-point: pre-generation
priority: 5
description: 从 code wiki 加载模块上下文，生成前了解项目结构与模块边界
---

生成代码前，先从 code wiki 获取项目知识（若 `.wiki/` 不存在则跳过整个步骤）���

1. 读取 `.wiki/00-overview.md`，了解整体架构、技术栈、模块图
2. 根据 task_card.json 中的 `affected_files` 推导涉及的模块名
   （如 `shots`、`canvas`），在 `.wiki/01-modules.md` 中定位对应的
   `<!-- SECTION: {module} -->` 块并读取，了解该模块的现有功能边界
3. 读取 `.wiki/03-data-flow.md`，了解请求链路和数据流

加载后将 wiki 知识作为代码生成的背景约束，确保新代码与现有模块边界一致，
不重复实现已有功能，不破坏现有数据流。
