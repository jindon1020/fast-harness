# test-command

## Task
提交前快速单元测试闭环：基于 git 改动自动生成单元测试并执行，产出 VERDICT: PASS 或 FAIL。适用于手动改动代码或纯对话式 AI 修改后、未经流水线的场景。

## Context

不依赖 `task_card.json`，直接从 git diff 识别改动面，复用 `unit-test-gen-agent` 的 `changed_files.txt` 输入模式，契合框架现有文件契约体系。

与流水线命令的关系：
- `/implement` / `/modify` / `/fix` — 有完整 task_card，单元测试是其中一个阶段
- `/test` — 无 task_card，只关心"当前改动的代码有没有通过验证"，是上述命令的轻量替代

### File Contracts

**Path**: `.ai/test/{branch}/`

| 文件 | 写入方 | 读取方 | 用途 |
|------|--------|--------|------|
| `changed_files.txt` | Pre-flight | unit-test-gen-agent | 本次改动文件列表 |
| `unit_test_results.md` | test-runner-agent | Debugger / 用户 | 测试执行结果 |

> `branch` 自动检测：`git rev-parse --abbrev-ref HEAD | tr '/' '_'`
>
> 同一分支多次运行会覆盖上一次的 `unit_test_results.md`，结果始终代表最新状态。

## Command Format

```
/test [scope=staged|all] [router=<name>]
```

### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `scope` | `all` | `staged` — 仅 `git diff --cached` 的暂存文件；`all` — 暂存 + 未暂存（`git diff HEAD`） |
| `router` | 自动推断 | 限定只测某个 router（如 `router=shots`），不传则覆盖改动中所有涉及的 router |

## Pre-flight

1. 检测 git 环境：
   ```bash
   git rev-parse --is-inside-work-tree 2>/dev/null || echo "NOT_GIT"
   ```
   若非 git 仓库 → 提示「/test 需要在 git 仓库中运行」并终止。

2. 获取改动文件：
   ```bash
   BRANCH=$(git rev-parse --abbrev-ref HEAD | tr '/' '_')

   # scope=staged
   git diff --cached --name-only

   # scope=all（默认）
   git diff HEAD --name-only
   # 若 HEAD 无提交（初次提交），用：
   git diff --cached --name-only
   ```

3. 若 `changed_files.txt` 为空 → AskQuestion：「未检测到任何改动文件。(A) 指定 scope=staged 查看暂存区 (B) 手动输入文件路径 (C) 取消」

4. 若传入 `router=<name>`，过滤改动列表只保留包含 `routers/{name}` 的文件（及其对应 service/dao/schema）。

5. 检查改动文件中是否包含 router 相关文件（`*router*.py` 或 `*routers*`）：
   - **包含** → 正常继续
   - **不包含** → AskQuestion：「改动文件中未检测到 router 文件（变更可能在 service/dao 层）。unit-test-gen-agent 将从改动文件推导测试入口，可能覆盖范围有限。(A) 继续 (B) 取消」

6. 写入契约文件并展示执行计划：
   ```bash
   mkdir -p .ai/test/{branch}
   # 将改动文件列表写入 changed_files.txt
   ```
   告知用户：
   「将对以下改动生成并执行单元测试：
   [展示 changed_files.txt 内容]
   → Phase 1: 生成测试（unit-test-gen-agent）
   → Phase 2: 执行测试（test-runner-agent）
   → Retry Loop（MAX=3，失败时 debugger-agent 最小化修复代码）」

## Execution Steps

### Phase 1: 生成单元测试

**Agent**: `unit-test-gen-agent` (Sub-agent)

**Prompt**:
> 请根据 `.ai/test/{branch}/changed_files.txt` 识别本次接口改动，连接本地 MySQL 查询真实数据，
> 生成 pytest 单元测试。
> 无 task_card.json，直接使用 `changed_files.txt` 作为改动来源（对应 unit-test-gen-agent 的"仅有改动列表"模式）。
> 按 router 推导目录名，持久化到 `tests/{router}/{router}_unit_test.py` 与 `tests/{router}/{router}_unit_data.yaml`。
> 若已有用例完全覆盖本次改动，输出 SKIPPED_GENERATION 并列出沿用路径。
> 输出标准 VERDICT 报告，并告知本次涉及的 router 列表和测试路径。

**Done when**: unit-test-gen-agent 输出 VERDICT（PASS / FAIL / SKIPPED_GENERATION）

**On SKIPPED_GENERATION**: 直接使用已有测试文件路径进入 Phase 2，无需重新生成。

**On block**（服务无法启动 / 数据库无法连接）: 暂停，展示阻塞原因，AskQuestion「(A) 解决后重试 (B) 终止」

---

### Phase 2: 执行测试

**Agent**: `test-runner-agent` (Sub-agent)

从 unit-test-gen-agent 的输出中解析本次涉及的 **router 列表**和对应的 **测试路径**，拼接 pytest 命令传入。

**Prompt**:
> 执行单元测试，测试类型：单元测试。
> 测试路径：{unit-test-gen-agent 输出的 router 对应路径，如 `tests/shots/ tests/canvas/`}
> 结果写入 `.ai/test/{branch}/unit_test_results.md`，输出 VERDICT。

**Verdict**: PASS → 进入最终报告 | FAIL → Retry Loop

**Retry Loop** (MAX=3):
1. 提取 `unit_test_results.md` 中失败用例的错误信息
2. 启动 `debugger-agent` (Sub-agent)，Prompt：
   > 根据以下单元测试失败信息最小化修复**业务代码**（不修改测试文件）。
   > 失败详情：[从 unit_test_results.md 提取]
   > 改动来源：`.ai/test/{branch}/changed_files.txt`
   > 只修复报告的失败点，不重构、不改风格、不改其他文件。
3. debugger-agent 修复完成 → 重新执行 Phase 2（test-runner-agent）
4. 超过 3 轮仍 FAIL → AskQuestion「已循环 3 轮，以下用例仍失败：[列出]。(A) 人工修复后重新 /test (B) 忽略失败直接提交 (C) 终止」

---

### Phase 3: 最终报告

```markdown
## ✅ /test 执行报告

**分支**: {branch}
**改动范围**: {scope=staged|all}
**涉及 Router**: {列表}

### 测试概览

| Router | 测试文件 | 用例数 | 通过率 | 状态 |
|--------|---------|--------|--------|------|
| {router} | tests/{router}/{router}_unit_test.py | {N} | {X}% | ✅/❌ |

### 生成情况

- GENERATED：新建 {N} 个 router 的测试
- APPENDED：追加 {N} 个 router 的缺口用例
- SKIPPED_GENERATION：{N} 个 router 已有用例完全覆盖，沿用既有

### VERDICT: PASS / FAIL

{[if PASS] 所有用例通过，可安全提交。}
{[if FAIL after retry] 经 {N} 轮修复仍有失败，详见 .ai/test/{branch}/unit_test_results.md}
```

**Checkpoint（仅 PASS 时）**: AskQuestion —「测试全部通过，是否直接提交？(A) 确认 commit (B) 不提交」

选 (A) 输出 commit message 建议：
```
{原改动的描述}（已通过单元测试 {N} 例）
```

## Key Principles

- **无 task_card 模式**：完全依赖 `changed_files.txt`，与 unit-test-gen-agent 的"仅有改动列表"输入路径对齐，不引入新的 agent 接口约定
- **只修复代码，不修改测试**：Retry Loop 中 debugger-agent 明确禁止改动 `tests/` 目录
- **测试持久化复用**：生成的测试文件写入 `tests/{router}/`，后续 `/implement` / `/fix` 流水线中的 unit-test-gen-agent 会自动执行覆盖扫描（步骤 7.5），识别为已覆盖并跳过重复生成
- **契约隔离**：结果文件写入 `.ai/test/{branch}/`，与 `.ai/implement/`、`.ai/fix/` 等目录完全隔离，互不干扰
- **歧义必须停下**：改动文件无法关联到 router 时主动询问，不猜测
