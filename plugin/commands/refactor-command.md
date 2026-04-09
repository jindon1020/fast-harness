# refactor-command

## Task
批量代码重构流水线：从重构目标出发，经过范围定义、基线快照、批量重构执行、行为等价验证、质量审计，最终产出结构改善且行为不变的可提交代码。

## Context

与 `implement` 和 `fix` 流水线互补：
- **implement** = 正向构建流水线（从零到一）：新增功能，**行为变更**是目标
- **fix** = 修复闭环流水线（从一到一）：最小化修复，**行为修正**是目标
- **refactor** = 结构优化流水线（从一到更好的一）：改善内部结构，**行为不变**是硬约束

核心设计原则：
> **Refactoring is the process of changing a software system in such a way that it does not alter the external behavior of the code yet improves its internal structure.** — Martin Fowler

基于相同的 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 三体架构：
- **Refactorer**（重构执行）→ **Tester**（行为等价验证）→ **Reviewer**（质量审计）
- 注意顺序差异：重构流水线中**测试在审查之前**。因为行为不变是第一约束，必须先验证通过，再审查结构改善质量。
- **Context Reset**：Agent 间通过文件契约传递状态

### 重构来源分类

| 来源 | 输入形式 | 典型场景 |
|------|----------|----------|
| **审查反馈** | code-reviewer 的 Improvements/Nitpicks 项 | implement 流水线的非阻塞改进建议积压 |
| **复杂度告警** | `radon cc` 输出 C/D/E 级函数 | 函数圈复杂度超标，需拆分 |
| **重复代码** | `pylint duplicate-code` 检测结果 | 多处相同逻辑片段需提取公共函数 |
| **架构违规** | `rg` 扫描跨层引用 | router 直接调 dao、dao 反引 service 等 |
| **技术债务** | 团队积压的技术债清单 | 命名不规范、模块边界模糊、配置硬编码等 |
| **用户指令** | 自然语言描述重构意图 | 「把 shot_service 里的分页逻辑抽到 utils」 |

### 重构类型分类

| 类型 | 代号 | 说明 | 典型操作 |
|------|------|------|----------|
| **提取** | `extract` | 将大函数/重复逻辑提取为独立函数或模块 | 提取公共分页、提取校验器、提取 DTO 转换 |
| **重命名** | `rename` | 统一命名规范，消除歧义 | 变量/函数/文件重命名 |
| **移动** | `move` | 调整代码归属层级或模块 | 从 service 移到 utils、从 dao 移到 gateway |
| **简化** | `simplify` | 降低圈复杂度，消除冗余分支 | 提前返回、策略模式替代多层 if-else |
| **去重** | `deduplicate` | 合并重复代码为公共组件 | 合并相似 DAO 方法、统一异常处理模板 |
| **分层修正** | `restructure` | 修复架构违规，恢复层级依赖方向 | 消除跨层引用、隔离副作用 |

### 文件契约（Agent 间通信协议）

文件保存路径：`.ai/refactor/{refactor_id}/`

`refactor_id` 命名规则：`{sprint}_{scope}_{序号}`，如 `sprint_2026_04_service_layer_001`

| 契约文件 | 写入方 | 读取方 | 用途 |
|----------|--------|--------|------|
| `.ai/refactor/{refactor_id}/refactor_plan.md` | Phase 0 | 全体 Agent | 结构化重构计划（目标、范围、预期改善） |
| `.ai/refactor/{refactor_id}/baseline_snapshot.md` | Phase 1 | Phase 3/5 | 重构前的测试基线 + 质量指标 |
| `.ai/refactor/{refactor_id}/changed_files.txt` | Phase 2 | Reviewer / Tester | 重构涉及的文件列表 |
| `.ai/refactor/{refactor_id}/behavior_test_results.md` | test-runner-agent | debugger-agent | 行为等价验证结果 |
| `.ai/refactor/{refactor_id}/review_feedback.md` | Reviewer | 修复参考 | 质量审计反馈 |
| `.ai/refactor/{refactor_id}/metrics_comparison.md` | Phase 5 | 用户 | 重构前后指标对比 |

---

## Execution Steps

**启动前必须动作**：
1. 检查参数完整性：至少需要重构目标描述或审查反馈文件
2. 若用户传入 `from=implement`，从 `.ai/implement/{sprint}_{module}/review_feedback.md` 读取 Improvements/Nitpicks 作为重构输入
3. 若 `fast=true`，向用户说明：「启动 refactor 重构流水线（**快速模式**），将跳过质量审计，依次经过：范围定义 → 基线快照 → 批量重构 → 行为验证。重构过程中**不会改变任何接口的外部行为**。」
4. 若 `fast` 未设置或为 `false`，向用户说明：「启动 refactor 重构流水线，将依次经过：范围定义 → 基线快照 → 批量重构 → 行为验证 → 质量审计。重构过程中**不会改变任何接口的外部行为**。」
5. **创建 Git 安全检查点**：

```bash
# 记录当前 HEAD，用于紧急回退
git rev-parse HEAD > .ai/refactor/{refactor_id}/git_checkpoint.txt
git stash list > .ai/refactor/{refactor_id}/stash_before.txt
```

---

### Phase 0: 范围定义与重构计划（Scope & Plan）

**执行者**: refactor-command 自身 + code-reviewer-agent（诊断扫描）

**目标**: 精确定义重构范围、预期改善目标、不可触碰边界

#### Step 0a: 重构目标识别

根据输入来源，自动分析重构范围：

**若来自审查反馈**：
```bash
# 从 review_feedback.md 提取 Improvements 和 Nitpicks
rg "### Improvements|### Nitpicks" .ai/implement/{sprint}_{module}/review_feedback.md -A 20
```

**若来自用户指令/技术债务**：启动 code-reviewer-agent 对目标范围做一次诊断扫描：

**Agent**: `code-reviewer-agent`（Sub-agent，只读诊断模式）

```
prompt: "请对以下目标范围执行诊断扫描，不输出 VERDICT，只输出改善建议：
目标：{用户描述的重构意图}
扫描范围：{指定目录或文件}

请输出以下维度的现状评估：
1. 圈复杂度（radon cc）— 列出 C 级及以上的函数
2. 重复代码（pylint duplicate-code）— 列出重复片段
3. 架构合规性（rg 扫描跨层引用）— 列出违规点
4. 命名一致性 — 列出不规范命名
输出格式为 Markdown 列表，每项包含文件路径、行号、问题描述。"
```

#### Step 0b: 生成结构化重构计划

```bash
mkdir -p .ai/refactor/{refactor_id}
```

```markdown
# Refactor Plan: {refactor_id}

## 重构目标
{一句话描述重构目标}

## 来源
- **类型**: 审查反馈 / 复杂度告警 / 重复代码 / 架构违规 / 技术债务 / 用户指令
- **关联 implement**: .ai/implement/{sprint}_{module}/（若有）

## 重构项清单

| ID | 类型 | 文件 | 位置 | 问题描述 | 重构方案 | 优先级 |
|----|------|------|------|----------|----------|--------|
| R-001 | extract | app/services/shot_service.py | L45-L78 | 分页逻辑重复出现 3 次 | 提取到 utils/pagination.py | 高 |
| R-002 | simplify | app/services/asset_service.py | L120-L180 | 圈复杂度 D 级(12) | 拆分为 3 个私有函数 | 高 |
| R-003 | restructure | app/dao/asset_dao.py | L30 | import app.services 违规 | 移除反向引用，参数化传入 | 中 |

## 不可触碰边界
- 所有 router 层的接口签名（path/method/request/response）不得改变
- 所有 schema 的字段定义不得改变
- 数据库模型（models/）不在本次重构范围
- 已有测试用例的断言逻辑不得修改

## 预期改善指标
- 圈复杂度：{函数名} 从 D(12) 降至 B(5)
- 重复代码：消除 {N} 处重复片段
- 架构合规：消除 {N} 个跨层引用违规

## 受影响文件
{列出所有可能被修改的文件}
```

将重构计划写入 `.ai/refactor/{refactor_id}/refactor_plan.md`。

**强制卡点**: 调用 `AskQuestion` —— 「重构计划已生成，请确认：(A) 确认范围，开始重构 (B) 调整范围 (C) 终止」

---

### Phase 1: 基线快照（Baseline Capture）

**设计思想**: 重构的前提是有一条绿色的测试基线。如果当前测试本身就有失败，必须先修复或标记排除，否则无法判断重构是否引入了行为变更。

#### Step 1a: 运行已有测试，建立基线

**Agent**: `test-runner-agent`（Sub-agent 方式启动）

```
prompt: "请运行以下测试文件，建立重构前基线快照。
测试范围：
1. tests/{sprint}/{module}_unit_test.py（若存在）
2. tests/{sprint}/{module}_api_test.py（若存在）
3. 其他与重构范围相关的测试文件

测试类型：基线快照（不做 VERDICT 判断，只记录结果）
将完整测试结果写入 .ai/refactor/{refactor_id}/baseline_snapshot.md
格式要求：每个用例的 ID、名称、状态（PASS/FAIL/SKIP）、耗时。"
```

#### Step 1b: 采集质量指标基线

```bash
cd /Users/geralt/PycharmProjects/creation-tool
source .venv/bin/activate

# 圈复杂度基线
pip show radon > /dev/null 2>&1 || pip install radon -q
radon cc {受影响文件列表} -s -j > .ai/refactor/{refactor_id}/cc_before.json

# 架构合规性基线（跨层引用计数）
rg "from app\.dao" app/routers/ -c --glob "*.py" 2>/dev/null || echo "0"
rg "from app\.services" app/dao/ -c --glob "*.py" 2>/dev/null || echo "0"
```

将指标写入 `baseline_snapshot.md` 的指标部分：

```markdown
## 质量指标基线

### 圈复杂度
| 函数 | 文件 | 复杂度 | 评级 |
|------|------|--------|------|
| transfer_assets | asset_service.py:120 | 12 | D |
| get_shot_list | shot_service.py:45 | 8 | C |

### 架构合规
- 跨层引用违规数：{N}
- 重复代码块数：{N}

### 测试基线
- 总用例：{N}
- 通过：{N}（基线绿色用例）
- 失败：{N}（基线已知失败，重构后不应增加）
- 跳过：{N}
```

**关键规则**：
- 基线中已有失败的用例标记为 `known_failures`，重构后这些用例的状态不得恶化
- 基线中通过的用例，重构后必须全部通过
- 若基线测试全部失败或无测试 → 调用 `AskQuestion`：「当前无有效测试基线，重构后无法验证行为等价性。请选择：(A) 先生成测试用例再重构 (B) 接受风险继续重构 (C) 终止」

---

### Phase 2: 批量重构执行（Refactoring）

**执行者**: refactor-command 自身（直接执行重构操作）

按 `refactor_plan.md` 中的优先级逐项执行重构。

#### 执行规则

**原子提交**：每个重构项（R-001、R-002...）单独完成后，立即记录改动文件，便于出问题时定位到具体重构项。

**执行顺序**：
1. `restructure`（分层修正）→ 先修正架构骨架
2. `move`（移动）→ 调整代码归属
3. `extract`（提取）→ 抽取公共逻辑
4. `deduplicate`（去重）→ 合并重复代码
5. `simplify`（简化）→ 降低复杂度
6. `rename`（重命名）→ 最后统一命名

> 顺序设计考量：先修正结构再动逻辑，最后改命名。如果先重命名再移动，会产生大量无意义的 diff。

**不可触碰的红线**（重构过程中持续检查）：
- 不得修改任何函数/方法的外部接口签名（参数名、参数类型、返回类型）
- 不得修改 schema 字段定义
- 不得修改 router 路径/方法
- 不得修改测试用例的断言逻辑
- 不得新增或删除 API 接口

**每个重构项执行后**：
```bash
# 记录改动文件
git diff --name-only >> .ai/refactor/{refactor_id}/changed_files.txt
```

**全部重构完成后**：
```bash
# 去重并排序
sort -u .ai/refactor/{refactor_id}/changed_files.txt -o .ai/refactor/{refactor_id}/changed_files.txt
```

---

### Phase 3: 行为等价验证（Behavior Preservation）

**设计思想**: 重构流水线的核心质量门控。必须证明重构前后行为完全一致。

#### Step 3a: 运行全量已有测试

**Agent**: `test-runner-agent`（Sub-agent 方式启动）

```
prompt: "请运行以下测试文件，验证重构后行为等价性。
测试范围（与 Phase 1 基线完全一致）：
1. tests/{sprint}/{module}_unit_test.py（若存在）
2. tests/{sprint}/{module}_api_test.py（若存在）
3. 其他与重构范围相关的测试文件

测试类型：行为等价验证（重构回归）
将测试结果写入 .ai/refactor/{refactor_id}/behavior_test_results.md
输出 VERDICT: PASS 或 FAIL。

PASS 条件（严格）：
- 基线中所有 PASS 的用例，重构后必须仍然 PASS
- 基线中已知 FAIL 的用例，重构后状态不得恶化（仍然 FAIL 可接受，变 PASS 更好）
- 不得出现新的失败用例"
```

**VERDICT 处理**:
- `VERDICT: PASS` → 进入 Step 3b
- `VERDICT: FAIL` → 进入修复循环

**修复循环**:
```
retry_count = 0
MAX_RETRY = 2

while VERDICT == FAIL and retry_count < MAX_RETRY:
    1. 启动 debugger-agent（Sub-agent）：
       prompt: "重构导致行为变更，请修复。
       测试结果：.ai/refactor/{refactor_id}/behavior_test_results.md
       重构计划：.ai/refactor/{refactor_id}/refactor_plan.md
       改动文件：$(cat .ai/refactor/{refactor_id}/changed_files.txt)

       核心约束：修复时只能调整重构实现方式，不得修改测试用例断言。
       如果发现测试断言本身有问题，报告后等待人类决策。"
    2. 修复完成后，重新执行 Step 3a（test-runner-agent）
    3. retry_count += 1

if retry_count >= MAX_RETRY and still FAIL:
    暂停流水线，调用 AskQuestion:
    「行为等价验证已循环 2 轮仍有失败用例，说明重构可能改变了外部行为。
    失败用例：[列出]
    请选择：(A) 人工修复 (B) 回退重构（git checkout） (C) 终止」

    若选择 (B)：
    git checkout $(cat .ai/refactor/{refactor_id}/git_checkpoint.txt) -- {受影响文件}
```

#### Step 3b: 补充覆盖验证（按需）

若重构涉及的代码路径没有被已有测试覆盖（Phase 1 基线中无相关用例），启动补充测试：

**Agent**: `api-test-agent`（Sub-agent 方式启动）

```
prompt: "请为重构后的代码补充回归测试。
重构计划：.ai/refactor/{refactor_id}/refactor_plan.md
改动文件：$(cat .ai/refactor/{refactor_id}/changed_files.txt)
关联 task_card（若有）：.ai/implement/{sprint}_{module}/task_card.json

重点覆盖：
1. 被提取的公共函数 — 验证入参出参一致性
2. 被简化的逻辑分支 — 验证各分支行为不变
3. 被移动的模块 — 验证调用链路不变

将测试追加到 tests/{sprint}/{module}_unit_test.py
标记为 @pytest.mark.refactor + @pytest.mark.unit"
```

补充测试后再执行一轮 test-runner-agent 验证。

---

### Phase 4: 质量审计（Quality Audit）

**跳过条件**: `fast=true` 时跳过整个 Phase 4，直接进入 Phase 5。跳过时在重构报告中标注「⚡ 快速模式 — 质量审计已跳过」。

**设计思想**: 行为不变已验证，现在评判重构是否真正**改善了**代码质量。审计失败不阻塞提交（因为行为正确），但会标记需关注项。

**Agent**: `code-reviewer-agent` + `security-reviewer-agent`（**并行**启动两个 Sub-agent）

**传入上下文（两者相同）**:
```
prompt: "请审查以下重构代码。这是一次结构优化重构（非新功能、非 Bug 修复），请重点关注：

1. 重构是否达成了预期改善目标（参见 refactor_plan.md）
2. 重构后的代码结构是否确实更清晰
3. 是否引入了不必要的抽象层级
4. 重命名/移动后的 import 是否全部更新
5. 是否存在遗漏的引用更新（其他文件仍引用旧路径/旧名称）

重构计划：.ai/refactor/{refactor_id}/refactor_plan.md
改动文件列表：$(cat .ai/refactor/{refactor_id}/changed_files.txt)
基线快照：.ai/refactor/{refactor_id}/baseline_snapshot.md

请输出 VERDICT: PASS 或 FAIL。
将审查结果写入 .ai/refactor/{refactor_id}/review_feedback.md。"
```

**VERDICT 处理**:
- 两个 Reviewer 都 PASS → 直接进入 Phase 5
- 任一 FAIL（存在 Critical 问题）→ 修复循环（最多 1 轮）

**修复循环**:
```
if any VERDICT == FAIL:
    启动 debugger-agent 修复 Critical 问题
    修复后重新执行 Phase 3（行为验证）+ Phase 4（质量审计）
    仅允许 1 轮修复。仍 FAIL 则标记问题，不阻塞但在报告中显著标注。
```

> 审计循环上限为 **1 轮**，比 fix 的 2 轮更严格。重构不应产生 Critical 问题，如果 1 轮修不好说明重构方案本身有问题。

---

### Phase 5: 重构报告 + 人类确认

#### Step 5a: 采集重构后质量指标

```bash
# 重构后圈复杂度
radon cc {受影响文件列表} -s -j > .ai/refactor/{refactor_id}/cc_after.json

# 重构后架构合规性
rg "from app\.dao" app/routers/ -c --glob "*.py" 2>/dev/null || echo "0"
rg "from app\.services" app/dao/ -c --glob "*.py" 2>/dev/null || echo "0"
```

#### Step 5b: 生成前后对比报告

```markdown
## refactor 重构流水线执行报告

### 模式
{若 fast=true 则显示：⚡ 快速模式（已跳过质量审计），否则不显示此行}

### 概览
| 阶段 | Agent | VERDICT | 重试次数 |
|------|-------|---------|----------|
| Phase 0: 范围定义 | code-reviewer (诊断) | ✅ 完成 | - |
| Phase 1: 基线快照 | test-runner | ✅ {N} 例基线 | - |
| Phase 2: 批量重构 | refactor-command | ✅ {M} 项完成 | - |
| Phase 3: 行为验证 | test-runner | PASS/FAIL | 0-2 |
| Phase 4: 质量审计 | code-reviewer + security-reviewer | PASS/FAIL/⚡SKIP | 0-1 |

### 重构项执行
| ID | 类型 | 文件 | 状态 |
|----|------|------|------|
| R-001 | extract | shot_service.py → utils/pagination.py | ✅ 完成 |
| R-002 | simplify | asset_service.py:120 | ✅ 完成 |
| R-003 | restructure | asset_dao.py:30 | ✅ 完成 |

### 改善指标对比
| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| 圈复杂度 max | D(12) | B(5) | ⬇️ 58% |
| C 级以上函数数 | 4 | 1 | ⬇️ 75% |
| 跨层引用违规 | 3 | 0 | ✅ 消除 |
| 重复代码块 | 5 | 1 | ⬇️ 80% |

### 行为等价验证
- 基线用例：{N} 个
- 重构后通过：{N} 个
- 行为等价：✅ 100%

### 改动文件
$(cat .ai/refactor/{refactor_id}/changed_files.txt)
```

**强制卡点**: 调用 `AskQuestion` —— 「重构流水线执行完毕，是否确认提交？(A) 确认，准备 commit (B) 需要调整 (C) 回退所有改动」

若选择 (A)，输出建议的 git commit message（中文）：
```
refactor: {重构目标一句话描述}

- 重构项：{N} 项（extract {X} / simplify {Y} / restructure {Z}）
- 圈复杂度改善：max D→B
- 行为验证：{N} 例全通过
```

若选择 (C)：
```bash
git checkout $(cat .ai/refactor/{refactor_id}/git_checkpoint.txt) -- $(cat .ai/refactor/{refactor_id}/changed_files.txt)
```

---

## 重构闭环流程总览

```
┌────────────────────────────────────────────────────────────┐
│                  refactor 结构优化流水线                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Phase 0                Phase 1             Phase 2        │
│  ┌──────────────┐       ┌─────────────┐    ┌───────────┐ │
│  │ 范围定义      │       │ 基线快照     │    │ 批量重构   │ │
│  │ code-reviewer │──────▶│ test-runner  │───▶│ 逐项执行   │ │
│  │ (诊断扫描)    │       │ radon/rg    │    │ 原子记录   │ │
│  └──────────────┘       └─────────────┘    └─────┬─────┘ │
│       │                                          │        │
│  ✋人类确认范围                                     ▼        │
│                                            Phase 3        │
│                                   ┌────────────────────┐  │
│                                   │ 行为等价验证         │  │
│                                   │ test-runner          │  │
│                                   │ (基线用例全量重跑)    │  │
│                                   └──────────┬─────────┘  │
│                                              │             │
│                              ┌───────────────┤             │
│                         FAIL │          PASS │             │
│                    (retry≤2) │               ▼             │
│                         ┌────▼──────┐  Phase 4            │
│                         │ debugger  │  ┌───────────────┐  │
│                         │ (不改测试) │  │ 质量审计       │  │
│                         └───────────┘  │ code-reviewer  │  │
│                                        │ security-rev   │  │
│                                        │ (并行)         │  │
│                                        └───────┬───────┘  │
│                                                │           │
│                                           VERDICT          │
│                                                │           │
│                                           Phase 5          │
│                                     ┌──────────────────┐  │
│                                     │ 前后指标对比      │  │
│                                     │ 重构报告          │  │
│                                     │ ✋人类确认/回退    │  │
│                                     └──────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

## 与 implement / fix 的关系

| 维度 | implement | fix | refactor |
|------|-----------|-----|----------|
| **目标** | 新增功能 | 修复 Bug | 改善结构 |
| **行为变更** | 是（目标） | 是（修正） | 否（硬约束） |
| **入口** | 需求描述 | Bug 报告 | 重构目标 / 审查反馈 |
| **核心 Agent** | planner→generator→reviewer→tester | debugger→reviewer→tester | reviewer(诊断)→tester(基线)→reviewer(审计) |
| **GAN 循环上限** | 3 轮 | 2 轮 | 行为验证 2 轮 + 审计 1 轮 |
| **质量门控顺序** | 审查 → 测试 | 审查 → 测试 | **测试 → 审查**（行为不变优先） |
| **文件契约目录** | `.ai/implement/` | `.ai/fix/` | `.ai/refactor/` |
| **安全回退** | 无 | 无 | Git 检查点 + 支持一键回退 |
| **互操作** | 审查反馈可触发 refactor | 可读取 implement 上下文 | 可读取 implement 的 task_card 和审查反馈 |

### 从 implement 衔接到 refactor

implement 流水线的 Phase 2 审查中，Code Reviewer 输出的 Improvements/Nitpicks 不阻塞 implement 流水线，但会积累为技术债。用户可批量启动 refactor：

```bash
/refactor from=implement sprint=sprint_2026_04 module=asset_transfer
```

此时 refactor 流水线自动：
1. 从 `.ai/implement/{sprint}_{module}/review_feedback.md` 提取非阻塞改进建议
2. 将 Improvements 转化为重构项清单
3. 读取 implement 的 task_card.json 获取模块上下文
4. 利用 implement 阶段已生成的测试文件作为基线

---

## Key Principles

- **行为不变是第一约束**：重构不改变外部行为，用测试基线严格验证。宁可多跑一轮测试，也不能放过一个行为变更。
- **测试先于审查**：与 implement/fix 不同，refactor 先验证行为不变（Phase 3），再审计结构改善（Phase 4）。
- **可度量改善**：每次重构必须产出前后指标对比，不接受"感觉更好了"的模糊改善。
- **Git 安全检查点**：重构前记录 HEAD，支持一键回退，降低心理负担。
- **原子记录**：每个重构项单独记录改动，出问题可精准定位到具体项。
- **批量有序**：多项重构按 restructure → move → extract → deduplicate → simplify → rename 的固定顺序执行，避免交叉冲突。
- **审计不强阻塞**：Phase 4 质量审计 FAIL 不阻断提交（行为已验证正确），但在报告中显著标注。

## Command Format

```
/refactor <重构目标描述>
```

或带参数：
```
/refactor <重构目标描述> [sprint=sprint_name] [module=module_name] [scope=app/services/] [fast=true]
```

或从 implement 流水线衔接：
```
/refactor from=implement [sprint=sprint_name] [module=module_name] [fast=true]
```

或从已有重构计划继续：
```
/refactor plan=.ai/refactor/{refactor_id}/refactor_plan.md [fast=true]
```

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| 重构目标描述 | 是（与 from/plan 三选一） | 自然语言描述重构意图 |
| `from` | 否 | 设为 `implement` 时从审查反馈中提取改进建议 |
| `plan` | 否 | 已有 refactor_plan.md 路径，跳过 Phase 0 |
| `sprint` | 否 | Sprint 名称 |
| `module` | 否 | 模块名 |
| `scope` | 否 | 限定重构扫描范围（目录或文件路径） |
| `fast` | 否 | 设为 `true` 时跳过 Phase 4 质量审计，节省约 20%-30% Token 消耗。行为等价验证（Phase 3）仍然执行，确保重构不破坏功能。适用于 rename/move 等低风险重构 |

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
