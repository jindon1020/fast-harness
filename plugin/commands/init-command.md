# init-command

## Task
新项目首次 Code Wiki 构建：扫描代码库生成结构化知识文档，并自动配置 AI 流水线 wiki 感知扩展，使后续所有 Agent 开箱即获得项目上下文。

## Context

`/init` 是安装 fast-harness 插件后的**首次初始化命令**，负责：
1. 调用 `code-wiki-gen` 生成 `.wiki/` 代码知识库
2. 引导项目维护者录入历史遗留问题、架构缺陷与技术债务，生成 `.wiki/06-legacy-issues.md`
3. 将 wiki 知识注入流水线三个关键扩展点：
   - `@pre-generation`（generator-agent）— 代码生成前加载模块上下文
   - `@coding-convention`（generator-agent）— 编码规范自动对齐
   - `@design-convention`（requirement-design-agent）— 接口设计基准对齐
4. 建立 MANIFEST.json 驱动的鲜度管理基础，供 `/implement` Pre-flight 检测使用

执行完成后，`/implement`、`/fix`、`/modify` 等命令启动时，其 sub-agent 将自动加载并应用 wiki 知识，无需用户每次手动提供项目上下文。

### 为什么需要 /init

| 问题 | /init 后的改变 |
|------|---------------|
| generator-agent 从零读源码推断规范 | 自动读取 `.wiki/05-patterns.md` + `02-interfaces.md` |
| requirement-design-agent 不了解现有接口契约 | 自动读取 `.wiki/02-interfaces.md` + `01-modules.md` |
| 代码生成前不知道模块现有边界 | @pre-generation 自动加载对应 wiki section |
| wiki 随代码变化逐渐过期无感知 | MANIFEST.json 追踪鲜度，`/implement` Pre-flight 自动告警 |
| 历史债务与架构缺陷散落在口口相传中 | 结构化录入 `.wiki/06-legacy-issues.md`，Agent 生成时自动规避已知坑点 |

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
   ① wiki 生成（code-wiki-gen 扫描全库）
   ② 历史问题收集（引导维护者录入遗留问题 / 架构缺陷 / 技术债务）
   ③ generator-agent 扩展配置（@pre-generation + @coding-convention）
   ④ requirement-design-agent 扩展配置（@design-convention）
   完成后流水线 Agent 将自动感知项目代码结构与已知风险点。」

## Execution Steps

### Step 1: 生成 Code Wiki

使用 **Skill 工具**调用 `code-wiki-gen`，对当前项目根目录进行全量 wiki 生成。

code-wiki-gen 将在项目根目录下生成：

| 文件 | 内容 |
|------|------|
| `.wiki/00-overview.md` | 系统概览（技术栈、模块图、入口、部署） |
| `.wiki/01-modules.md` | 各模块详细说明（router/service 级别） |
| `.wiki/02-interfaces.md` | 内部接口契约（响应格式、依赖注入、权限） |
| `.wiki/03-data-flow.md` | 数据流与请求生命周期 |
| `.wiki/04-shared-code.md` | 公共工具代码 |
| `.wiki/05-patterns.md` | 架构模式与编码规范 |
| `.wiki/MANIFEST.json` | Section 鲜度追踪清单（source_hash + stale 标志） |

> 若 Pre-flight 选择了「跳过 wiki 生成」（选项 A），跳过此步骤，直接进入 Step 1.5。

**Done when**: `.wiki/MANIFEST.json` 文件存在且包含 `sections` 数组

---

### Step 1.5: 收集历史遗留问题

引导项目维护者补充代码库的**已知问题**，这些信息无法从源码静态分析得出，只存在于团队认知中。

#### 交互式收集

依次向用户提问（每类可多条，回复「跳过」则略过该类）：

```
① 遗留问题（Legacy Issues）
   「请描述项目中已知但暂未修复的 Bug 或功能缺陷，例如：
     - 某接口在并发场景下偶发数据不一致
     - 分页逻辑在总数为 0 时返回错误状态码」

② 架构缺陷（Architecture Defects）
   「请描述当前架构设计上的不合理之处，例如：
     - Service 层直接操作 HTTP Request 对象，导致单元测试困难
     - 权限校验散落在各 router，缺乏统一中间件」

③ 历史债务（Technical Debt）
   「请描述明确需要重构但被推迟的模块或实现，例如：
     - auth 模块用 session 实现，计划迁移为 JWT 但未排期
     - 数据库查询未做索引优化，高并发下存在慢查询风险」
```

若用户三类均跳过，仍生成空结构的 `06-legacy-issues.md`（保留占位，便于后续 `/wiki-update issues=...` 追加）。

#### 生成 `.wiki/06-legacy-issues.md`

将收集到的内容按以下模板写入文件：

```markdown
# Legacy Issues

> 本文件记录项目中已知的遗留问题、架构缺陷与技术债务。
> 由 `/init` 初始化时人工录入，可通过 `/wiki-update issues=...` 持续追加。
> Agent 在生成代码前应读取本文件，主动规避已知风险点。

<!-- SECTION: legacy-issues -->

## 遗留问题（Legacy Issues）

{用户录入内容，每条格式如下}
- **[LI-001]** {问题描述}（录入时间：{date}）

## 架构缺陷（Architecture Defects）

- **[AD-001]** {缺陷描述}（录入时间：{date}）

## 历史债务（Technical Debt）

- **[TD-001]** {债务描述}（录入时间：{date}）

<!-- /SECTION: legacy-issues -->
```

**Done when**: `.wiki/06-legacy-issues.md` 写入完成

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
| `06-legacy-issues.md` | ✅ 历史遗留问题（{N} 条） |
| `MANIFEST.json` | ✅ 鲜度追踪（{N} 个 section） |

> 流水线 wiki 扩展文件（`@pre-generation`、`@coding-convention`、`@design-convention`）
> 已随插件安装时写入 `.ether/agents/*/extensions/`，无需手动创建。

### 流水线效果预览

| 阶段 | 之前 | 之后 |
|------|------|------|
| 需求设计（Phase 0） | Agent 自行推断现有接口规范 | 自动读取 `.wiki/02-interfaces.md` 对齐接口契约 |
| 代码生成前（Step 1） | 从零读源码理解模块边界 | `@pre-generation` 自动加载对应 wiki section |
| 代码生成（Step 2） | 依赖 Agent 记忆应用规范 | `@coding-convention` 自动注入规范约束 |
| 历史债务感知 | Agent 不知道已知坑点 | 自动读取 `.wiki/06-legacy-issues.md` 规避已知风险 |

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
