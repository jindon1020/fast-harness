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
| **线上异常** | `request_id` / 环境名（drama-dev/drama-prod） | 标记需 Loki 日志 + DB 比对 |
| **手动报告** | 其他自然语言描述 | 标记需用户补充复现步骤 |

### File Contracts

**Path**: `.ai/fix/{fix_id}/`（fix_id = `{branch}_{module}_{序号}`）

| 文件 | 写入方 | 读取方 | 用途 |
|------|--------|--------|------|
| `bug_report.md` | Phase 0 | debugger-agent | 结构化 Bug 报告 |
| `diagnosis.md` | debugger-agent | 用户确认 | 根因分析报告 |
| `changed_files.txt` | debugger-agent | Reviewer/Tester | 修复文件列表 |
| `review_feedback.md` | Reviewer | debugger-agent | 修复审查反馈 |
| `regression_test_results.md` | test-runner | debugger-agent | 回归测试结果 |
| `tests/{branch}/` | unit-test-gen-agent | test-runner | 回归测试用例 |

## Command Format

```
/fix <Bug 描述> [module=xxx] [fast=true]
/fix from=implement [module=xxx] [fast=true]
/fix bug_report=.ai/fix/{fix_id}/bug_report.md [fast=true]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| Bug 描述 | 是（与 bug_report/from 二选一） | 自然语言 Bug 描述 |
| `from` | 否 | `implement` 时从 implement 失败结果衔接 |
| `bug_report` | 否 | 已有 bug_report.md 路径，跳过 Phase 0 |
| `module` | 否 | 模块名 |
| `fast` | 否 | `true` 跳过 Phase 2 修复审查（省 30-40% Token）。不建议在线上异常/安全鉴权使用 |

> branch 自动检测：`git rev-parse --abbrev-ref HEAD | tr '/' '_'`

## Pre-flight

1. 检查参数：至少需要 Bug 描述或已有测试结果/审查反馈路径
2. `BRANCH=$(git rev-parse --abbrev-ref HEAD | tr '/' '_')`
3. `from=implement` → 从 `.ai/implement/{branch}_{module}/` 读取 task_card.json + 测试结果，直接生成 bug_report.md 进入 Phase 1
4. `fast=true` → 告知「快速模式，跳过修复审查：问题收集 → 诊断修复 → 回归测试」
5. 默认 → 告知「完整模式：问题收集 → 诊断修复 → 修复审查 → 回归测试。关键节点暂停确认」

## Execution Steps

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
- 关联 implement: .ai/implement/{branch}_{module}/（若有）

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

**Prompt**:
> 请根据 Bug 报告进行诊断和修复。
> Bug 报告：.ai/fix/{fix_id}/bug_report.md
> 关联 task_card（若有）：.ai/implement/{branch}_{module}/task_card.json
> 执行路径：
> - 来源为「测试失败/审查反馈/手动报告」→ 路径 A（本地调试）
> - 来源为「线上异常」→ 路径 B（先 plan 模式分析，用户确认根因后修复）
> 修复完成后：changed_files.txt + diagnosis.md + 输出 VERDICT: PASS 或 FAIL。

**Done when**: `diagnosis.md` + `changed_files.txt` 已生成 + VERDICT: PASS
**On FAIL**: 暂停流水线，AskQuestion「Debugger 无法自动修复，请查看诊断报告。(A) 提供额外信息 (B) 人工修复后继续 (C) 终止」
**线上场景强制卡点**: 路径 B 中根因分析后必须等用户确认才执行修复

### Phase 2: 修复审查（Discriminator）

**Skip if**: `fast=true`（报告中标注「⚡ 快速模式 — 修复审查已跳过」）

**Agents**: `code-reviewer-agent` + `security-reviewer-agent` (并行 Sub-agent)

**Prompt** (both):
> 请审查以下修复代码（Bug 修复），重点关注：
> 1. 修复是否精准针对根因，未引入无关变更
> 2. 是否可能产生副作用（破坏现有功能）
> 3. 是否遵循最小化原则
> Bug 报告：.ai/fix/{fix_id}/bug_report.md
> 诊断报告：.ai/fix/{fix_id}/diagnosis.md
> 改动文件：$(cat .ai/fix/{fix_id}/changed_files.txt)
> 关联 task_card（若有）：.ai/implement/{branch}_{module}/task_card.json
> 输出 VERDICT: PASS 或 FAIL，写入 review_feedback.md。

**Verdict**: 两者都 PASS → Phase 3 | 任一 FAIL → Retry Loop
**Retry Loop** (MAX=2): 提取 Critical → `debugger-agent` 二次修复（不扩大范围）→ 重新审查。超限 → AskQuestion「已循环 2 轮：[列出]。(A) 人工修复 (B) 忽略继续回归测试 (C) 终止」

### Phase 3: 回归测试（Regression Test）

#### Step 3a: 生成回归测试用例

**Agent**: `unit-test-gen-agent` (Sub-agent)

**Prompt**:
> 基于 Bug 修复内容生成回归测试用例。
> Bug 报告：.ai/fix/{fix_id}/bug_report.md | 诊断报告：.ai/fix/{fix_id}/diagnosis.md
> 修复文件：$(cat .ai/fix/{fix_id}/changed_files.txt)
> 关联 task_card（若有）：.ai/implement/{branch}_{module}/task_card.json
> 要求：
> 1. 「修复验证用例」— 验证原 Bug 已修复
> 2. 「回归保护用例」— 验证相邻功能未被破坏
> 3. 连接本地 MySQL 查询真实数据
> 4. 追加到 tests/{branch}/{module}_unit_test.py（不覆盖）+ 更新 unit_data.yaml
> 5. 标记 @pytest.mark.fix + @pytest.mark.unit

#### Step 3b: 执行回归测试

**Agent**: `test-runner-agent` (Sub-agent)

**Prompt**:
> 执行回归测试。测试范围：1) fix 标记用例 2) tests/{branch}/{module}_unit_test.py 全部用例。
> 测试类型：单元测试（回归）。结果写入 regression_test_results.md，输出 VERDICT。

**Verdict**: PASS → Phase 3c/4 | FAIL → Retry Loop
**Retry Loop** (MAX=2): `debugger-agent` 修复代码（不改测试）→ 重新执行 Step 3b。超限 → AskQuestion「已循环 2 轮：[列出]。(A) 人工修复 (B) 终止」

### Phase 3c: 已有集成测试回归（可选）

**Trigger**: 存在 `tests/{branch}/{module}_api_test.py`

**Agent**: `test-runner-agent` (Sub-agent)

**Prompt**:
> 执行集成测试回归：tests/{branch}/{module}_api_test.py。
> 结果追加到 regression_test_results.md，输出 VERDICT。

Retry Loop 同 Step 3b。

### Phase 4: 修复报告

输出报告：

```markdown
## 🔧 fix 修复流水线执行报告

### 模式
{若 fast=true：⚡ 快速模式（已跳过修复审查）}

### 概览
| 阶段 | Agent | VERDICT | 重试 |
|------|-------|---------|------|
| Phase 0: 问题收集 | fix-command | ✅ | - |
| Phase 1: 诊断修复 | debugger-agent | PASS | - |
| Phase 2: 修复审查 | code-reviewer + security-reviewer | PASS/FAIL/⚡SKIP | 0-2 |
| Phase 3: 回归测试 | unit-test-gen-agent + test-runner | PASS/FAIL | 0-2 |
| Phase 3c: 集成回归 | test-runner（可选） | PASS/FAIL/SKIP | 0-2 |

### Bug 信息
fix_id: {fix_id} | 来源: {类型} | 根因: {一句话}

### 修复内容
$(cat .ai/fix/{fix_id}/changed_files.txt)

### 回归测试
- 修复验证：{N} 用例，通过率 {X}%
- 全量回归：{N} 用例，通过率 {X}%
- 集成回归：{N} 用例，通过率 {X}%（若执行）
```

**Checkpoint**: AskQuestion —「修复流水线完毕。(A) 确认 commit (B) 需要调整 (C) 终止」

选 (A) 输出 commit message：
```
fix: {根因一句话}
- 修复文件：{affected_files}
- 根因：{root_cause}
- 回归测试：{N} 例通过
```

## Key Principles

- **最小化修复**: 只改根因代码，不重构、不改风格、不扩大范围
- **修复必审查**: 每次修复都经 Code Reviewer + Security Reviewer 独立审查
- **回归必覆盖**: 验证原 Bug 已修复 + 相邻功能未被破坏
- **2 轮上限**: 修复 GAN 循环比 implement 更严格（2 轮 vs 3 轮），超限升级人类
- **线上场景强制卡点**: 涉及线上环境的修复，根因分析必须经人类确认后才执行
- **证据驱动**: 禁止"试错式"修改，所有修复基于日志/堆栈/数据比对等证据
- **Context Reset**: Agent 间通过文件契约通信，不继承对话历史
- **歧义必须停下**: 遇到缺失/歧义暂停确认，禁止猜测

## Project Context

> 安装后根据实际项目填写，参考 `fast-harness/project-context.example.md`

**项目路径**: `{{PROJECT_ROOT}}`
**目录结构**: `{{PROJECT_STRUCTURE}}`
**本地数据库**: Host: {{DB_HOST}} | Port: {{DB_PORT}} | User: {{DB_USER}} | Pass: {{DB_PASS}} | DB: {{DB_NAME}}
**本地服务**: `{{DEV_SERVER_CMD}}`
**健康检查**: `{{HEALTH_CHECK_URL}}`
