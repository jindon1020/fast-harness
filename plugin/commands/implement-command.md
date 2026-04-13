# implement-command

## Task
端到端需求实现流水线：需求设计 → 代码生成 → GAN 对抗审查 → 单元测试 → 集成测试，产出通过全部测试的可提交代码。

## Context

基于 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 三体架构：Planner → Generator → Evaluator。
- GAN 分离：Generator 与 Evaluator 独立，消除自我评价偏差
- Context Reset：Agent 间通过文件契约传递状态，不依赖对话历史
- 渐进式鉴别：静态审查 → 单元测试 → 集成测试

### File Contracts

**Path**: `.ai/implement/{branch}_{module}/`

| 文件 | 写入方 | 读取方 | 用途 |
|------|--------|--------|------|
| `task_card.json` | Planner | 全体 | 需求/API/DB 完整上下文 |
| `changed_files.txt` | Generator | Reviewer/Tester | 改动文件列表 |
| `review_feedback.md` | Reviewer | Debugger/Generator | 审查反馈 |
| `unit_test_results.md` | Test Runner | Debugger | 单元测试结果 |
| `integration_test_results.md` | Test Runner | Debugger | 集成测试结果 |
| `tests/{branch}/` | api-test/tester-gen | Test Runner | 持久化测试用例 |

### Test Categories

| 类型 | 生成方式 | Agent | 产出 |
|------|----------|-------|------|
| 单元测试（自发性） | 查询本地 DB 真实数据 | `unit-test-gen-agent` | `tests/{branch}/{module}_unit_test.py` |
| 集成测试（外部） | 解析 xmind 脑图 | `integration-test-gen-agent` | `tests/{branch}/{module}_api_test.py` |

## Command Format

```
/implement <需求描述> [module=xxx] [xmind=...] [mode=fast] [unit_test=off] [inte_test=off]
/implement task_card=<path> [xmind=...] [mode=fast] [unit_test=off] [inte_test=off]
```

### 输入参数

| 参数 | 必填 | 说明 |
|------|------|------|
| 需求描述 | 二选一 | 自然语言需求，触发 Phase 0 需求设计 |
| `task_card` | 二选一 | 已有 `task_card.json` 路径，跳过 Phase 0 |

### 上下文参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `module` | 自动推断 | 模块名。未传入时从需求描述或分支名推断 |
| `xmind` | - | xmind 测试用例路径，用于集成测试（Phase 4） |

### 流水线控制参数

| 参数 | 默认值 | 取值 | 说明 |
|------|--------|------|------|
| `mode` | `full` | `full` / `fast` | `fast` 跳过 Phase 2 GAN 审查（省 30-40% Token）。不建议在核心业务/安全鉴权使用 |
| `unit_test` | `on` | `on` / `off` / `<module>` | `off` 跳过 Phase 3；传模块名仅运行该模块的单元测试 |
| `inte_test` | `on` | `on` / `off` / `<module>` | `off` 跳过 Phase 4；传模块名仅运行该模块的集成测试 |

> `branch` 自动检测：`git rev-parse --abbrev-ref HEAD | tr '/' '_'`

## Pre-flight

1. 检查参数完整性：至少需要需求描述或 `task_card` 路径
2. `BRANCH=$(git rev-parse --abbrev-ref HEAD | tr '/' '_')`，`module` 未传入时从需求描述或分支名推断
3. 传入 `task_card=...` 且文件存在 → 跳过 Phase 0
4. 解析运行模式，向用户确认流水线配置：
   - `mode=fast` → 跳过 Phase 2 GAN 审查
   - `unit_test=off` → 跳过 Phase 3 单元测试；`unit_test={module_name}` → Phase 3 仅运行指定模块
   - `inte_test=off` → 跳过 Phase 4 集成测试；`inte_test={module_name}` → Phase 4 仅运行指定模块
5. 告知用户流水线路径：
   - 完整模式（默认）：「需求设计 → 代码生成 → GAN 审查 → 单元测试 → 集成测试。关键节点暂停确认」
   - 快速模式（mode=fast）：「需求设计 → 代码生成 → 单元测试 → 集成测试」
   - 根据 unit_test/inte_test 开关动态裁剪路径展示

## Execution Steps

### Phase 0: 需求设计（Planner）

**Agent**: `requirement-design-agent` (Sub-agent)
**Skip if**: `task_card` 参数指向已存在文件

传入用户需求描述、branch、可选参数（module、xmind）。Agent 内部含多步骤人类确认流程（需求理解 → 技术方案 → DB 设计 → API 设计 → 业务逻辑 → 侵入性检查）。

**Done when**: `task_card.json` 已写入（status: inbox） + `.ai/design/{branch}_{feature}.md` 已生成
**Checkpoint**: AskQuestion — 「需求设计已完成，task_card.json 已生成。是否进入代码生成阶段？」

### Phase 1: 代码生成（Generator）

**Agent**: `generator-agent` (Sub-agent)

**Prompt**:
> 请根据 .ai/implement/{branch}_{module}/task_card.json 实现代码。完成后将改动文件列表写入 .ai/implement/{branch}_{module}/changed_files.txt，并更新 task_card.json 的 status 为 in_progress。

**Done when**: `changed_files.txt` 已生成 + status → `in_progress` + 改动不超出 `affected_files` 范围
**On block**: 暂停流水线，展示阻塞原因

### Phase 2: GAN 对抗审查（Discriminator Round 1）

**Skip if**: `mode=fast`（报告中标注「⚡ 快速模式 — GAN 审查已跳过」）

**Agents**: `code-reviewer-agent` + `security-reviewer-agent` (并行 Sub-agent)

**Prompt** (both):
> 请审查以下改动文件，task_card 位于 .ai/implement/{branch}_{module}/task_card.json。
> 改动文件列表：$(cat .ai/implement/{branch}_{module}/changed_files.txt)
> 请严格按六维度/安全维度审查，输出 VERDICT: PASS 或 FAIL。
> 将审查结果同时写入 .ai/implement/{branch}_{module}/review_feedback.md。

**Verdict**: 两者都 PASS → Phase 3 | 任一 FAIL → Retry Loop
**Retry Loop** (MAX=3): 提取 review_feedback.md 中 Critical → `debugger-agent` 最小化修复（只改 Critical，不重构不改风格，更新 changed_files.txt）→ 重新并行审查。超限 → AskQuestion「已循环 3 轮仍有 Critical：[列出]。(A) 人工修复后继续 (B) 忽略继续测试 (C) 终止」

### Phase 3: 单元测试（Discriminator Round 2）

**Skip if**: `unit_test=off`（报告中标注「⏭️ 单元测试已跳过（unit_test=off）」）
**Scope**: `unit_test={module_name}` 时仅运行 `tests/{branch}/{module_name}_unit_test.py`，报告标注「🎯 单元测试范围：{module_name}」

#### Step 3a: 生成测试用例

**Agent**: `unit-test-gen-agent` (Sub-agent)

**Prompt**:
> 请根据 .ai/implement/{branch}_{module}/task_card.json 中的接口变更和 changed_files.txt，
> 连接本地 MySQL 查询真实数据，生成 pytest 单元测试。
> 要求：识别改动面、推导数据依赖、查询真实样本、构建测试参数。
> 保存到 tests/{branch}/{module}_unit_test.py 和 tests/{branch}/{module}_unit_data.yaml。输出标准验证报告。

**Done when**: 测试文件 + 数据文件已生成

#### Step 3b: 执行测试

**Agent**: `test-runner-agent` (Sub-agent)

**Prompt**:
> 执行 tests/{branch}/{test_target_module}_unit_test.py，测试类型：单元测试（自发性测试）。
> task_card 位于 .ai/implement/{branch}_{module}/task_card.json。
> 结果写入 .ai/implement/{branch}_{module}/unit_test_results.md，输出 VERDICT。

> 其中 `test_target_module` = unit_test 参数值（若为模块名）或当前 module。

**Verdict**: PASS → Phase 4 | FAIL → Retry Loop
**Retry Loop** (MAX=3): `debugger-agent` 根据 unit_test_results.md 最小化修复代码（不改测试）→ 重新执行 Step 3b。超限 → AskQuestion「已循环 3 轮：[列出失败]。(A) 人工修复 (B) 跳过继续集成测试 (C) 终止」

### Phase 4: 集成测试（Discriminator Round 3）

**Skip if**: `inte_test=off`（报告中标注「⏭️ 集成测试已跳过（inte_test=off）」）
**Skip if**: task_card.json 中 `test_cases` 为空或无 xmind → AskQuestion「未指定 xmind。(A) 提供路径继续 (B) 跳过进入报告」
**Scope**: `inte_test={module_name}` 时仅运行 `tests/{branch}/{module_name}_api_test.py`，报告标注「🎯 集成测试范围：{module_name}」

#### Step 4a: 生成测试用例

**Agent**: `integration-test-gen-agent` (Sub-agent)

**Prompt**:
> 解析 xmind 生成 pytest 集成测试。xmind: {task_card.test_cases}，task_card: .ai/implement/{branch}_{module}/task_card.json。
> 优先从 task_card 获取 API 上下文。
> 生成 tests/{branch}/{module}_api_test.py 和 tests/{branch}/{module}_test_data.yaml。

#### Step 4b: 执行测试

**Agent**: `test-runner-agent` (Sub-agent)

**Prompt**:
> 执行 tests/{branch}/{test_target_module}_api_test.py，测试类型：集成测试（外部测试 - xmind）。
> task_card 位于 .ai/implement/{branch}_{module}/task_card.json。
> 结果写入 .ai/implement/{branch}_{module}/integration_test_results.md，输出 VERDICT。

> 其中 `test_target_module` = inte_test 参数值（若为模块名）或当前 module。

**Retry Loop**: 同 Phase 3（MAX=3，超限人类介入）

### Phase 5: 最终报告

输出报告，更新 task_card.json status → `done`：

```markdown
## 🏁 implement 流水线执行报告

### 模式
{mode=fast：⚡ 快速模式（已跳过 GAN 审查）}
{unit_test=off：⏭️ 单元测试已跳过}
{inte_test=off：⏭️ 集成测试已跳过}
{unit_test/inte_test 为模块名：🎯 测试范围已限定}

### 概览
| 阶段 | Agent | VERDICT | 重试 |
|------|-------|---------|------|
| Phase 0: 需求设计 | requirement-design-agent | ✅ | - |
| Phase 1: 代码生成 | generator-agent | ✅ | - |
| Phase 2: 代码审查 | code-reviewer + security-reviewer | PASS/FAIL/⚡SKIP | 0-3 |
| Phase 3: 单元测试 | unit-test-gen-agent + test-runner | PASS/FAIL/⏭️SKIP | 0-3 |
| Phase 4: 集成测试 | integration-test-gen-agent + test-runner | PASS/FAIL/⏭️SKIP | 0-3 |

### 改动文件
$(cat .ai/implement/{branch}_{module}/changed_files.txt)

### 测试覆盖
- 单元测试：tests/{branch}/{module}_unit_test.py — {N} 用例，通过率 {X}%
- 集成测试：tests/{branch}/{module}_api_test.py — {N} 用例，通过率 {X}%

### 审查摘要
- 代码审查：{Critical 数} Critical / {Improvement 数} Improvements
- 安全审查：{结论}

### task_card 状态
.ai/implement/{branch}_{module}/task_card.json → done
```

**Checkpoint**: AskQuestion —「流水线完毕，是否确认提交？(A) 确认 commit (B) 需要调整 (C) 终止」

选 (A) 输出 commit message：
```
feat: {task_card.feature}
- 涉及文件：{affected_files}
- 测试覆盖：单元 {N} 例 + 集成 {N} 例
```

## Key Principles

- **Context Reset**: Sub-agent 从文件契约获取上下文，不继承对话历史
- **GAN 分离**: Generator 不自评，Reviewer/Tester 独立评判；Debugger 只修复已报告问题，不做额外重构
- **渐进式鉴别**: Round 1 静态审查 → Round 2 单元测试 → Round 3 集成测试
- **测试持久化**: 保存到 `tests/{branch}/`，后续可复用
- **人类卡点**: Phase 0 后、GAN/测试超限时、Phase 4 跳过判断时、最终报告后
- **最多 3 轮重试**: 超限升级人类，防止无限循环消耗 Token
- **歧义必须停下**: Agent 遇到缺失/歧义必须暂停确认，禁止猜测

## Historical Context

在 Pre-flight 阶段，读取项目根目录 `AGENTS.md` 中的「流水线执行归档」章节，利用历史执行记录提升流水线质量：

1. **同模块历史**: 查找与当前 `module` 相关的历史 implement 记录，复用已有 `task_card.json` 中的接口设计、DB Schema 和技术方案（`.ai/design/`），避免从零设计
2. **审查经验**: 参考历史 `review_feedback.md` 的 Critical/Improvements，在 Phase 1 代码生成阶段主动规避已知问题
3. **测试资产**: 复用 `tests/{branch}/` 下已有的测试用例和数据文件，Phase 3/4 只生成增量测试
4. **设计文档**: 若涉及跨模块依赖，通过归档索引定位相关模块的 `task_card.json` 了解接口契约

> 若 `AGENTS.md` 不存在或无归档记录，跳过此步骤正常执行。

## Project Context

> 项目上下文已集中管理，不再使用占位符。
> 所有 Sub-agent 启动时自动读取 `.ether/project-context.md` 获取项目路径、目录结构、开发服务器等信息。
> 中间件连接配置（MySQL、Redis、Kafka 等）从 `.ether/config/infrastructure.json` 读取。
