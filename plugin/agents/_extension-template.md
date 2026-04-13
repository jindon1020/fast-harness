---
extension-point: data-source          # 必填：挂载到哪个扩展点（参见各 Agent 的 Available Extension Points）
name: my-custom-extension             # 必填：扩展名称（英文，kebab-case）
description: 一句话描述扩展功能         # 必填：简述
priority: 10                          # 可选：执行优先级，数字越小越先执行（默认 10）
requires-config: redis.local          # 可选：依赖的 infrastructure.json 配置段（如 mysql.dev、redis.local）
---

## 扩展标题

### 触发条件

描述在什么场景下应该触发此扩展的执行逻辑。

### 执行步骤

1. 第一步操作说明
2. 第二步操作说明

### 命令模板

```bash
# 示例命令，可引用 infrastructure.json 中的配置变量
# 变量引用格式：从 fast-harness/config/infrastructure.json 的 requires-config 段读取
```

### 结果解读

说明执行结果如何解读和使用。
