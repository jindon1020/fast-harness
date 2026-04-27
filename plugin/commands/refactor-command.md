# refactor-command

## Task
批量代码重构流水线：范围定义 → 基线快照 → 批量重构 → 行为等价验证 → 质量审计，产出结构改善且行为不变的可提交代码。

## Context

基于 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 三体架构：Refactorer → Tester → Reviewer。
- 定位：改善内部结构，**行为不变**是硬约束。区别于 implement（新建）/ modify（行为变更）/ fix（修 Bug）
- 顺序差异：**测试在审查之前**，行为不变是第一约束，必须先验证通过再审查结构改善质量
- Context Reset：Agent 间通过文件契约传递状态，不依赖对话历史

### 重构来源

审查反馈（Improvements/Nitpicks）| 复杂度告警（radon cc C/D/E 级）| 重复代码（pylint duplicate-code）| 架构违规（跨层引用）| 技术债务 | 用户指令

### 重构类型

| 代号 | 说明 | 执行顺序 |
|------|------|----------|
| `restructure` | 修复架构违规，恢复层级依赖方向 | 1 |
| `move` | 调整代码归属层级或模块 | 2 |
| `extract` | 提取大函数/重复逻辑为独立函数或模块 | 3 |
| `deduplicate` | 合并重复代码为公共组件 | 4 |
| `simplify` | 降低圈复杂度，消除冗余分支 | 5 |
| `rename` | 统一命名规范，消除歧义 | 6 |

> 先修正结构再动逻辑，最后改命名，避免交叉冲突产生无意义 diff

### File Contracts

**Path**: `.ai/refactor/{module}/{branch}_{序号}/`（refactor_id = `{module}/{branch}_{序号}`）

| 文件 | 写入方 | 读取方 | 用途 |
|------|--------|--------|------|
| `refactor_plan.md` | Phase 0 | 全体 | 重构计划（目标、范围、预期改善） |
| `baseline_snapshot.md` | Phase 1 | Phase 3/5 | 重构前测试基线 + 质量指标 |
| `changed_files.txt` | Phase 2 | Reviewer/Tester | 重构文件列表 |
| `behavior_test_results.md` | test-runner | debugger-agent | 行为等价验证结果 |
| `review_feedback.md` | Reviewer | 修复参考 | 质量审计反馈 |
| `metrics_comparison.md` | Phase 5 | 用户 | 重构前后指标对比 |
| `git_checkpoint.txt` | Pre-flight | Phase 5 | HEAD hash，用于紧急回退 |

## Command Format

```
/refactor <重构目标描述> [module=xxx] [scope=app/services/] [mode=fast] [unit_test=off] [inte_test=off]
/refactor from=implement [module=xxx] [mode=fast] [unit_test=off] [inte_test=off]
/refactor plan=<path> [mode=fast] [unit_test=off] [inte_test=off]
```

### 输入参数

| 参数 | 必填 | 说明 |
|------|------|------|
| 重构目标描述 | 三选一 | 自然语言描述重构意图，触发 Phase 0 诊断扫描 |
| `from` | 三选一 | `implement` 时从审查反馈提取 Improvements/Nitpicks |
| `plan` | 三选一 | 已有 `refactor_plan.md` 路径，跳过 Phase 0 |

### 上下文参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `module` | 自动推断 | 模块名。未传入时从重构描述或分支名推断 |
| `scope` | - | 限定重构扫描范围（目录或文件路径），缩小诊断和改动边界 |

### 流水线控制参数

| 参数 | 默认值 | 取值 | 说明 |
|------|--------|------|------|
| `mode` | `full` | `full` / `fast` | `fast` 跳过 Phase 4 质量审计（省 20-30% Token），行为验证仍执行。适用于 rename/move 等低风险重构 |
| `unit_test` | `on` | `on` / `off` / `<module>` | `off` 跳过 Phase 1/3 单元测试基线与验证；传模块名仅运行该模块的单元测试 |
| `inte_test` | `on` | `on` / `off` / `<module>` | `off` 跳过 Phase 1/3 集成测试基线与验证；`on` 在测试文件存在时自动纳入基线；传模块名仅运行该模块的集成测试 |

> `branch` 自动检测：`git rev-parse --abbrev-ref HEAD | tr '/' '_'`

## Pre-flight

1. 检查参数：至少需要重构目标描述或审查反馈文件
2. `BRANCH=$(git rev-parse --abbrev-ref HEAD | tr '/' '_')`
3. `from=implement` → 从 `.ai/implement/{module}/{branch}/review_feedback.md` 读取 Improvements/Nitpicks + task_card.json 上下文 + 复用已有测试文件
4. 解析运行模式，向用户确认流水线配置：
   - `mode=fast` → 跳过 Phase 4 质量审计
   - `unit_test=off` → Phase 1/3 跳过单元测试基线采集与行为验证；`unit_test={module_name}` → 仅运行指定模块的单元测试
   - `inte_test=off` → Phase 1/3 跳过集成测试基线采集与行为验证；`inte_test={module_name}` → 仅运行指定模块的集成测试
5. 告知用户流水线路径：
   - 完整模式（默认）：「范围定义 → 基线快照 → 批量重构 → 行为验证 → 质量审计。**不会改变任何接口外部行为**」
   - 快速模式（mode=fast）：「范围定义 → 基线快照 → 批量重构 → 行为验证。**不会改变任何接口外部行为**」
   - 根据 unit_test/inte_test 开关动态裁剪基线采集和验证范围
6. 创建 Git 安全检查点：
```bash
mkdir -p .ai/refactor/{refactor_id}
git rev-parse HEAD > .ai/refactor/{refactor_id}/git_checkpoint.txt
git stash list > .ai/refactor/{refactor_id}/stash_before.txt
```

## Execution Steps

### Phase 0: 范围定义与重构计划

**执行者**: refactor-command 自身 + `code-reviewer-agent`（诊断扫描）

**若来自审查反馈**: 从 `review_feedback.md` 提取 Improvements/Nitpicks
**若来自用户指令**: `code-reviewer-agent` (Sub-agent，只读诊断) 对目标范围扫描：
> ⛔ **MANDATORY DELEGATION**: 诊断扫描必须通过 Sub-agent 委托执行。
> Planner 禁止自行扫描代码、直接生成重构计划或跳过委托。
> 未收到 code-reviewer-agent 的扫描完成响应前，禁止写入 refactor_plan.md。

**Prompt**:
> 对以下范围执行诊断扫描，不输出 VERDICT，只输出改善建议：
> 目标：{重构意图} | 扫描范围：{目录或文件}
> 输出维度：1) 圈复杂度 radon cc C 级以上 2) 重复代码 pylint duplicate-code 3) 架构合规 rg 跨层引用 4) 命名一致性
> 每项含文件路径、行号、问题描述。

生成 `refactor_plan.md`：

```markdown
# Refactor Plan: {refactor_id}

## 重构目标
{一句话}

## 来源
- 类型: 审查反馈/复杂度告警/重复代码/架构违规/技术债务/用户指令
- 关联 implement: .ai/implement/{module}/{branch}/（若有）

## 重构项清单
| ID | 类型 | 文件 | 位置 | 问题描述 | 重构方案 | 优先级 |
|----|------|------|------|----------|----------|--------|

## 不可触碰边界
- router 接口签名（path/method/request/response）不得改变
- schema 字段定义不得改变
- models/ 不在重构范围
- 已有测试用例断言逻辑不得修改
- 不得新增或删除 API 接口

## 预期改善指标
{圈复杂度/重复代码/架构合规 数值目标}

## 受影响文件
{列表}
```

🔴 **HARD STOP — 人类确认卡点**
**必须执行 AskQuestion**：「重构计划已生成。(A) 确认范围开始 (B) 调整范围 (C) 终止」
禁止推断用户意图自动继续。未收到用户明确回复前，流水线在此终止等待。

### Phase 1: 基线快照（Baseline Capture）

#### Step 1a: 运行已有测试

**Agent**: `test-runner-agent` (Sub-agent)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须通过 Sub-agent 委托执行。
> Planner 禁止自行运行测试或替代 test-runner-agent 输出基线结果。
> 未收到 test-runner-agent 的基线完成响应前，禁止进入 Phase 2。

**测试范围根据开关动态裁剪**:
- `unit_test=off` → 跳过 `tests/{router}/` 单元测试基线采集
- `inte_test=off` → 跳过 `{module}_api_test.py` 基线采集
- `unit_test={router_name}` → 仅采集 `tests/{router_name}/` 下单元测试
- `inte_test={module_name}` → 仅采集 `{module_name}_api_test.py`

**Prompt**:
> 运行以下测试建立基线快照（不做 VERDICT 判断，只记录结果）：
> 1) tests/{router}/（若 unit_test 未关闭；`unit_test={router_name}` 时仅该目录；否则由 orchestrator 根据重构范围解析 router 列表）
> 2) tests/{branch}/{test_target_module}_api_test.py（若 inte_test 未关闭）
> 3) 重构范围相关测试
> 写入 baseline_snapshot.md，格式：每用例 ID/名称/状态(PASS/FAIL/SKIP)/耗时。

#### Step 1b: 采集质量指标

```bash
radon cc {受影响文件} -s -j > .ai/refactor/{refactor_id}/cc_before.json
rg "from app\.dao" app/routers/ -c --glob "*.py" 2>/dev/null || echo "0"
rg "from app\.services" app/dao/ -c --glob "*.py" 2>/dev/null || echo "0"
```

将指标追加到 `baseline_snapshot.md`（圈复杂度表 + 架构合规 + 测试基线统计）。

**关键规则**:
- 基线已有 FAIL → 标记为 `known_failures`，重构后不得恶化
- 基线 PASS → 重构后必须全部 PASS
- 无有效基线 → AskQuestion「无测试基线，无法验证行为等价。(A) 先生成测试 (B) 接受风险继续 (C) 终止」

### Phase 2: 批量重构执行

**执行者**: refactor-command 自身

按 `refactor_plan.md` 优先级 + 固定类型顺序（restructure → move → extract → deduplicate → simplify → rename）逐项执行。

**执行规则**:
- **原子记录**: 每项完成后 `git diff --name-only >> changed_files.txt`
- **不可触碰红线**: 不改外部接口签名/schema/router/测试断言/不增删 API
- **全部完成**: `sort -u changed_files.txt -o changed_files.txt`

### Phase 3: 行为等价验证

**Skip if**: `unit_test=off` 且 `inte_test=off`（报告中标注「⏭️ 行为等价验证全部跳过」，⚠️ 高风险：无法保证行为不变）

#### Step 3a: 运行全量测试

**Agent**: `test-runner-agent` (Sub-agent)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须通过 Sub-agent 委托执行。
> Planner 禁止自行运行测试或替代输出行为等价验证结果。
> 未收到 test-runner-agent 的书面 VERDICT 响应前，禁止进入 Step 3b。

**测试范围与 Phase 1 基线一致**（跟随 unit_test/inte_test 开关裁剪）

**Prompt**:
> 运行与 Phase 1 基线完全一致的测试范围，验证重构后行为等价。
> 写入 behavior_test_results.md，输出 VERDICT。
> PASS 条件（严格）：基线 PASS 用例仍 PASS + 基线 FAIL 不恶化 + 无新增失败。

**Verdict**: PASS → Step 3b | FAIL → Retry Loop
**Retry Loop** (MAX=2): `debugger-agent` 修复（只调整重构实现，不改测试断言；测试断言有问题则报告等人类决策）→ 重新验证。超限 → AskQuestion「已循环 2 轮，重构可能改变了外部行为。[列出]。(A) 人工修复 (B) 回退重构 git checkout (C) 终止」

> 选 (B) 时：`git checkout $(cat git_checkpoint.txt) -- {受影响文件}`

#### Step 3b: 补充覆盖验证（按需）

**Skip if**: `unit_test=off`

若重构涉及的代码路径无测试覆盖，启动 `unit-test-gen-agent` (Sub-agent) 补充回归测试：

> ⛔ **MANDATORY DELEGATION**: 本步骤必须通过 Sub-agent 委托执行。
> Planner 禁止自行生成测试或直接写入测试文件。
> 未收到 unit-test-gen-agent 的 VERDICT 前不得继续验证。

**Prompt**:
> 为重构后的代码补充回归测试。重构计划：refactor_plan.md，改动文件：changed_files.txt。
> 重点覆盖：1) 被提取的公共函数入参出参一致性 2) 被简化的逻辑各分支行为不变 3) 被移动的模块调用链路不变
> 追加到 tests/{router}/{router}_unit_test.py（router 由 changed_files 中 `app/routers/*.py` 推导），标记 @pytest.mark.refactor + @pytest.mark.unit

补充后再执行一轮 test-runner-agent 验证。

### Phase 4: 质量审计

**Skip if**: `mode=fast`（报告中标注「⚡ 快速模式 — 质量审计已跳过」）

**Agents**: `code-reviewer-agent` + `security-reviewer-agent` (并行 Sub-agent)
> ⛔ **MANDATORY DELEGATION**: 本步骤必须同时委托两个 Sub-agent 并行执行质量审计。
> Planner 禁止自行执行审查、直接输出 VERDICT 或跳过任意一个 Agent。
> 未同时收到两个 Agent 的 VERDICT 响应前，禁止进入 Phase 5。

**Prompt** (both):
> 审查以下重构代码（结构优化，非新功能/非 Bug 修复），重点关注：
> 1. 是否达成 refactor_plan.md 预期改善目标
> 2. 代码结构是否确实更清晰
> 3. 是否引入不必要抽象层级
> 4. 重命名/移动后 import 是否全部更新
> 5. 是否有遗漏引用（其他文件仍引用旧路径/旧名称）
> refactor_plan.md + changed_files.txt + baseline_snapshot.md
> 输出 VERDICT，写入 review_feedback.md。

**Verdict**: 两者都 PASS → Phase 5 | 任一 FAIL → Retry Loop
**Retry Loop** (MAX=1): `debugger-agent` 修复 Critical → 重新执行 Phase 3 + Phase 4。仍 FAIL → 标记问题，**不阻塞提交**但在报告中显著标注

> 审计循环仅 1 轮。重构不应产生 Critical，1 轮修不好说明方案本身有问题

### Phase 5: 重构报告

#### Step 5a: 采集重构后指标

```bash
radon cc {受影响文件} -s -j > .ai/refactor/{refactor_id}/cc_after.json
rg "from app\.dao" app/routers/ -c --glob "*.py" 2>/dev/null || echo "0"
rg "from app\.services" app/dao/ -c --glob "*.py" 2>/dev/null || echo "0"
```

#### Step 5b: 输出报告

```markdown
## ♻️ refactor 重构流水线执行报告

### 模式
{mode=fast：⚡ 快速模式（已跳过质量审计）}
{unit_test=off：⏭️ 单元测试验证已跳过}
{inte_test=off：⏭️ 集成测试验证已跳过}
{unit_test/inte_test 为模块名：🎯 测试范围已限定}

### 概览
| 阶段 | Agent | VERDICT | 重试 |
|------|-------|---------|------|
| Phase 0: 范围定义 | code-reviewer (诊断) | ✅ | - |
| Phase 1: 基线快照 | test-runner | ✅ {N} 例基线 | - |
| Phase 2: 批量重构 | refactor-command | ✅ {M} 项完成 | - |
| Phase 3: 行为验证 | test-runner | PASS/FAIL/⏭️SKIP | 0-2 |
| Phase 4: 质量审计 | code-reviewer + security-reviewer | PASS/FAIL/⚡SKIP | 0-1 |

### 重构项执行
| ID | 类型 | 文件 | 状态 |
|----|------|------|------|

### 改善指标对比
| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|

### 行为等价验证
基线用例 {N} 个 → 重构后通过 {N} 个 → 行为等价 ✅ 100%（若跳过则标注 ⏭️ SKIP）

### 改动文件
$(cat .ai/refactor/{refactor_id}/changed_files.txt)
```

🔴 **HARD STOP — 人类确认卡点**
**必须执行 AskQuestion**：「重构流水线完毕。(A) 确认 commit (B) 需要调整 (C) 回退所有改动」
禁止推断用户意图自动继续。未收到用户明确回复前，流水线在此终止等待。

选 (A) 输出 commit message：
```
refactor: {重构目标一句话}
- 重构项：{N} 项（extract {X} / simplify {Y} / restructure {Z}）
- 圈复杂度改善：max D→B
- 行为验证：{N} 例全通过
```

选 (C)：`git checkout $(cat git_checkpoint.txt) -- $(cat changed_files.txt)`

## Key Principles

- **行为不变第一约束**: 用测试基线严格验证，宁可多跑一轮测试也不放过行为变更
- **测试先于审查**: 先验证行为不变（Phase 3），再审计结构改善（Phase 4）
- **可度量改善**: 必须产出前后指标对比，不接受"感觉更好了"
- **Git 安全检查点**: 重构前记录 HEAD，支持一键回退
- **原子记录**: 每个重构项单独记录改动，出问题精准定位
- **批量有序**: 固定执行顺序 restructure→move→extract→deduplicate→simplify→rename
- **审计不强阻塞**: Phase 4 FAIL 不阻断提交（行为已验证），但报告中显著标注
- **Context Reset**: Agent 间通过文件契约通信，不继承对话历史

### 禁止行为（无论任务复杂度如何，一律适用）
- 禁止以「重构小」「改动少」为由跳过标注 (Sub-agent) 的步骤
- 禁止 Planner 自行进行诊断扫描、测试执行或质量审计（即便能力上可行）
- 禁止自动通过 HARD STOP 卡点，必须等待用户明确响应
- 禁止在未收到上一阶段 VERDICT 的情况下进入下一阶段
- 禁止省略 Pre-flight 的流水线配置确认步骤

## Historical Context

在 Pre-flight 阶段，读取项目根目录 `AGENTS.md` 中的「流水线执行归档」章节，利用历史执行记录制定更精准的重构计划：

1. **历史重构**: 查找同模块/同 scope 的历史 refactor 记录，读取 `refactor_plan.md` 和 `metrics_comparison.md` 了解已完成的改善和残留技术债
2. **接口契约**: 通过历史 implement/modify 记录的 `task_card.json`/`change_card.json` 确认不可触碰的接口边界
3. **审查积压**: 参考历史 `review_feedback.md` 中的 Improvements/Nitpicks，纳入重构范围一并解决
4. **测试基线**: 单元测试复用 `tests/{router}/`；集成测试复用 `tests/{branch}/`，作为行为等价验证基线

> 若 `AGENTS.md` 不存在或无归档记录，跳过此步骤正常执行。

## Project Context

> 项目上下文已集中管理，不再使用占位符。
> 所有 Sub-agent 启动时自动读取 `.ether/project-context.md` 获取项目路径、目录结构、开发服务器等信息。
> 中间件连接配置（MySQL、Redis、Kafka 等）从 `.ether/config/infrastructure.json` 读取。
