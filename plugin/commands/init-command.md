# init-command

## Task
新项目首次 Code Wiki 构建：扫描代码库生成结构化知识文档，并自动配置 AI 流水线 wiki 感知扩展，使后续所有 Agent 开箱即获得项目上下文。

## Context

`/init` 是安装 fast-harness 插件后的**首次初始化命令**，负责：
1. 调用 `wiki-agent` 生成 `.wiki/` 代码知识库
2. 将 wiki 知识注入流水线三个关键扩展点：
   - `@pre-generation`（generator-agent）— 代码生成前加载模块上下文
   - `@coding-convention`（generator-agent）— 编码规范自动对齐
   - `@design-convention`（requirement-design-agent）— 接口设计基准对齐
3. 建立 MANIFEST.json 驱动的鲜度管理基础，供 `/implement` Pre-flight 检测使用

执行完成后，`/implement`、`/fix`、`/modify` 等命令启动时，其 sub-agent 将自动加载并应用 wiki 知识，无需用户每次手动提供项目上下文。

### 为什么需要 /init

| 问题 | /init 后的改变 |
|------|---------------|
| generator-agent 从零读源码推断规范 | 自动读取 `.wiki/05-patterns.md` + `02-interfaces.md` |
| requirement-design-agent 不了解现有接口契约 | 自动读取 `.wiki/02-interfaces.md` + `01-modules.md` |
| 代码生成前不知道模块现有边界 | @pre-generation 自动加载对应 wiki section |
| wiki 随代码变化逐渐过期无感知 | MANIFEST.json 追踪鲜度，`/implement` Pre-flight 自动告警 |

## Command Format

```
/init [force]
```

| 参数 | 说明 |
|------|------|
| `force` | 即使 `.wiki/` 已存在也重新全量生成（用于重大重构后刷新） |
| （无参数） | 首次初始化，自动检测并询问已有 wiki 处理策略 |

## Pre-flight

1. 检测 `.wiki/MANIFEST.json` 是否存在：
   - **不存在** → 直接进入 Step 1（首次初始化）
   - **存在且无 `force` 参数** → AskQuestion：
     「检测到 `.wiki/` 已存在（上次生成：{MANIFEST.json 中 generated_at}）。
     (A) 跳过 wiki 生成，仅重装三个扩展文件
     (B) 强制重新全量生成 wiki + 重装扩展文件
     (C) 取消」
   - **存在且有 `force` 参数** → 跳过询问，直接全量重新生成

2. 检测 `.ether/` 目录是否存在：
   - 不存在 → AskQuestion：「未检测到 `.ether/` 目录，fast-harness 可能未安装。是否继续仅生成 wiki（不配置扩展文件）？」

3. 告知用户执行计划：
   「开始 /init 初始化，将执行：
   ① wiki 生成（wiki-agent 扫描全库）
   ② generator-agent 扩展配置（@pre-generation + @coding-convention）
   ③ requirement-design-agent 扩展配置（@design-convention）
   完成后流水线 Agent 将自动感知项目代码结构。」

## Execution Steps

### Step 1: 生成 Code Wiki

使用 **Skill 工具**调用 `wiki-agent`，对当前项目根目录进行全量 wiki 生成。

wiki-agent 将在项目根目录下生成：

| 文件 | 内容 |
|------|------|
| `.wiki/00-overview.md` | 系统概览（技术栈、模块图、入口、部署） |
| `.wiki/01-modules.md` | 各模块详细说明（router/service 级别） |
| `.wiki/02-interfaces.md` | 内部接口契约（响应格式、依赖注入、权限） |
| `.wiki/03-data-flow.md` | 数据流与请求生命周期 |
| `.wiki/04-shared-code.md` | 公共工具代码 |
| `.wiki/05-patterns.md` | 架构模式与编码规范 |
| `.wiki/MANIFEST.json` | Section 鲜度追踪清单（source_hash + stale 标志） |

> 若 Pre-flight 选择了「跳过 wiki 生成」（选项 A），跳过此步骤，直接进入 Step 2。

**Done when**: `.wiki/MANIFEST.json` 文件存在且包含 `sections` 数组

---

### Step 2: 最终报告

输出初始化完成报告并更新 task 状态：

```markdown
## ✅ /init 初始化完成

### 生成的文件

**Code Wiki** (`.wiki/`)
| 文件 | 状态 |
|------|------|
| `00-overview.md` | ✅ 系统概览 |
| `01-modules.md` | ✅ 模块文档（{N} 个模块） |
| `02-interfaces.md` | ✅ 接口契约 |
| `03-data-flow.md` | ✅ 数据流 |
| `04-shared-code.md` | ✅ 公共代码 |
| `05-patterns.md` | ✅ 架构模式 |
| `MANIFEST.json` | ✅ 鲜度追踪（{N} 个 section） |

> 流水线 wiki 扩展文件（`@pre-generation`、`@coding-convention`、`@design-convention`）
> 已随插件安装时写入 `.ether/agents/*/extensions/`，无需手动创建。

### 流水线效果预览

| 阶段 | 之前 | 之后 |
|------|------|------|
| 需求设计（Phase 0） | Agent 自行推断现有接口规范 | 自动读取 `.wiki/02-interfaces.md` 对齐接口契约 |
| 代码生成前（Step 1） | 从零读源码理解模块边界 | `@pre-generation` 自动加载对应 wiki section |
| 代码生成（Step 2） | 依赖 Agent 记忆应用规范 | `@coding-convention` 自动注入规范约束 |

### 下一步

- `/implement` 等命令在 Pre-flight 阶段会自动检测 wiki 是否过期（基于 MANIFEST.json）
- 当积累大量代码变更后，运行 `/init force` 重新全量刷新 wiki
- `.wiki/` 建议提交到 git，作为项目知识资产持续维护
```

## Key Principles

- **幂等操作**：重复执行只覆盖扩展文件，不损坏已有代码或 wiki
- **wiki 属于项目资产**：`.wiki/` 建议提交 git，扩展文件写入 `.ether/`（与代码分离，不进 git）
- **按需读取**：扩展文件指示 agent 读取特定 wiki section，不做全量加载
- **鲜度自愈**：`/implement` Pre-flight 检测到 stale section 时主动提示，wiki 不会静默腐化
