---
name: integration-test-command
description: 提交前快速集成测试闭环
skill: ahe-observer
---

# integration-test-command

## Task
提交前快速集成测试闭环：基于 git 改动和测试用例描述（xmind/yaml），自动生成集成测试并执行，产出 VERDICT: PASS 或 FAIL。适用于接口变更后需验证跨模块集成行为的场景。

## Context

支持两种测试用例描述输入——xmind 脑图（结构化用例）或 yaml 描述文件（轻量用例），配合 `changed_files.txt` 识别改动面，复用 `integration-test-gen-agent` 的 xmind/yaml 解析能力，契合框架现有文件契约体系。

与流水线命令的关系：
- `/implement` / `/modify` — 有完整 task_card，集成测试是其中的可选阶段（需显式启用）
- `/integration-test` — 无 task_card，只关心"改动涉及的接口集成行为是否正常"，是上述命令中集成测试阶段的独立可执行版本

### File Contracts

**Path**: `.ai/integration-test/{branch}/`

| 文件 | 写入方 | 读取方 | 用途 |
|------|--------|--------|------|
| `changed_files.txt` | Pre-flight | integration-test-gen-agent | 本次改动文件列表 |
| `test_case_input` | Pre-flight（复制自 xmind/yaml） | integration-test-gen-agent | 测试用例描述 |
| `integration_test_results.md` | test-runner-agent | Debugger / 用户 | 测试执行结果 |

> `branch` 自动检测：`git rev-parse --abbrev-ref HEAD | tr '/' '_'`
>
> 同一分支多次运行会覆盖上一次的 `integration_test_results.md`，结果始终代表最新状态。

## Command Format

```
/integration-test [xmind=<path>] [yaml=<path>]
```

> 流水线参数（`module`、`scope`）不再通过命令行传入，改为 Pre-flight 阶段通过 `AskUserQuestion` 主动询问用户。若用户输入中已包含参数值（如 `/integration-test scope=staged`）则跳过对应询问。`xmind` 和 `yaml` 也可在 Pre-flight 交互选择。

### 参数（Pre-flight 交互收集）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `xmind` | - | xmind 脑图文件路径，包含结构化集成测试用例。与 `yaml` 二选一 |
| `yaml` | - | yaml 描述文件路径，包含集成测试用例定义（场景、步骤、断言）。与 `xmind` 二选一 |
| `module` | 自动推断 | 模块名。影响测试文件命名：`tests/{branch}/{module}_api_test.py` |
| `scope` | `all` | `staged` — 仅 `git diff --cached` 的暂存文件；`all` — 暂存 + 未暂存（`git diff HEAD`） |

> 若 `xmind` 和 `yaml` 均未传入且无已有 `changed_files.txt`，命令将询问用户提供测试用例来源。

## Pre-flight

1. 检测 git 环境：
   ```bash
   git rev-parse --is-inside-work-tree 2>/dev/null || echo "NOT_GIT"
   ```
   若非 git 仓库 → 提示「/integration-test 需要在 git 仓库中运行」并终止。

2. **交互收集参数**：若用户未在命令中指定以下参数，通过 `AskUserQuestion` 依次询问：
   - **测试用例来源**（若 `xmind` 和 `yaml` 均未传入且 `.ai/integration-test/{branch}/test_case_input` 不存在）：「未指定测试用例来源。(A) 提供 xmind 路径 (B) 提供 yaml 路径 (C) 取消」
   - **scope**：「请选择改动范围。(A) all — 暂存 + 未暂存 (B) staged — 仅暂存区」
     - 默认 `all`，用户选 B 时 `scope=staged`
   - **module**（若无法自动推断）：「请指定目标模块名」

3. 校验测试用例输入：
   - `xmind=<path>` 且文件存在 → 复制到 `.ai/integration-test/{branch}/test_case_input`，标记 `input_type=xmind`
   - `yaml=<path>` 且文件存在 → 复制到 `.ai/integration-test/{branch}/test_case_input`，标记 `input_type=yaml`
   - 均未传入 → 检查 `.ai/integration-test/{branch}/test_case_input` 是否存在（复用上次），若无则已在上一步 AskQuestion 处理

4. 获取改动文件：
   ```bash
   BRANCH=$(git rev-parse --abbrev-ref HEAD | tr '/' '_')

   # scope=staged
   git diff --cached --name-only

   # scope=all（默认）
   git diff HEAD --name-only
   # 若 HEAD 无提交（初次提交），用：
   git diff --cached --name-only
   ```

5. 若改动文件列表为空 → AskQuestion：「未检测到任何改动文件。(A) 指定 scope=staged 查看暂存区 (B) 手动输入文件路径 (C) 取消」

6. 写入契约文件并展示执行计划：
   ```bash
   mkdir -p .ai/integration-test/{branch}
   # 将改动文件列表写入 changed_files.txt
   # 若传入 xmind 或 yaml，复制到 test_case_input
   ```
   告知用户：
   「将对以下改动生成并执行集成测试：
   **模块**: {module}
   **测试用例来源**: {xmind 路径 / yaml 路径 / 复用上次 test_case_input}
   **改动范围**:
   [展示 changed_files.txt 内容]
   → Phase 1: 生成集成测试（integration-test-gen-agent）
   → Phase 2: 执行集成测试（test-runner-agent）
   → Retry Loop（MAX=3，失败时 debugger-agent 最小化修复代码）」

7. **AHE 轨迹初始化**：
   ```bash
   mkdir -p .ai/harness-trace
   python3 -c "
   import json, time, uuid
   meta = {
       'trace_id': str(uuid.uuid4()),
       'command': 'integration-test',
       'module': '\$module',
       'branch': '\$BRANCH',
       'input_type': '\$input_type',
       'scope': '\$scope',
       'preflight_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'preflight_done': False,
       'phase_events': [],
       'verdicts': []
   }
   with open('.ai/harness-trace/.preflight_meta.json', 'w') as f:
       json.dump(meta, f, indent=2)
   "
   ```
   > **AHE**: Observer Skill 读取此文件，在 Command 执行完毕后生成轨迹。

8. **AHE Pre-flight 完成标记**：
   ```bash
   python3 -c "
   import json, time
   with open('.ai/harness-trace/.preflight_meta.json') as f:
       meta = json.load(f)
   meta['preflight_done'] = True
   with open('.ai/harness-trace/.preflight_meta.json', 'w') as f:
       json.dump(meta, f, indent=2)
   "
   ```

## Execution Steps

> **AHE Phase 事件**：每个 Phase 开始前，Command 框架自动向 `.ai/harness-trace/.preflight_meta.json` 追加 `phase_events` 记录。

### Phase 1: 生成集成测试

**Agent**: `integration-test-gen-agent` (Sub-agent)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须通过 Sub-agent 委托执行。
> Planner 禁止自行解析 xmind/yaml 或直接生成集成测试文件。
> 未收到 integration-test-gen-agent 的书面 VERDICT 响应前，禁止进入 Phase 2。

**Prompt**:
> 请根据 `.ai/integration-test/{branch}/changed_files.txt` 识别本次接口改动范围，结合测试用例描述生成 pytest 集成测试。
> 测试用例描述：`.ai/integration-test/{branch}/test_case_input`（格式：{input_type}）。
> 无 task_card.json，基于 changed_files.txt 和测试用例描述独立分析接口契约和调用链路。
> 按 module 推导输出路径，持久化到 `tests/{branch}/{module}_api_test.py` 与 `tests/{branch}/{module}_test_data.yaml`。
> 若已有集成测试文件，增量追加缺失用例（不整文件覆盖），标记 `@pytest.mark.integration`。
> 输出标准 VERDICT 报告，并告知生成的测试文件和用例数。

**Done when**: integration-test-gen-agent 输出 VERDICT（PASS / FAIL / SKIPPED_GENERATION）

**On SKIPPED_GENERATION**: 直接使用已有测试文件路径进入 Phase 2，无需重新生成。

**On block**（服务无法启动 / 无法解析测试用例）: 暂停，展示阻塞原因，AskQuestion「(A) 解决后重试 (B) 终止」

---

### Phase 2: 执行测试

**Agent**: `test-runner-agent` (Sub-agent)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须通过 Sub-agent 委托执行。
> Planner 禁止自行执行 pytest 命令或替代 test-runner-agent 输出测试结果。
> 未收到 test-runner-agent 的书面 VERDICT 响应前，禁止进入最终报告。

从 integration-test-gen-agent 的输出中解析测试文件路径，拼接 pytest 命令传入。

**Prompt**:
> 执行集成测试，测试类型：集成测试。
> 测试路径：{integration-test-gen-agent 输出的测试文件路径，如 `tests/{branch}/{module}_api_test.py`}
> 结果写入 `.ai/integration-test/{branch}/integration_test_results.md`，输出 VERDICT。

**Verdict**: PASS → 进入最终报告 | FAIL → Retry Loop

**Retry Loop** (MAX=3):
1. 提取 `integration_test_results.md` 中失败用例的错误信息
2. 启动 `debugger-agent` (Sub-agent)，Prompt：
   > 根据以下集成测试失败信息最小化修复**业务代码**（不修改测试文件）。
   > 失败详情：[从 integration_test_results.md 提取]
   > 改动来源：`.ai/integration-test/{branch}/changed_files.txt`
   > 只修复报告的失败点，不重构、不改风格、不改其他文件。
   > 若失败由测试用例与接口契约不匹配引起（非代码缺陷），标注 TEST_CASE_MISMATCH 并建议用户更新测试用例描述。
3. debugger-agent 修复完成 → 重新执行 Phase 2（test-runner-agent）
4. 超过 3 轮仍 FAIL → AskQuestion「已循环 3 轮，以下用例仍失败：[列出]。(A) 人工修复后重新 /integration-test (B) 忽略失败直接提交 (C) 终止」

> **AHE**: 每次 Retry Loop 触发时，记录 `{"phase": "Phase 2", "event": "retry", "retry_count": N}` 到轨迹 `phase_events` 中。

---

### Phase 3: 最终报告

```markdown
## ✅ /integration-test 执行报告

**分支**: {branch}
**模块**: {module}
**改动范围**: {scope=staged|all}
**测试用例来源**: {xmind 路径 / yaml 路径}

### 测试概览

| 模块 | 测试文件 | 用例数 | 通过率 | 状态 |
|------|---------|--------|--------|------|
| {module} | tests/{branch}/{module}_api_test.py | {N} | {X}% | ✅/❌ |

### 生成情况

- GENERATED：新建集成测试 {N} 个用例
- APPENDED：追加 {N} 个缺口用例
- SKIPPED_GENERATION：已有用例完全覆盖，沿用既有

### VERDICT: PASS / FAIL

{[if PASS] 所有集成测试用例通过，接口集成行为正常。}
{[if FAIL after retry] 经 {N} 轮修复仍有失败，详见 .ai/integration-test/{branch}/integration_test_results.md}

### AHE 轨迹信息
- **轨迹文件**：`.ai/harness-trace/{trace_id}_integration-test_{branch}.jsonl`
- **分析触发**：执行 `/ahe-analyze limit=30` 进行根因分析
- **演化触发**：分析后执行 `/ahe-evo apply <candidate_id>` 应用改进候选
```

🔴 **HARD STOP — 人类确认卡点**
**必须执行 AskQuestion**：「集成测试全部通过，是否直接提交？(A) 确认 commit (B) 不提交」
禁止推断用户意图自动继续。未收到用户明确回复前，流水线在此终止等待。

选 (A) 输出 commit message 建议：
```
{原改动的描述}（已通过集成测试 {N} 例）
```

## Key Principles

- **xmind/yaml 双输入**: 支持 xmind 脑图（结构化用例）和 yaml 描述文件（轻量场景描述），适配不同测试设计习惯
- **无 task_card 模式**: 基于 `changed_files.txt` 和测试用例描述独立工作，不依赖 task_card.json
- **只修复代码，不修改测试**: Retry Loop 中 debugger-agent 明确禁止改动 `tests/` 目录；若失败源于测试用例与契约不匹配则标注 TEST_CASE_MISMATCH 交由用户决策
- **测试持久化复用**: 生成的集成测试文件写入 `tests/{branch}/`，增量追加不整文件覆盖，后续流程可复用
- **契约隔离**: 结果文件写入 `.ai/integration-test/{branch}/`，与 `.ai/implement/`、`.ai/fix/`、`.ai/unit-test/` 等目录完全隔离，互不干扰
- **歧义必须停下**: 测试用例描述不完整或改动无法关联到接口时主动询问，不猜测

### 禁止行为（无论任务复杂度如何，一律适用）
- 禁止以「测试简单」「改动很小」为由跳过标注 (Sub-agent) 的步骤
- 禁止 Planner 自行解析 xmind/yaml 或执行 pytest（即便能力上可行）
- 禁止在缺少测试用例描述（xmind/yaml）时猜测用例内容
- 禁止自动通过 HARD STOP 卡点，必须等待用户明确响应
- 禁止在未收到 Phase 1 VERDICT 的情况下直接进入 Phase 2
- 禁止在未收到 Phase 2 VERDICT 的情况下输出最终报告
