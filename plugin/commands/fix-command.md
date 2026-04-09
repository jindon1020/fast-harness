# fix-command

## Task
Bug 修复闭环流水线：从 Bug 报告出发，经过诊断定位、最小化修复、GAN 对抗审查、回归测试，最终产出通过全部测试的修复代码。

## Context

与 `implement` 流水线互补：
- **implement** = 正向构建流水线（从零到一）：需求 → 设计 → 生成 → 审查 → 测试
- **fix** = 修复闭环流水线（从一到一）：Bug → 诊断 → 修复 → 审查 → 回归测试

基于相同的 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 三体架构：
- **Debugger**（诊断修复）→ **Reviewer**（修复审查）→ **Tester**（回归验证）
- 修复代码同样需要 GAN 对抗审查，防止"修了一个 Bug 引入两个新 Bug"
- **Context Reset**：Agent 间通过文件契约传递状态，不依赖对话历史

### Bug 来源分类

| 来源 | 输入形式 | 典型场景 |
|------|----------|----------|
| **测试失败** | test-runner-agent 的 `VERDICT: FAIL` + 失败用例列表 | implement 流水线 Phase 3/4 失败后独立修复 |
| **审查反馈** | code-reviewer / security-reviewer 的 `review_feedback.md` | implement 流水线 Phase 2 Critical 问题需要独立修复 |
| **线上异常** | request_id / 错误描述 / 环境名 | 用户反馈线上 500、数据异常、功能异常 |
| **手动报告** | 用户自然语言描述 Bug | 开发/测试人员发现的 Bug |

### 文件契约（Agent 间通信协议）

文件保存路径：`.ai/fix/{fix_id}/`

`fix_id` 命名规则：`{sprint}_{module}_{序号}`，如 `sprint_2026_04_asset_transfer_001`

| 契约文件 | 写入方 | 读取方 | 用途 |
|----------|--------|--------|------|
| `.ai/fix/{fix_id}/bug_report.md` | fix-command (Phase 0) | debugger-agent | 结构化 Bug 报告 |
| `.ai/fix/{fix_id}/diagnosis.md` | debugger-agent | 用户确认 | 根因分析报告 |
| `.ai/fix/{fix_id}/changed_files.txt` | debugger-agent | Reviewer / Tester | 修复涉及的文件列表 |
| `.ai/fix/{fix_id}/review_feedback.md` | Reviewer | debugger-agent | 修复代码的审查反馈 |
| `.ai/fix/{fix_id}/regression_test_results.md` | test-runner-agent | debugger-agent | 回归测试结果 |
| `tests/{sprint}/` | api-test-agent | test-runner-agent | 回归测试用例（可复用） |

---

## Execution Steps

**启动前必须动作**：
1. 检查参数完整性：至少需要 Bug 描述或已有的测试结果/审查反馈文件路径
2. 若用户传入 `from=implement`，从 `.ai/implement/{sprint}_{module}/` 读取关联的 task_card.json 和测试结果文件作为上下文
3. 若 `fast=true`，向用户说明：「启动 fix 修复流水线（**快速模式**），将跳过修复审查，依次经过：问题收集 → 诊断修复 → 回归测试。」
4. 若 `fast` 未设置或为 `false`，向用户说明：「启动 fix 修复流水线，将依次经过：问题收集 → 诊断修复 → 修复审查 → 回归测试。关键节点会暂停等待您确认。」

---

### Phase 0: 问题收集与结构化（Intake）

**执行者**: fix-command 自身（无需 Sub-agent）

**目标**: 将多种来源的 Bug 信息标准化为统一的 `bug_report.md`

#### Step 0a: 识别 Bug 来源

根据用户输入判断 Bug 类型：

| 输入特征 | 判定为 | 自动关联 |
|----------|--------|----------|
| 包含 `VERDICT: FAIL` 或指向 `*_test_results.md` | 测试失败 | 读取测试结果文件提取失败用例 |
| 包含 `review_feedback.md` 或 Critical 关键词 | 审查反馈 | 读取审查反馈提取 Critical 项 |
| 包含 `request_id` / 环境名（drama-dev/drama-prod） | 线上异常 | 标记需要 Loki 日志 + DB 比对 |
| 其他自然语言描述 | 手动报告 | 标记需要用户补充复现步骤 |

#### Step 0b: 生成结构化 Bug 报告

```bash
mkdir -p .ai/fix/{fix_id}
```

```markdown
# Bug Report: {fix_id}

## 基本信息
- **fix_id**: {fix_id}
- **来源**: 测试失败 / 审查反馈 / 线上异常 / 手动报告
- **环境**: local / drama-dev / drama-prod
- **关联 implement**: .ai/implement/{sprint}_{module}/（若有）

## 问题描述
{用户描述或从文件中提取的错误信息}

## 错误证据
- **失败用例**: {从 test_results.md 提取，若有}
- **审查 Critical**: {从 review_feedback.md 提取，若有}
- **错误堆栈**: {若有}
- **request_id**: {若有}

## 涉及文件（初步判断）
- {从 changed_files.txt 或错误堆栈推断}

## 复现步骤
{用户提供或待补充}
```

将 Bug 报告写入 `.ai/fix/{fix_id}/bug_report.md`。

**信息不足时的处理**：若缺少复现步骤或关键错误信息，调用 `AskQuestion` 向用户补充。严禁猜测。

---

### Phase 1: 诊断与修复（Debugger）

**Agent**: `debugger-agent`（Sub-agent 方式启动）

**传入上下文**:
```
prompt: "请根据 Bug 报告进行诊断和修复。
Bug 报告：.ai/fix/{fix_id}/bug_report.md
关联 task_card（若有）：.ai/implement/{sprint}_{module}/task_card.json

执行路径判断：
- 来源为「测试失败」或「审查反馈」或「手动报告」→ 路径 A（本地开发调试）
- 来源为「线上异常」→ 路径 B（线上问题排查，需先 plan 模式分析，用户确认后修复）

修复完成后：
1. 将修复涉及的文件列表写入 .ai/fix/{fix_id}/changed_files.txt
2. 将诊断分析写入 .ai/fix/{fix_id}/diagnosis.md
3. 输出 VERDICT: PASS（修复完成）或 VERDICT: FAIL（无法修复，需人工介入）"
```

**完成标准**:
- `.ai/fix/{fix_id}/diagnosis.md` 已生成，包含根因分析
- `.ai/fix/{fix_id}/changed_files.txt` 已生成，包含修复的文件列表
- debugger-agent 输出 `VERDICT: PASS`

**失败处理**:
- debugger-agent 输出 `VERDICT: FAIL` → 暂停流水线，展示诊断报告给用户，调用 `AskQuestion`：「Debugger 无法自动修复此问题，请查看诊断报告。选择：(A) 提供额外信息继续 (B) 人工修复后继续流水线 (C) 终止」

**强制卡点（线上异常场景）**: 路径 B 中 debugger-agent 输出根因分析后，必须等待用户确认根因正确后才执行修复。

---

### Phase 2: 修复审查（Discriminator — 修复验证）

**跳过条件**: `fast=true` 时跳过整个 Phase 2，直接进入 Phase 3。跳过时在修复报告中标注「⚡ 快速模式 — 修复审查已跳过」。

**设计思想**: 修复代码的质量同样需要独立评判。修复过程中的"顺手"改动、范围扩大、风格变更等都可能引入新问题。

**Agent**: `code-reviewer-agent` + `security-reviewer-agent`（**并行**启动两个 Sub-agent）

**传入上下文（两者相同）**:
```
prompt: "请审查以下修复代码。这是一次 Bug 修复，请重点关注：
1. 修复是否精准针对根因，未引入无关变更
2. 修复是否可能产生副作用（破坏现有功能）
3. 修复是否遵循最小化原则

Bug 报告：.ai/fix/{fix_id}/bug_report.md
诊断报告：.ai/fix/{fix_id}/diagnosis.md
改动文件列表：$(cat .ai/fix/{fix_id}/changed_files.txt)
关联 task_card（若有）：.ai/implement/{sprint}_{module}/task_card.json

请严格按审查维度输出 VERDICT: PASS 或 FAIL。
将审查结果写入 .ai/fix/{fix_id}/review_feedback.md。"
```

**VERDICT 汇总逻辑**:
- 两个 Reviewer 都返回 `VERDICT: PASS` → Phase 2 通过，进入 Phase 3
- 任一返回 `VERDICT: FAIL` → 进入修复循环

**修复循环（GAN Fix Loop）**:

```
retry_count = 0
MAX_RETRY = 2

while any VERDICT == FAIL and retry_count < MAX_RETRY:
    1. 将 .ai/fix/{fix_id}/review_feedback.md 中的 Critical 列表提取
    2. 启动 debugger-agent（Sub-agent）：
       prompt: "审查发现修复代码存在 Critical 问题，请二次修复。
       审查反馈：.ai/fix/{fix_id}/review_feedback.md
       改动文件：$(cat .ai/fix/{fix_id}/changed_files.txt)
       只修复 Critical 问题，不扩大改动范围。修复后更新 changed_files.txt。"
    3. 修复完成后，重新启动 Phase 2 的两个 Reviewer（并行）
    4. retry_count += 1

if retry_count >= MAX_RETRY and still FAIL:
    暂停流水线，调用 AskQuestion:
    「修复审查已循环 2 轮仍有 Critical 问题未解决。
    未解决的 Critical 问题：[列出]
    请选择：(A) 人工修复后继续 (B) 忽略继续执行回归测试 (C) 终止流水线」
```

> 注意：fix 流水线的 GAN 循环最多 **2 轮**（比 implement 的 3 轮少），因为修复应该是小范围改动，超过 2 轮说明修复方向可能有误。

---

### Phase 3: 回归测试（Regression Test）

**设计思想**: 修复 Bug 后必须确保：① 原 Bug 已修复；② 未引入新的回归。

#### Step 3a: 生成/更新回归测试用例

**Agent**: `api-test-agent`（Sub-agent 方式启动）

**传入上下文**:
```
prompt: "请基于 Bug 修复内容生成回归测试用例。

Bug 报告：.ai/fix/{fix_id}/bug_report.md
诊断报告：.ai/fix/{fix_id}/diagnosis.md
修复文件：$(cat .ai/fix/{fix_id}/changed_files.txt)
关联 task_card（若有）：.ai/implement/{sprint}_{module}/task_card.json

要求：
1. 必须包含「修复验证用例」— 精准验证原 Bug 已修复
2. 必须包含「回归保护用例」— 验证修复未破坏相邻功能
3. 连接本地 MySQL 查询真实数据构建测试参数
4. 将测试用例追加到 tests/{sprint}/{module}_unit_test.py（若文件已存在则追加，不覆盖原有用例）
5. 更新 tests/{sprint}/{module}_unit_data.yaml"
```

**完成标准**:
- 回归测试用例已生成或追加到 `tests/{sprint}/{module}_unit_test.py`
- 用例中明确标注 `@pytest.mark.fix` + `@pytest.mark.unit`

#### Step 3b: 执行回归测试

**Agent**: `test-runner-agent`（Sub-agent 方式启动）

**传入上下文**:
```
prompt: "请执行回归测试。

测试范围：
1. 修复验证：运行新增的 fix 标记用例
2. 全量回归：运行 tests/{sprint}/{module}_unit_test.py 全部用例

测试文件：tests/{sprint}/{module}_unit_test.py
测试类型：单元测试（回归测试）
将测试结果写入 .ai/fix/{fix_id}/regression_test_results.md
输出 VERDICT: PASS 或 FAIL。"
```

**VERDICT 处理**:
- `VERDICT: PASS` → 进入 Phase 4
- `VERDICT: FAIL` → 进入修复循环

**修复循环**:
```
retry_count = 0
MAX_RETRY = 2

while VERDICT == FAIL and retry_count < MAX_RETRY:
    1. 启动 debugger-agent（Sub-agent）：
       prompt: "回归测试失败，请根据以下信息修复：
       测试结果：.ai/fix/{fix_id}/regression_test_results.md
       改动文件：$(cat .ai/fix/{fix_id}/changed_files.txt)
       只修复导致测试失败的代码，不修改测试用例本身。"
    2. 修复完成后，重新执行 Step 3b（test-runner-agent）
    3. retry_count += 1

if retry_count >= MAX_RETRY and still FAIL:
    暂停流水线，调用 AskQuestion:
    「回归测试已循环修复 2 轮仍有失败用例。
    失败用例：[列出]
    请选择：(A) 人工修复后继续 (B) 终止流水线」
```

---

### Phase 3c: 已有集成测试回归（可选）

**触发条件**: 存在 `tests/{sprint}/{module}_api_test.py` 集成测试文件

若存在已有的集成测试文件，额外执行一轮集成测试回归：

**Agent**: `test-runner-agent`（Sub-agent 方式启动）

```
prompt: "请执行集成测试回归。
测试文件：tests/{sprint}/{module}_api_test.py
测试类型：集成测试（回归）
将结果追加到 .ai/fix/{fix_id}/regression_test_results.md
输出 VERDICT: PASS 或 FAIL。"
```

VERDICT 处理同 Step 3b。

---

### Phase 4: 修复报告 + 人类确认

汇总所有阶段的执行结果，输出修复报告：

```markdown
## fix 修复流水线执行报告

### 模式
{若 fast=true 则显示：⚡ 快速模式（已跳过修复审查），否则不显示此行}

### 概览
| 阶段 | Agent | VERDICT | 重试次数 |
|------|-------|---------|----------|
| Phase 0: 问题收集 | fix-command | ✅ 完成 | - |
| Phase 1: 诊断修复 | debugger-agent | PASS | - |
| Phase 2: 修复审查 | code-reviewer + security-reviewer | PASS/FAIL/⚡SKIP | 0-2 |
| Phase 3: 回归测试 | api-test-agent + test-runner | PASS/FAIL | 0-2 |
| Phase 3c: 集成回归 | test-runner（可选） | PASS/FAIL/SKIP | 0-2 |

### Bug 信息
- **fix_id**: {fix_id}
- **来源**: {来源类型}
- **根因**: {一句话根因}

### 修复内容
$(cat .ai/fix/{fix_id}/changed_files.txt)

### 修复 Diff 摘要
{每个文件的关键修改点}

### 回归测试
- 修复验证用例：{N} 个，通过率 {X}%
- 全量回归用例：{N} 个，通过率 {X}%
- 集成回归用例：{N} 个，通过率 {X}%（若执行）

### 诊断报告
{诊断报告核心内容}
```

**强制卡点**: 调用 `AskQuestion` —— 「修复流水线执行完毕，是否确认提交？(A) 确认，准备 commit (B) 需要调整 (C) 终止」

若用户选择 (A)，输出建议的 git commit message（中文）：
```
fix: {根因一句话描述}

- 修复文件：{affected_files}
- 根因：{root_cause}
- 回归测试：{N} 例通过
```

---

## 修复闭环流程总览

```
┌──────────────────────────────────────────────────────────┐
│                   fix 修复闭环流水线                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Phase 0              Phase 1             Phase 2        │
│  ┌─────────────┐      ┌─────────────┐    ┌───────────┐ │
│  │ 问题收集     │      │ debugger-   │    │ code-     │ │
│  │ bug_report  │─────▶│ agent       │───▶│ reviewer  │ │
│  │ .md         │      │ (诊断+修复)  │    │ security- │ │
│  └─────────────┘      └──────▲──────┘    │ reviewer  │ │
│                              │           │ (并行审查)  │ │
│  输入来源：                    │           └─────┬─────┘ │
│  • 测试 FAIL                  │                 │        │
│  • 审查 Critical              │            VERDICT       │
│  • 线上 request_id            │                 │        │
│  • 手动报告                    │     ┌──────────┤        │
│                              │     │          │        │
│                         FAIL │  PASS          │        │
│                    (retry≤2) │     │          │        │
│                              │     ▼          │        │
│                              │  Phase 3       │        │
│                              │  ┌───────────┐ │        │
│                              │  │api-test   │ │        │
│                              │  │test-runner│ │        │
│                              │  │(回归测试)  │ │        │
│                              │  └─────┬─────┘ │        │
│                              │        │       │        │
│                              │   VERDICT      │        │
│                              │        │       │        │
│                              │   ┌────┤       │        │
│                              │   │    │       │        │
│                         FAIL │ PASS   │       │        │
│                    (retry≤2) │   │    │       │        │
│                              │   ▼    │       │        │
│                              │ Phase 4│       │        │
│                              │ 修复报告│       │        │
│                              │ ✋人类确认      │        │
│                              │        │       │        │
└──────────────────────────────┴────────┴───────┘        │
                                                          │
└──────────────────────────────────────────────────────────┘
```

## 与 implement 流水线的关系

| 维度 | implement | fix |
|------|-----------|-----|
| **目标** | 从零构建新功能 | 修复已有代码的 Bug |
| **入口** | 需求描述 / task_card.json | Bug 报告 / 测试失败 / 审查反馈 / 线上异常 |
| **Phase 数** | 6 个（Phase 0-5） | 5 个（Phase 0-4） |
| **核心 Agent** | requirement-design → generator → reviewer → tester | debugger → reviewer → tester |
| **GAN 循环上限** | 3 轮 | 2 轮（修复应小范围，超限说明方向有误） |
| **文件契约目录** | `.ai/implement/{sprint}_{module}/` | `.ai/fix/{fix_id}/` |
| **互操作** | Phase 3/4 FAIL 可触发 fix 流水线 | 可读取 implement 的 task_card.json 获取上下文 |

### 从 implement 衔接到 fix

当 implement 流水线的 Phase 3/4 测试失败且超过 3 轮自动修复后，用户可选择启动独立的 fix 流水线：

```bash
/fix from=implement sprint=sprint_2026_04 module=asset_transfer
```

此时 fix 流水线自动：
1. 从 `.ai/implement/{sprint}_{module}/unit_test_results.md` 或 `integration_test_results.md` 提取失败信息
2. 从 `.ai/implement/{sprint}_{module}/task_card.json` 读取完整上下文
3. 跳过 Phase 0 中的信息收集，直接生成 bug_report.md 并进入 Phase 1

---

## Key Principles

- **最小化修复**: 只改根因代码，不重构、不改风格、不扩大范围。Debugger Agent 核心原则。
- **修复必审查**: 每一次修复都必须经过 Code Reviewer + Security Reviewer 的独立审查，杜绝"修了一个 Bug 引入两个新 Bug"。
- **回归必覆盖**: 修复后必须验证原 Bug 已修复 + 相邻功能未被破坏。
- **Context Reset**: 同 implement，Agent 间通过文件契约通信，不继承对话历史。
- **2 轮上限**: 修复的 GAN 循环比 implement 更严格（2 轮 vs 3 轮），超限即升级人类。
- **线上场景强制卡点**: 涉及线上环境的修复，诊断报告必须经人类确认后才执行代码变更。
- **证据驱动**: 禁止"试错式"修改，所有修复必须基于日志、堆栈、数据比对等证据。

## Command Format

```
/fix <Bug 描述>
```

或带参数：
```
/fix <Bug 描述> [sprint=sprint_name] [module=module_name] [fast=true]
```

或从 implement 流水线衔接：
```
/fix from=implement [sprint=sprint_name] [module=module_name] [fast=true]
```

或指定已有 Bug 报告：
```
/fix bug_report=.ai/fix/{fix_id}/bug_report.md [fast=true]
```

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| Bug 描述 | 是（与 bug_report/from 二选一） | 自然语言 Bug 描述，触发完整修复流水线 |
| `from` | 否 | 设为 `implement` 时从 implement 流水线的失败结果衔接 |
| `bug_report` | 否 | 已有 bug_report.md 路径，跳过 Phase 0 |
| `sprint` | 否 | Sprint 名称，默认按日期生成如 `sprint_2026_04` |
| `module` | 否 | 模块名，用于定位关联文件 |
| `fast` | 否 | 设为 `true` 时跳过 Phase 2 修复审查，节省约 30%-40% Token 消耗。适用于明确根因的简单修复。**不建议在线上异常修复或涉及安全/鉴权的修复中使用** |

## 项目上下文

> **安装后请根据实际项目填写此部分**，参考 `fast-harness/project-context.example.md`

**项目路径**: `{{PROJECT_ROOT}}`

**目录结构**:
```
{{PROJECT_STRUCTURE}}
```

**本地数据库**: Host: {{DB_HOST}} | Port: {{DB_PORT}} | User: {{DB_USER}} | Pass: {{DB_PASS}} | DB: {{DB_NAME}}
**本地服务**: `{{DEV_SERVER_CMD}}`
**健康检查**: `{{HEALTH_CHECK_URL}}`
