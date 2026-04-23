# wiki-update-command

## Task
手动触发 wiki 增量更新：基于 git diff 或用户指定的文件列表，调用 `code-wiki-gen` skill 的增量更新流程，外科手术式更新受影响的 wiki sections；同时支持通过 `issues` 参数将用户描述的历史问题追加到 `.wiki/06-legacy-issues.md`。

## Context

与 `/init` 的区别：
- `/init` — 全量生成或强制刷新整个 `.wiki/`，并交互式收集历史遗留问题
- `/wiki-update` — 增量更新变化的 sections，或快速追加新的历史问题记录

适用场景：
- 用户手动改了代码，想立即更新 wiki（不等 git commit 触发 hook）
- git hook 的 LLM 模式未启用，用户想手动触发一次完整更新
- 积累了多个 stale sections，想批量刷新
- 新发现了 Bug、架构缺陷或技术债务，想快速补录到历史问题 wiki

### File Contracts

**Path**: 无（不依赖 `.ai/` 目录，直接操作 `.wiki/`）

| 文件 | 读取方 | 写入方 | 用途 |
|------|--------|--------|------|
| `.wiki/MANIFEST.json` | code-wiki-gen | code-wiki-gen | 追踪 sections 的 source_files 和 stale 状态 |
| `.wiki/*.md` | code-wiki-gen | code-wiki-gen | wiki 内容文件，通过 `<!-- SECTION: id -->` 标记定位更新范围 |
| `.wiki/06-legacy-issues.md` | /wiki-update | /wiki-update | 历史遗留问题记录，`issues` 模式下追加写入 |

## Command Format

```
/wiki-update [files=<path1,path2>] [force]
/wiki-update issues=<问题描述文本>
```

### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `files` | 自动检测 | 逗号分隔的文件路径列表，如 `files=src/auth/service.py,src/drama/router.py`；不传则用 `git diff HEAD --name-only` |
| `force` | false | 即使 hash 未变化也强制重新生成对应 sections |
| `issues` | — | 用自然语言描述新发现的历史问题（遗留 Bug / 架构缺陷 / 技术债务），追加到 `.wiki/06-legacy-issues.md`；与 `files` / `force` 互斥，传入后直接进入 Issues 模式 |

> **两种运行模式**
> - **代码更新模式**（默认）：`files` / `force` 参数 → 走 Pre-flight + Step 1 增量更新流程
> - **Issues 追加模式**：`issues` 参数 → 跳过 Pre-flight，直接执行 Step 0 后结束

## Execution Steps（Issues 追加模式）

> 仅当传入 `issues` 参数时执行此流程，完成后**不执行**后续代码更新流程。

### Step 0: 追加历史问题到 `06-legacy-issues.md`

1. 检测 `.wiki/06-legacy-issues.md` 是否存在：
   - **不存在** → 提示「历史问题文件未找到，请先运行 /init 初始化」并终止
   - **存在** → 继续

2. 分析 `issues` 参数中的描述，自动判断问题类型：
   - 包含 Bug、异常、错误、不一致、偶发等关键词 → **遗留问题（LI）**
   - 包含架构、设计、耦合、测试困难、中间件等关键词 → **架构缺陷（AD）**
   - 包含重构、迁移、优化、债务、排期等关键词 → **历史债务（TD）**
   - 无法判断 → AskQuestion：「请确认该问题属于哪类：(A) 遗留问题 (B) 架构缺陷 (C) 历史债务」

3. 读取 `.wiki/06-legacy-issues.md`，找到 `<!-- SECTION: legacy-issues -->` 标记块，在对应分类末尾追加新条目：

   ```markdown
   - **[LI-{N+1}]** {用户描述的问题内容}（录入时间：{当前日期}）
   ```

   编号规则：读取当前分类已有的最大编号，自增 1。

4. 输出追加结果：

   ```markdown
   ## ✅ 历史问题已追加

   **类型**: 遗留问题 / 架构缺陷 / 历史债务
   **编号**: LI-003
   **内容**: {用户描述}
   **写入位置**: `.wiki/06-legacy-issues.md`

   > 提示：Agent 在下次 `/implement` 时将自动感知此问题并主动规避。
   ```

---

## Pre-flight（代码更新模式）

> `issues` 参数存在时跳过此节，直接执行 Step 0。

1. 检测 `.wiki/MANIFEST.json` 是否存在：
   - **不存在** → 提示「wiki 未初始化，请先运行 /init」并终止
   - **存在** → 继续

2. 获取变更文件列表：
   ```bash
   # 若用户传入 files 参数
   CHANGED_FILES="src/auth/service.py,src/drama/router.py"
   
   # 若未传入，自动检测
   git diff HEAD --name-only
   # 若 working tree clean，则检测最近一次 commit
   git diff HEAD~1 HEAD --name-only
   ```

3. 若 `CHANGED_FILES` 为空 → AskQuestion：「未检测到任何改动文件。(A) 手动输入文件路径 (B) 取消」

4. 加载 MANIFEST.json，查找受影响的 sections：
   - 对每个 changed file，找到 `source_files` 包含它的 sections
   - 输出受影响的 sections 列表

5. 告知用户执行计划：
   「将更新以下 wiki sections：
   [列出 wiki_file#section_id]
   → 调用 code-wiki-gen skill 增量更新模式
   → 更新 MANIFEST.json 的 source_hash 和 last_verified_commit」

## Execution Steps

### Step 1: 调用 code-wiki-gen 增量更新

**使用 Skill 工具**调用 `code-wiki-gen`，传入增量更新参数：

**Prompt**:
> 请对以下文件执行 wiki 增量更新：
> {CHANGED_FILES 列表}
> 
> 参考 `references/update.md` 的 6 步流程：
> 1. 加载 MANIFEST.json，找到受影响的 sections
> 2. 读取变更文件，理解功能变化
> 3. 使用 `<!-- SECTION: id -->` 标记外科手术式替换对应 wiki 内容
> 4. 重新计算 source_hash 并更新 MANIFEST.json
> 5. 标记下游依赖的 sections 为 stale（若共享模块变化）
> 
> 输出更新摘要：哪些 sections 被重写，哪些被标记为 stale。

**Done when**: code-wiki-gen 输出更新完成报告

---

### Step 2: 最终报告

```markdown
## ✅ /wiki-update 执行报告

**变更文件**: {N} 个
{列出文件路径}

**更新的 sections**: {N} 个
| Wiki 文件 | Section ID | 状态 |
|----------|-----------|------|
| 01-modules.md | drama-module | ✅ 已更新 |
| 02-interfaces.md | internal-api-contracts | ✅ 已更新 |

**标记为 stale 的 sections**: {N} 个
| Wiki 文件 | Section ID | 原因 |
|----------|-----------|------|
| 03-data-flow.md | auth-flow | 依赖 common/auth/service.py 变化 |

### 下一步

- 运行 `/implement` 时 Pre-flight 将不再报告这些 sections 过期
- 若有 stale sections，可再次运行 `/wiki-update` 或 `/init force` 全量刷新
```

## Key Principles

- **双模式设计**：`issues` 参数触发历史问题追加模式，其余参数触发代码增量更新模式，互不干扰
- **无 task_card 模式**：完全依赖 git diff 或用户指定的 files 参数
- **外科手术式更新**：只重写变化的 sections，不动其他内容
- **MANIFEST.json 驱动**：通过 source_files 映射找到受影响范围
- **下游传播**：共享模块变化时自动标记依赖方为 stale
- **幂等操作**：重复执行只更新 hash 变化的 sections
- **问题自动分类**：根据描述关键词推断问题类型，无法判断时主动询问，不强迫用户手动指定前缀
