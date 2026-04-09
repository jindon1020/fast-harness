# implement-command

## Task
端到端需求实现流水线：从原始需求出发，经过需求设计、代码生成、GAN 对抗审查、自发性单元测试、外部集成测试，最终产出通过全部测试的可提交代码。

## Context

基于 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 三体架构设计：
- **Planner**（需求设计）→ **Generator**（代码生成）→ **Evaluator**（多维鉴别）
- 借鉴 GAN 对抗思想：Generator 与 Evaluator 分离，Evaluator 独立于 Generator 评判质量，消除自我评价偏差
- **Context Reset**：Agent 间通过文件契约（`task_card.json`、`changed_files.txt`、`review_feedback.md`）传递状态，不依赖对话历史，避免上下文膨胀。文件统一保存在 `.ai/implement/{sprint}_{module}/` 目录下。

### 文件契约（Agent 间通信协议）

文件保存路径：`.ai/implement/{sprint}_{module}/`

| 契约文件 | 写入方 | 读取方 | 用途 |
|----------|--------|--------|------|
| `.ai/implement/{sprint}_{module}/task_card.json` | Planner | 全体 Agent | 需求、API、数据库变更等完整上下文 |
| `.ai/implement/{sprint}_{module}/changed_files.txt` | Generator | Reviewer / Tester | 本次改动的文件列表 |
| `.ai/implement/{sprint}_{module}/review_feedback.md` | Reviewer | Debugger / Generator | 审查反馈（Critical/Improvements） |
| `.ai/implement/{sprint}_{module}/unit_test_results.md` | Test Runner | Debugger | 单元测试执行结果 |
| `.ai/implement/{sprint}_{module}/integration_test_results.md` | Test Runner | Debugger | 集成测试执行结果 |
| `tests/{sprint}/` | api-test-agent / tester-gen-agent | Test Runner | 持久化测试用例（可复用） |

### 测试分类

| 类型 | 别名 | 生成方式 | Agent | 产出 |
|------|------|----------|-------|------|
| 自发性测试 | 单元测试 | 根据接口变动自动查询本地 DB 真实数据生成 | `api-test-agent` | `tests/{sprint}/{module}_unit_test.py` |
| 外部测试 | 集成测试 | 解析测试人员提供的 xmind 脑图生成 | `tester-gen-agent` | `tests/{sprint}/{module}_api_test.py` |

## Execution Steps

**启动前必须动作**：
1. 检查参数完整性：至少需要需求描述或 `task_card` 路径
2. 若用户直接传入 `task_card=.ai/implement/{sprint}_{module}/task_card.json`，跳过 Phase 0，从 Phase 1 开始
3. 若 `fast=true`，向用户说明：「启动 implement 流水线（**快速模式**），将跳过 GAN 对抗审查，依次经过：需求设计 → 代码生成 → 单元测试 → 集成测试。」
4. 若 `fast` 未设置或为 `false`，向用户说明：「启动 implement 流水线，将依次经过：需求设计 → 代码生成 → GAN 对抗审查 → 单元测试 → 集成测试。关键节点会暂停等待您确认。」

---

### Phase 0: 需求设计（Planner）

**Agent**: `requirement-design-agent`（Sub-agent 方式启动）

**跳过条件**: 用户已传入 `task_card=.ai/implement/{sprint}_{module}/task_card.json` 且文件存在

**执行内容**:
调用 `requirement-design-agent`，传入用户需求描述和可选参数（sprint、module、xmind）。

该 Agent 内部包含完整的多步骤人类确认流程（需求理解 → 技术方案 → 数据库设计 → API 设计 → 业务逻辑 → 侵入性检查），每步都有 `AskQuestion` 卡点。

**完成标准**:
- `.ai/implement/{sprint}_{module}/task_card.json` 已写入且 `status` 为 `inbox`
- `.ai/design/{sprint}_{feature}.md` 详细设计文档已生成

**强制卡点**: 调用 `AskQuestion` 确认 —— 「需求设计阶段已完成，task_card.json 已生成。是否进入代码生成阶段？」

---

### Phase 1: 代码生成（Generator）

**Agent**: `generator-agent`（Sub-agent 方式启动）

**传入上下文**:
```
prompt: "请根据 .ai/implement/{sprint}_{module}/task_card.json 实现代码。完成后将改动文件列表写入 .ai/implement/{sprint}_{module}/changed_files.txt，并更新 task_card.json 的 status 为 in_progress。"
```

**完成标准**:
- `.ai/implement/{sprint}_{module}/changed_files.txt` 已生成，包含所有改动文件路径
- `task_card.json` 的 `status` 已更新为 `in_progress`
- 改动文件不超出 `task_card.json` 中 `affected_files` 范围

**失败处理**: Generator 报告阻塞 → 暂停流水线，展示阻塞原因给用户

---

### Phase 2: GAN 对抗审查（Discriminator Round 1）

**跳过条件**: `fast=true` 时跳过整个 Phase 2，直接进入 Phase 3。跳过时在最终报告中标注「⚡ 快速模式 — GAN 对抗审查已跳过」。

**设计思想**: Generator 和 Evaluator 分离是 Harness 的核心。两个 Reviewer 作为「鉴别者」独立评判代码质量，不受 Generator 自我评价偏差影响。

**Agent**: `code-reviewer-agent` + `security-reviewer-agent`（**并行**启动两个 Sub-agent）

**传入上下文（两者相同）**:
```
prompt: "请审查以下改动文件，task_card 位于 .ai/implement/{sprint}_{module}/task_card.json。
改动文件列表：$(cat .ai/implement/{sprint}_{module}/changed_files.txt)
请严格按六维度/安全维度审查，输出 VERDICT: PASS 或 FAIL。
将审查结果同时写入 .ai/implement/{sprint}_{module}/review_feedback.md。"
```

**VERDICT 汇总逻辑**:
- 两个 Reviewer 都返回 `VERDICT: PASS` → Phase 2 通过，进入 Phase 3
- 任一返回 `VERDICT: FAIL` → 进入修复循环

**修复循环（GAN Loop）**:

```
retry_count = 0
MAX_RETRY = 3

while any VERDICT == FAIL and retry_count < MAX_RETRY:
    1. 将 .ai/implement/{sprint}_{module}/review_feedback.md 中的 Critical 列表提取
    2. 启动 debugger-agent（Sub-agent）：
       prompt: "以下为审查反馈中的 Critical 问题，请最小化修复。
       反馈文件：.ai/implement/{sprint}_{module}/review_feedback.md
       改动文件：$(cat .ai/implement/{sprint}_{module}/changed_files.txt)
       只修复 Critical 问题，不重构、不改风格。修复后更新 changed_files.txt。"
    3. 修复完成后，重新启动 Phase 2 的两个 Reviewer（并行）
    4. retry_count += 1

if retry_count >= MAX_RETRY and still FAIL:
    暂停流水线，调用 AskQuestion:
    「GAN 对抗审查已循环 3 轮仍有 Critical 问题未解决。
    未解决的 Critical 问题：[列出]
    请选择：(A) 人工修复后继续 (B) 忽略继续执行测试 (C) 终止流水线」
```

---

### Phase 3: 单元测试（Discriminator Round 2 — 自发性测试）

**设计思想**: 代码审查是静态鉴别，测试是动态鉴别。先跑基于真实数据的单元测试，验证接口变更的正确性。

#### Step 3a: 生成单元测试用例

**Agent**: `api-test-agent`（Sub-agent 方式启动）

**传入上下文**:
```
prompt: "请根据 .ai/implement/{sprint}_{module}/task_card.json 中的接口变更和 .ai/implement/{sprint}_{module}/changed_files.txt 的改动文件，
连接本地 MySQL 查询真实数据，生成可复用的 pytest 单元测试文件。

要求：
1. 按正常执行流程识别改动面、推导数据依赖、查询真实样本、构建测试参数
2. 将测试用例保存到 tests/{sprint}/{module}_unit_test.py
3. 将测试数据保存到 tests/{sprint}/{module}_unit_data.yaml
4. 输出标准验证报告"
```

**完成标准**:
- `tests/{sprint}/{module}_unit_test.py` 已生成
- `tests/{sprint}/{module}_unit_data.yaml` 已生成

#### Step 3b: 执行单元测试

**Agent**: `test-runner-agent`（Sub-agent 方式启动）

**传入上下文**:
```
prompt: "请执行单元测试文件：tests/{sprint}/{module}_unit_test.py
测试类型：单元测试（自发性测试）
task_card 位于 .ai/implement/{sprint}_{module}/task_card.json
将测试结果写入 .ai/implement/{sprint}_{module}/unit_test_results.md
输出 VERDICT: PASS 或 FAIL。"
```

**VERDICT 处理**:
- `VERDICT: PASS` → 进入 Phase 4
- `VERDICT: FAIL` → 进入修复循环

**修复循环**:
```
retry_count = 0
MAX_RETRY = 3

while VERDICT == FAIL and retry_count < MAX_RETRY:
    1. 启动 debugger-agent（Sub-agent）：
       prompt: "单元测试失败，请根据以下信息最小化修复：
       测试结果：.ai/implement/{sprint}_{module}/unit_test_results.md
       改动文件：$(cat .ai/implement/{sprint}_{module}/changed_files.txt)
       只修复导致测试失败的代码，不修改测试用例本身。"
    2. 修复完成后，重新执行 Step 3b（test-runner-agent）
    3. retry_count += 1

if retry_count >= MAX_RETRY and still FAIL:
    暂停流水线，调用 AskQuestion:
    「单元测试已循环修复 3 轮仍有失败用例。
    失败用例：[列出]
    请选择：(A) 人工修复后继续 (B) 跳过单元测试继续集成测试 (C) 终止流水线」
```

---

### Phase 4: 集成测试（Discriminator Round 3 — 外部测试）

**跳过条件**: `task_card.json` 中 `test_cases` 字段为空或未提供 xmind 文件路径（task_card 位于 `.ai/implement/{sprint}_{module}/`）

若跳过，调用 `AskQuestion`:
「task_card 中未指定 xmind 测试用例文件。请选择：(A) 提供 xmind 文件路径继续 (B) 跳过集成测试直接进入最终报告」

#### Step 4a: 生成集成测试用例

**Agent**: `tester-gen-agent`（Sub-agent 方式启动）

**传入上下文**:
```
prompt: "请解析 xmind 文件生成 pytest 集成测试代码。
xmind 路径：{task_card.test_cases}
task_card 路径：.ai/implement/{sprint}_{module}/task_card.json
sprint: {task_card.sprint}
module: {task_card.module}

优先从 task_card.json 获取 API 结构上下文。
生成文件：tests/{sprint}/{module}_api_test.py
数据文件：tests/{sprint}/{module}_test_data.yaml"
```

**完成标准**:
- `tests/{sprint}/{module}_api_test.py` 已生成
- `tests/{sprint}/{module}_test_data.yaml` 已生成

#### Step 4b: 执行集成测试

**Agent**: `test-runner-agent`（Sub-agent 方式启动）

**传入上下文**:
```
prompt: "请执行集成测试文件：tests/{sprint}/{module}_api_test.py
测试类型：集成测试（外部测试 - xmind）
task_card 位于 .ai/implement/{sprint}_{module}/task_card.json
将测试结果写入 .ai/implement/{sprint}_{module}/integration_test_results.md
输出 VERDICT: PASS 或 FAIL。"
```

**VERDICT 处理**: 同 Phase 3 的修复循环逻辑（MAX_RETRY = 3，超限人类介入）

---

### Phase 5: 最终报告 + 人类确认

汇总所有阶段的执行结果，输出最终报告：

```markdown
## 🏁 implement 流水线执行报告

### 模式
{若 fast=true 则显示：⚡ 快速模式（已跳过 GAN 对抗审查），否则不显示此行}

### 概览
| 阶段 | Agent | VERDICT | 重试次数 |
|------|-------|---------|----------|
| Phase 0: 需求设计 | requirement-design-agent | ✅ 完成 | - |
| Phase 1: 代码生成 | generator-agent | ✅ 完成 | - |
| Phase 2: 代码审查 | code-reviewer + security-reviewer | PASS/FAIL/⚡SKIP | 0-3 |
| Phase 3: 单元测试 | api-test-agent + test-runner | PASS/FAIL | 0-3 |
| Phase 4: 集成测试 | tester-gen-agent + test-runner | PASS/FAIL/SKIP | 0-3 |

### 改动文件
$(cat .ai/implement/{sprint}_{module}/changed_files.txt)

### 测试覆盖
- 单元测试：tests/{sprint}/{module}_unit_test.py — {N} 个用例，通过率 {X}%
- 集成测试：tests/{sprint}/{module}_api_test.py — {N} 个用例，通过率 {X}%

### 审查摘要
- 代码审查：{Critical 数} Critical / {Improvement 数} Improvements
- 安全审查：{结论}

### task_card 状态
- 文件：.ai/implement/{sprint}_{module}/task_card.json
- 状态：done
```

更新 `task_card.json` 的 `status` 为 `done`。

**强制卡点**: 调用 `AskQuestion` —— 「流水线执行完毕，是否确认提交？(A) 确认，准备 commit (B) 需要调整 (C) 终止」

若用户选择 (A)，输出建议的 git commit message（中文）：
```
feat: {task_card.feature}

- 涉及文件：{affected_files}
- 测试覆盖：单元 {N} 例 + 集成 {N} 例
```

---

## GAN 对抗循环总览

```
┌──────────────────────────────────────────────────────────┐
│                   GAN 对抗质量提升机制                       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Generator                    Discriminator              │
│  ┌─────────────┐              ┌─────────────────┐       │
│  │ generator-  │  changed_    │ code-reviewer    │       │
│  │ agent       │──files.txt──▶│ security-reviewer│       │
│  │             │              │ (并行审查)        │       │
│  └──────▲──────┘              └────────┬────────┘       │
│         │                              │                 │
│         │                         VERDICT                │
│         │                              │                 │
│         │         ┌────────────────────┤                 │
│         │         │                    │                 │
│         │    FAIL + feedback      PASS │                 │
│         │         │                    ▼                 │
│         │    ┌────▼──────┐    ┌───────────────┐         │
│         │    │ debugger- │    │ api-test-agent │         │
│         │    │ agent     │    │ test-runner    │         │
│         │    │ (修复)     │    │ (单元测试)     │         │
│         │    └────┬──────┘    └───────┬───────┘         │
│         │         │                   │                  │
│         └─────────┘              VERDICT                 │
│         (retry ≤ 3)                   │                  │
│                           ┌───────────┤                  │
│                      FAIL │      PASS │                  │
│                           ▼           ▼                  │
│                      debugger    tester-gen-agent         │
│                      (修复)      test-runner              │
│                                  (集成测试)               │
│                                       │                  │
│                                  VERDICT                 │
│                                       │                  │
│                                  PASS ▼                  │
│                                   完成                    │
└──────────────────────────────────────────────────────────┘

每一层 Discriminator 都是独立的质量关卡：
- Round 1: 静态代码质量（审查）
- Round 2: 动态正确性（真实数据单元测试）
- Round 3: 业务完整性（xmind 集成测试）
```

## Key Principles

- **Context Reset**: 每个 Sub-agent 启动时通过文件契约获取上下文，不继承对话历史。Agent 完成后通过 `SendMessage` 返回结论，主流程只读取 VERDICT 和结果文件。
- **GAN 分离**: Generator 不自评代码质量，由独立的 Reviewer 和 Tester 评判。Debugger 只修复 Evaluator 报告的问题，不做额外重构。
- **渐进式鉴别**: 静态审查 → 单元测试 → 集成测试，层层递进，越早发现问题修复成本越低。
- **测试用例持久化**: 所有生成的测试保存到 `tests/{sprint}/` 目录，后续迭代可复用。
- **人类卡点**: Phase 0 结束后、GAN 循环超限时、Phase 4 跳过判断时、最终报告后 —— 关键决策交给人类。
- **最多 3 轮重试**: 每个 GAN 循环最多 3 轮自动修复，超限升级给人类，防止无限循环消耗 Token。
- **歧义必须停下**: 任何 Agent 遇到上下文缺失或歧义时，必须暂停向用户确认，禁止猜测。

## Command Format

```
/implement <需求描述>
```

或带参数：
```
/implement <需求描述> [sprint=sprint_name] [module=module_name] [xmind=/path/to/xxx.xmind] [fast=true]
```

或从已有 task_card 继续：
```
/implement task_card=.ai/implement/{sprint}_{module}/task_card.json [xmind=/path/to/xxx.xmind] [fast=true]
```

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| 需求描述 | 是（与 task_card 二选一） | 自然语言需求，触发 Phase 0 |
| `task_card` | 否 | 已有 task_card.json 路径，跳过 Phase 0 |
| `sprint` | 否 | Sprint 名称，默认按日期生成如 `sprint_2026_04` |
| `module` | 否 | 模块名，用于文件路径 `.ai/implement/{sprint}_{module}/` |
| `xmind` | 否 | xmind 测试用例路径，用于 Phase 4 集成测试 |
| `fast` | 否 | 设为 `true` 时跳过 Phase 2 GAN 对抗审查，节省约 30%-40% Token 消耗。适用于原型验证、低风险改动等场景。**不建议在核心业务逻辑或涉及安全/鉴权的功能上使用** |

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
