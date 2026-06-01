---
name: fix-command
description: Bug 修复闭环流水线
skill: ahe-observer
---

# fix-command

## Task
Bug 修复闭环流水线：问题收集 → 诊断修复 → GAN 对抗审查 → 回归测试，产出通过全部测试的修复代码。

## Context

基于 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 三体架构：Debugger → Reviewer → Tester。
- 定位：修复已有代码的 Bug（行为修正），区别于 implement（新建）/ modify（行为变更）/ refactor（行为不变）
- GAN 分离：修复代码同样需要独立审查，防止"修了一个 Bug 引入两个新 Bug"
- Context Reset：Agent 间通过文件契约传递状态，不依赖对话历史

### Bug 来源分类

| 来源 | 输入特征 | 自动关联 |
|------|----------|----------|
| **测试失败** | `VERDICT: FAIL` 或指向 `*_test_results.md` | 读取测试结果提取失败用例 |
| **审查反馈** | `review_feedback.md` 或 Critical 关键词 | 读取审查反馈提取 Critical 项 |
| **线上异常** | `request_id` / 环境名（drama-dev/drama-prod） | 标记需观测 MCP 证据 + DB 比对 |
| **手动报告** | 其他自然语言描述 | 标记需用户补充复现步骤 |

### File Contracts

**Path**: `.ai/fix/{module}/{branch}_{序号}/`（fix_id = `{module}/{branch}_{序号}`）

| 文件 | 写入方 | 读取方 | 用途 |
|------|--------|--------|------|
| `bug_report.md` | Phase 0 | debugger-agent | 结构化 Bug 报告 |
| `diagnosis.md` | debugger-agent | 用户确认 | 根因分析报告 |
| `changed_files.txt` | debugger-agent | Reviewer/Tester | 修复文件列表 |
| `review_feedback.md` | Reviewer | debugger-agent | 修复审查反馈 |
| `regression_test_results.md` | test-runner | debugger-agent | 回归测试结果 |
| `tests/{router}/` | unit-test-gen-agent | test-runner | 回归单元测试（按 router 分目录；与集成测试 `tests/{branch}/` 区分） |

## Command Format

```
/fix <Bug 描述>
/fix from=implement
/fix bug_report=<path>
```

> 流水线控制参数（`mode`、`unit_test`、`inte_test`）不再通过命令行传入，改为 Pre-flight 阶段通过 `AskUserQuestion` 主动询问用户。若用户输入中已包含参数值（如 `/fix xxx mode=fast`）则跳过对应询问。

### 输入参数

| 参数 | 必填 | 说明 |
|------|------|------|
| Bug 描述 | 三选一 | 自然语言 Bug 描述，触发 Phase 0 问题收集 |
| `from` | 三选一 | `implement` 时从 implement 失败结果衔接，自动生成 `bug_report.md` |
| `bug_report` | 三选一 | 已有 `bug_report.md` 路径，跳过 Phase 0 |

### 上下文参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `module` | 自动推断 | 模块名。未传入时从 Bug 描述或分支名推断 |

### 流水线控制参数（Pre-flight 交互收集）

| 参数 | 默认值 | 取值 | 说明 |
|------|--------|------|------|
| `mode` | `full` | `full` / `fast` | `fast` 仅跳过 `security-reviewer-agent`；`code-reviewer-agent` 始终强制执行。线上异常/安全鉴权建议使用 `full` |
| `unit_test` | `on` | `on` / `off` / `<router>` | `off` 跳过 Phase 3 Step 3a/3b；传 **router 目录名** 时仅 `pytest tests/<router>/` |
| `inte_test` | `on` | `on` / `off` / `<module>` | `off` 跳过 Phase 3c；`on` 在测试文件存在时自动触发集成回归；传模块名仅运行该模块的集成测试 |

> `branch` 自动检测：`git rev-parse --abbrev-ref HEAD | tr '/' '_'`

## Pre-flight

1. 检查参数：至少需要 Bug 描述或已有测试结果/审查反馈路径
2. `BRANCH=$(git rev-parse --abbrev-ref HEAD | tr '/' '_')`
3. `from=implement` → 从 `.ai/implement/{module}/{branch}/` 读取 task_card.json + 测试结果，直接生成 bug_report.md 进入 Phase 1
4. **交互收集流水线控制参数**：若用户未在命令中指定以下参数，通过 `AskUserQuestion` 依次询问：
   - **mode**：「请选择运行模式。(A) 完整模式 — 问题收集 → 诊断修复 → 代码审查 + 安全审查 → 回归测试 (B) 快速模式 — 保留代码审查，仅跳过安全审查」
     - 默认 `full`，用户选 B 时 `mode=fast`
   - **unit_test**：「是否执行回归单元测试？(A) 是，全部 (B) 否，跳过 (C) 仅指定 router」
     - 默认 `on`，选 B 时 `unit_test=off`，选 C 时追问 router 名
   - **inte_test**：「是否执行集成测试回归？(A) 是，测试文件存在时自动触发 (B) 否，跳过 (C) 仅指定模块」
     - 默认 `on`，选 B 时 `inte_test=off`，选 C 时追问模块名
5. 向用户确认并展示流水线路径：
   - 完整模式（默认）：「问题收集 → 诊断修复 → 修复审查 → 回归测试。关键节点暂停确认」
   - 快速模式（mode=fast）：「问题收集 → 诊断修复 → 强制代码审查 → 回归测试」
   - 根据 unit_test/inte_test 开关动态裁剪路径展示
6. **AHE 轨迹初始化**：
   ```bash
   mkdir -p .ai/harness-trace
   python3 -c "
   import json, time, uuid
   meta = {
       'trace_id': str(uuid.uuid4()),
       'command': 'fix',
       'module': '$module',
       'branch': '$BRANCH',
       'mode': '$mode',
       'unit_test': '$unit_test',
       'inte_test': '$inte_test',
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
7. **AHE Pre-flight 完成标记**：
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

> **AHE Phase 事件**：每个 Phase 开始前，Command 框架自动向 `.ai/harness-trace/.preflight_meta.json` 追加 `phase_events` 记录。Observer Skill 在 Command 执行完毕后统一消费写入轨迹。

### Phase 0: 问题收集与结构化（Intake）

**执行者**: fix-command 自身（无需 Sub-agent）

根据用户输入识别 Bug 来源（见上表），生成结构化报告：

```bash
mkdir -p .ai/fix/{fix_id}
```

```markdown
# Bug Report: {fix_id}

## 基本信息
- fix_id: {fix_id} | 来源: {类型} | 环境: local/drama-dev/drama-prod
- 关联 implement: .ai/implement/{module}/{branch}/（若有）

## 问题描述
{用户描述或从文件提取的错误信息}

## 错误证据
- 失败用例: {从 test_results.md 提取} | 审查 Critical: {从 review_feedback.md 提取}
- 错误堆栈: {若有} | request_id: {若有}

## 涉及文件（初步判断）
{从 changed_files.txt 或堆栈推断}

## 复现步骤
{用户提供或待补充}
```

写入 `.ai/fix/{fix_id}/bug_report.md`。信息不足时 AskQuestion 向用户补充，严禁猜测。

### Phase 1: 诊断与修复（Debugger）

**Agent**: `debugger-agent` (Sub-agent)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须通过 Sub-agent 委托执行。
> Planner 禁止自行读取代码、直接进行修复或替代 debugger-agent 执行诊断。
> 未收到 debugger-agent 的书面 VERDICT 响应前，禁止进入下一阶段。

**Prompt**:
> 请根据 Bug 报告进行诊断和修复。
> Bug 报告：.ai/fix/{fix_id}/bug_report.md
> 关联 task_card（若有）：.ai/implement/{module}/{branch}/task_card.json
> 执行路径：
> - 来源为「测试失败/审查反馈/手动报告」→ 路径 A（本地调试）
> - 来源为「线上异常」→ 路径 B（先 plan 模式分析，用户确认根因后修复）
> 修复完成后：changed_files.txt + diagnosis.md + 输出 VERDICT: PASS 或 FAIL。

**Done when**: `diagnosis.md` + `changed_files.txt` 已生成 + VERDICT: PASS
**On FAIL**: 暂停流水线，AskQuestion「Debugger 无法自动修复，请查看诊断报告。(A) 提供额外信息 (B) 人工修复后继续 (C) 终止」
**线上场景强制卡点**: 路径 B 中根因分析后必须等用户确认才执行修复

### Phase 2: 修复审查（Discriminator）

**Never skip**: `code-reviewer-agent` 必须执行。`mode=fast` 仅跳过 `security-reviewer-agent`（报告中标注「⚡ 快速模式 — 安全审查已跳过，代码审查已执行」）。

**🔴 动态范围判断（只允许裁剪安全审查 — 红线）**:
若 `mode=full`，进入审查前先检查改动范围：
1. 读取 `changed_files.txt`，统计改动文件数和改动行数（`git diff --stat`）
2. 若改动范围较小（如 ≤ 2 个文件且改动行数较少），必须通过 `AskUserQuestion` 主动询问用户：
   > 「本次修复改动范围较小（仅 N 个文件，约 M 行变更）。是否跳过安全审查，仅执行强制代码审查后进入回归测试？
   > (A) 跳过安全审查，保留代码审查
   > (B) 继续完整审查流程（代码审查 + 安全审查）」
3. 用户选 A → 按 `mode=fast` 处理，仅跳过 `security-reviewer-agent`，报告中标注「⚡ 用户确认跳过安全审查 — 改动范围较小；代码审查已执行」
4. 用户选 B → 正常执行 Phase 2
5. **严禁 AI 自行判断并跳过安全审查，必须等待用户明确选择；严禁跳过 `code-reviewer-agent`。这是红线。**

**Agents**: `code-reviewer-agent` (强制) + `security-reviewer-agent` (`mode=full` 时并行)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须委托 `code-reviewer-agent` 执行代码审查；不存在跳过代码审查的路径。
> `mode=full` 时必须同时委托 `code-reviewer-agent` 与 `security-reviewer-agent` 并行执行审查；`mode=fast` 时仅可跳过 `security-reviewer-agent`。
> Planner 禁止自行执行审查、直接输出 VERDICT 或替代 `code-reviewer-agent`。
> 未收到 `code-reviewer-agent` 的 VERDICT 响应前，禁止进入下一阶段；`mode=full` 时还必须等待 `security-reviewer-agent` 的 VERDICT。

**Prompt** (`code-reviewer-agent`; `mode=full` 时同上下文传给 `security-reviewer-agent`):
> 请审查以下修复代码（Bug 修复），重点关注：
> 1. 修复是否精准针对根因，未引入无关变更
> 2. 是否可能产生副作用（破坏现有功能）
> 3. 是否遵循最小化原则
> Bug 报告：.ai/fix/{fix_id}/bug_report.md
> 诊断报告：.ai/fix/{fix_id}/diagnosis.md
> 改动文件：$(cat .ai/fix/{fix_id}/changed_files.txt)
> 关联 task_card（若有）：.ai/implement/{module}/{branch}/task_card.json
> 输出 VERDICT: PASS 或 FAIL，写入 review_feedback.md。

**Verdict**: `code-reviewer-agent` PASS 且（`mode=fast` 或 `security-reviewer-agent` PASS）→ Phase 3 | 任一已执行审查 FAIL → Retry Loop
**Retry Loop** (MAX=2): 提取 Critical → `debugger-agent` 二次修复（不扩大范围）→ 重新执行强制代码审查；`mode=full` 时重新并行执行安全审查。超限 → AskQuestion「已循环 2 轮：[列出]。(A) 人工修复 (B) 忽略继续回归测试 (C) 终止」

> **AHE**: 每次 Retry Loop 触发时，记录 `{"phase": "Phase 2", "event": "retry", "retry_count": N, "reason": "Critical"}` 到轨迹 `phase_events` 中。

### Phase 3: 回归测试（Regression Test）

**Skip if**: `unit_test=off` 且 `inte_test=off`（报告中标注「⏭️ 回归测试全部跳过」）

#### Step 3a: 生成回归测试用例

**Skip if**: `unit_test=off`（报告中标注「⏭️ 回归单元测试已跳过（unit_test=off）」）
**Scope**: `unit_test={router_name}` 时仅为指定 router 目录生成/运行单元测试，报告标注「🎯 单元测试范围：router={router_name}」

**Agent**: `unit-test-gen-agent` (Sub-agent)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须通过 Sub-agent 委托执行。
> Planner 禁止自行生成回归测试用例、直接写入测试文件或跳过委托。
> 未收到 unit-test-gen-agent 的书面 VERDICT 响应前，禁止进入 Step 3b。

**Prompt**:
> 基于 Bug 修复内容生成回归测试用例。
> Bug 报告：.ai/fix/{fix_id}/bug_report.md | 诊断报告：.ai/fix/{fix_id}/diagnosis.md
> 修复文件：$(cat .ai/fix/{fix_id}/changed_files.txt)
> 关联 task_card（若有）：.ai/implement/{module}/{branch}/task_card.json
> 要求：
> 1. 「修复验证用例」— 验证原 Bug 已修复
> 2. 「回归保护用例」— 验证相邻功能未被破坏
> 3. 连接本地 MySQL 查询真实数据
> 4. 按 changed_files / task_card 推导 router，追加到 tests/{router}/{router}_unit_test.py（不整文件覆盖）+ 更新 tests/{router}/{router}_unit_data.yaml；已覆盖则 SKIPPED_GENERATION
> 5. 标记 @pytest.mark.fix + @pytest.mark.unit

#### Step 3b: 执行回归测试

**Skip if**: `unit_test=off`

**Agent**: `test-runner-agent` (Sub-agent)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须通过 Sub-agent 委托执行。
> Planner 禁止自行执行 pytest 命令或替代 test-runner-agent 输出回归测试结果。
> 未收到 test-runner-agent 的书面 VERDICT 响应前，禁止进入下一阶段。

**Prompt**:
> 执行回归测试。测试范围：1) fix 标记用例 2) 传入的 `tests/{router}/` 目录（从 changed_files 解析 router；`unit_test={router_name}` 时仅该目录）。
> 测试类型：单元测试（回归）。结果写入 regression_test_results.md，输出 VERDICT。

**Verdict**: PASS → Phase 3c/4 | FAIL → Retry Loop
**Retry Loop** (MAX=2): `debugger-agent` 修复代码（不改测试）→ 重新执行 Step 3b。超限 → AskQuestion「已循环 2 轮：[列出]。(A) 人工修复 (B) 终止」

> **AHE**: 每次 Retry Loop 触发时，记录 `{"phase": "Phase 3: 回归测试", "event": "retry", "retry_count": N}` 到轨迹 `phase_events` 中。

### Phase 3c: 已有集成测试回归（可选）

**Skip if**: `inte_test=off`（报告中标注「⏭️ 集成测试回归已跳过（inte_test=off）」）
**Trigger**: `inte_test=on` 且存在 `tests/{branch}/{module}_api_test.py`，或 `inte_test={module_name}`
**Scope**: `inte_test={module_name}` 时仅运行 `tests/{branch}/{module_name}_api_test.py`，报告标注「🎯 集成测试范围：{module_name}」

**Agent**: `test-runner-agent` (Sub-agent)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须通过 Sub-agent 委托执行。
> Planner 禁止自行执行集成测试命令或替代输出结果。
> 未收到 test-runner-agent 的书面 VERDICT 响应前，禁止进入下一阶段。

**Prompt**:
> 执行集成测试回归：tests/{branch}/{test_target_module}_api_test.py。
> 结果追加到 regression_test_results.md，输出 VERDICT。

> 其中 `test_target_module` = inte_test 参数值（若为模块名）或当前 module。

Retry Loop 同 Step 3b。

### Phase 4: 修复报告

输出报告：

```markdown
## 🔧 fix 修复流水线执行报告

### 模式
{mode=fast：⚡ 快速模式（已跳过安全审查；代码审查已执行）}
{unit_test=off：⏭️ 回归单元测试已跳过}
{inte_test=off：⏭️ 集成测试回归已跳过}
{unit_test 为 router / inte_test 为模块名：🎯 测试范围已限定}

### 概览
| 阶段 | Agent | VERDICT | 重试 |
|------|-------|---------|------|
| Phase 0: 问题收集 | fix-command | ✅ | - |
| Phase 1: 诊断修复 | debugger-agent | PASS | - |
| Phase 2: 修复审查 | code-reviewer（强制）+ security-reviewer（full 模式） | PASS/FAIL/⚡SECURITY_SKIP | 0-2 |
| Phase 3: 回归测试 | unit-test-gen-agent + test-runner | PASS/FAIL/⏭️SKIP | 0-2 |
| Phase 3c: 集成回归 | test-runner（可选） | PASS/FAIL/⏭️SKIP | 0-2 |

### Bug 信息
fix_id: {fix_id} | 来源: {类型} | 根因: {一句话}

### 修复内容
$(cat .ai/fix/{fix_id}/changed_files.txt)

### 回归测试
- 修复验证：{N} 用例，通过率 {X}%（若执行）
- 全量回归：{N} 用例，通过率 {X}%（若执行）
- 集成回归：{N} 用例，通过率 {X}%（若执行）

### AHE 轨迹信息
- **轨迹文件**：`.ai/harness-trace/{trace_id}_fix_{module}_{branch}.jsonl`
- **分析触发**：执行 `/ahe-analyze limit=30` 进行根因分析
- **演化触发**：分析后执行 `/ahe-evo apply <candidate_id>` 应用改进候选
```

🔴 **HARD STOP — 人类确认卡点**
**必须执行 AskQuestion**：「修复流水线完毕。(A) 确认 commit (B) 需要调整 (C) 终止」
禁止推断用户意图自动继续。未收到用户明确回复前，流水线在此终止等待。

选 (A) 输出 commit message：
```
fix: {根因一句话}
- 修复文件：{affected_files}
- 根因：{root_cause}
- 回归测试：{N} 例通过
```

## Key Principles

- **最小化修复**: 只改根因代码，不重构、不改风格、不扩大范围
- **修复必审查**: 每次修复都必须经 `code-reviewer-agent` 独立审查；`mode=full` 时额外执行 Security Reviewer
- **回归必覆盖**: 验证原 Bug 已修复 + 相邻功能未被破坏
- **2 轮上限**: 修复 GAN 循环比 implement 更严格（2 轮 vs 3 轮），超限升级人类
- **线上场景强制卡点**: 涉及线上环境的修复，根因分析必须经人类确认后才执行
- **证据驱动**: 禁止“试错式”修改，所有修复基于观测 MCP 查询结果、日志/堆栈/数据比对等证据
- **Context Reset**: Agent 间通过文件契约通信，不继承对话历史
- **歧义必须停下**: 遇到缺失/歧义暂停确认，禁止猜测

### 禁止行为（无论任务复杂度如何，一律适用）
- 🔴 **红线**：禁止任何路径跳过 `code-reviewer-agent`；即便改动仅 1 行也必须委托该 Agent 并等待 VERDICT
- 🔴 **红线**：禁止 AI 自行判断「改动范围小」而跳过安全审查——即便仅跳过 `security-reviewer-agent` 也必须通过 `AskUserQuestion` 由用户决定。AI 不可替用户做主
- 禁止以「任务简单」「改动很小」为由跳过标注 (Sub-agent) 的步骤
- 禁止 Planner 自行执行诊断修复、审查或测试（即便能力上可行）
- 禁止自动通过 HARD STOP 卡点，必须等待用户明确响应
- 禁止在未收到上一阶段 VERDICT 的情况下进入下一阶段
- 禁止省略 Pre-flight 的流水线配置确认步骤

## Historical Context

在 Pre-flight 阶段，读取项目根目录 `AGENTS.md` 中的「流水线执行归档」章节，利用历史执行记录辅助 Bug 诊断：

1. **同模块历史**: 查找当前 `module` 的历史 implement/modify 记录，读取 `task_card.json`/`change_card.json` 了解原始设计意图，辅助根因分析
2. **历史修复**: 查找同模块的历史 fix 记录，读取 `diagnosis.md` 了解已修复的问题，避免重复诊断或引入已知的回归
3. **审查反馈**: 参考历史 `review_feedback.md` 中与当前 Bug 相关的审查意见，可能直接指向根因
4. **测试基线**: 复用已有单元测试（`tests/{router}/`）；集成回归仍使用 `tests/{branch}/` 下 `*_api_test.py`

> 若 `AGENTS.md` 不存在或无归档记录，跳过此步骤正常执行。

## Project Context

> 项目上下文已集中管理，不再使用占位符。
> 所有 Sub-agent 启动时自动读取 `.ether/project-context.md` 获取项目路径、目录结构、开发服务器等信息。
> 中间件连接配置（MySQL、Redis、Kafka 等）从 `.ether/config/infrastructure.json` 读取。
