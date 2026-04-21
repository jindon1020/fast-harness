# wiki-update-command

## Task
手动触发 wiki 增量更新：基于 git diff 或用户指定的文件列表，调用 `code-wiki-gen` skill 的增量更新流程，外科手术式更新受影响的 wiki sections。

## Context

与 `/init` 的区别：
- `/init` — 全量生成或强制刷新整个 `.wiki/`
- `/wiki-update` — 增量更新，只重写变化的 sections

适用场景：
- 用户手动改了代码，想立即更新 wiki（不等 git commit 触发 hook）
- git hook 的 LLM 模式未启用，用户想手动触发一次完整更新
- 积累了多个 stale sections，想批量刷新

### File Contracts

**Path**: 无（不依赖 `.ai/` 目录，直接操作 `.wiki/`）

| 文件 | 读取方 | 写入方 | 用途 |
|------|--------|--------|------|
| `.wiki/MANIFEST.json` | code-wiki-gen | code-wiki-gen | 追踪 sections 的 source_files 和 stale 状态 |
| `.wiki/*.md` | code-wiki-gen | code-wiki-gen | wiki 内容文件，通过 `<!-- SECTION: id -->` 标记定位更新范围 |

## Command Format

```
/wiki-update [files=<path1,path2>] [force]
```

### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `files` | 自动检测 | 逗号分隔的文件路径列表，如 `files=src/auth/service.py,src/drama/router.py`；不传则用 `git diff HEAD --name-only` |
| `force` | false | 即使 hash 未变化也强制重新生成对应 sections |

## Pre-flight

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

- **无 task_card 模式**：完全依赖 git diff 或用户指定的 files 参数
- **外科手术式更新**：只重写变化的 sections，不动其他内容
- **MANIFEST.json 驱动**：通过 source_files 映射找到受影响范围
- **下游传播**：共享模块变化时自动标记依赖方为 stale
- **幂等操作**：重复执行只更新 hash 变化的 sections
