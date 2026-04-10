# modify-command

## Task
已有接口功能变更流水线：变更分析 → 代码修改 → GAN 对抗审查 → 单元测试，产出通过测试的可提交代码。不执行集成测试。

## Context

基于 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 三体架构：Analyzer → Generator → Evaluator。
- 定位：修改**已有**接口的行为（行为变更是目标），区别于 implement（新建）/ fix（修 Bug）/ refactor（行为不变）
- 与 implement 相比：无需完整需求设计（轻量 Phase 0），无需集成测试（仅单元测试）
- Context Reset：Agent 间通过文件契约传递状态，不依赖对话历史

### 适用场景

接口行为变更 | 字段增删改 | 业务规则调整 | 权限/鉴权变更 | 响应格式调整

> 接口**已存在**于代码库 → `/modify`；全新接口 → `/implement`

### File Contracts

**Path**: `.ai/modify/{branch}_{module}/`

| 文件 | 写入方 | 读取方 | 用途 |
|------|--------|--------|------|
| `change_card.json` | Phase 0 | 全体 | 变更上下文（现状、目标变更、影响范围） |
| `changed_files.txt` | Generator | Reviewer/Tester | 改动文件列表 |
| `review_feedback.md` | Reviewer | Debugger | 审查反馈 |
| `unit_test_results.md` | Test Runner | Debugger | 单元测试结果 |
| `tests/{branch}/{module}_unit_test.py` | unit-test-gen-agent | Test Runner | 持久化测试用例 |

### change_card.json 结构

```json
{
  "branch": "feature_user-points",
  "module": "asset_transfer",
  "status": "inbox | in_progress | done",
  "change_description": "变更需求一句话描述",
  "existing_interfaces": [
    { "method": "POST", "path": "/api/v1/assets/transfer", "file": "app/routers/asset_router.py", "current_behavior": "当前行为描述" }
  ],
  "target_changes": [
    { "interface": "/api/v1/assets/transfer", "change_type": "add_field | remove_field | modify_logic | modify_response | modify_validation", "description": "具体变更描述", "details": "变更细节" }
  ],
  "affected_files": ["app/routers/asset_router.py", "app/services/asset_service.py", "app/schemas/asset_schema.py"],
  "db_changes": [],
  "backward_compatibility": "兼容 | 不兼容 — 说明影响",
  "risk_level": "low | medium | high"
}
```

## Command Format

```
/modify <变更描述> [module=xxx] [fast=true]
/modify <变更描述> from=implement [module=xxx] [fast=true]
/modify change_card=.ai/modify/{branch}_{module}/change_card.json [fast=true]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| 变更描述 | 是（与 change_card 二选一） | 自然语言变更需求，触发 Phase 0 |
| `change_card` | 否 | 已有 change_card.json 路径，跳过 Phase 0 |
| `module` | 否 | 模块名，不传时自动推断 |
| `from` | 否 | `implement` 时从 task_card 读取接口上下文 |
| `fast` | 否 | `true` 跳过 Phase 2 GAN 审查（省 30-40% Token）。不建议在核心业务/安全鉴权使用 |

> branch 自动检测：`git rev-parse --abbrev-ref HEAD | tr '/' '_'`

## Pre-flight

1. 检查参数：至少需要变更描述或 `change_card` 路径
2. `BRANCH=$(git rev-parse --abbrev-ref HEAD | tr '/' '_')`，`module` 未传入时自动推断
3. 传入 `change_card=...` 且文件存在 → 跳过 Phase 0
4. `from=implement` → 从 `.ai/implement/{branch}_{module}/task_card.json` 读取接口上下文，导入 `existing_interfaces`，复用已有测试文件
5. `fast=true` → 告知「快速模式，跳过 GAN 审查：变更分析 → 代码修改 → 单元测试」
6. 默认 → 告知「完整模式：变更分析 → 代码修改 → GAN 审查 → 单元测试。关键节点暂停确认」

## Execution Steps

### Phase 0: 变更分析（Change Analysis）

**执行者**: modify-command 自身（轻量分析，无需 Sub-agent）
**Skip if**: `change_card` 参数指向已存在文件

```bash
mkdir -p .ai/modify/{branch}_{module}
```

**Step 0a — 定位接口**:
1. 在 `app/routers/` 搜索目标接口
2. 沿调用链追踪：router → service → dao → model/schema
3. 记录每层文件路径和关键函数（只读取变更相关代码，不做全局扫描）

**Step 0b — 现状快照**: 读取 router 层（路径/方法/Schema）→ service 层（业务逻辑/DAO 调用）→ schema 层（字段/校验）→ dao/model 层（表结构/查询）

**Step 0c — 影响分析**: 分析变更点、影响范围、向后兼容性、数据库变更、风险等级（low/medium/high）

**Step 0d**: 将分析结构化写入 `change_card.json`，status 设为 `inbox`

**Checkpoint**: AskQuestion —「变更分析已完成。涉及接口：[列出]，影响文件：[列出]，向后兼容：[兼容/不兼容]，DB 变更：[有/无]。是否进入代码修改阶段？」

### Phase 1: 代码修改（Generator）

**Agent**: `generator-agent` (Sub-agent)

**Prompt**:
> 请根据 .ai/modify/{branch}_{module}/change_card.json 修改已有接口代码。
> 核心要求：
> 1. 先读取现有代码理解当前实现后再修改（非从零实现）
> 2. 只修改 target_changes 指定的变更点，不做额外重构或优化
> 3. backward_compatibility 为「不兼容」时在代码注释标注 BREAKING CHANGE
> 4. 涉及 db_changes 时先执行数据库变更再改代码
> 完成后将文件列表写入 changed_files.txt，更新 status 为 in_progress。

**Done when**: `changed_files.txt` 已生成 + status → `in_progress` + 改动不超出 `affected_files` 范围
**On block**: 暂停流水线，展示阻塞原因

### Phase 2: GAN 对抗审查（Discriminator Round 1）

**Skip if**: `fast=true`（报告中标注「⚡ 快速模式 — GAN 审查已跳过」）

**Agents**: `code-reviewer-agent` + `security-reviewer-agent` (并行 Sub-agent)

**Prompt** (both):
> 请审查以下接口修改代码（已有接口变更，非新建/非 Bug 修复），重点关注：
> 1. 修改是否精准对应 target_changes，未引入无关变更
> 2. 是否可能产生副作用（破坏现有功能/其他调用方）
> 3. 向后兼容性评估是否准确
> 4. 参数校验和边界处理是否完备
> 5. Schema 变更与 Service/DAO 层是否一致
> change_card: .ai/modify/{branch}_{module}/change_card.json
> 改动文件：$(cat .ai/modify/{branch}_{module}/changed_files.txt)
> 输出 VERDICT: PASS 或 FAIL，写入 review_feedback.md。

**Verdict**: 两者都 PASS → Phase 3 | 任一 FAIL → Retry Loop
**Retry Loop** (MAX=2): 提取 Critical → `debugger-agent` 最小化修复 → 重新审查。超限 → AskQuestion「已循环 2 轮：[列出]。(A) 人工修复 (B) 忽略继续测试 (C) 终止」

### Phase 3: 单元测试（Discriminator Round 2）

#### Step 3a: 生成测试用例

**Agent**: `unit-test-gen-agent` (Sub-agent)

**Prompt**:
> 根据 .ai/modify/{branch}_{module}/change_card.json 和 changed_files.txt，连接本地 MySQL 查询真实数据生成 pytest 单元测试。
> 要求：
> 1. 「变更验证用例」— 验证新行为符合 target_changes
> 2. 「回归保护用例」— 验证未修改功能仍正常
> 3. backward_compatibility 为「不兼容」时增加旧参数格式异常处理用例
> 4. 识别改动面、推导数据依赖、查询真实样本
> 5. 保存到 tests/{branch}/{module}_unit_test.py（已存在则追加）+ tests/{branch}/{module}_unit_data.yaml
> 6. 标记 @pytest.mark.modify + @pytest.mark.unit
> 输出标准验证报告。

#### Step 3b: 执行测试

**Agent**: `test-runner-agent` (Sub-agent)

**Prompt**:
> 执行 tests/{branch}/{module}_unit_test.py，测试类型：单元测试（变更验证）。
> change_card: .ai/modify/{branch}_{module}/change_card.json。
> 结果写入 unit_test_results.md，输出 VERDICT。

**Verdict**: PASS → Phase 4 | FAIL → Retry Loop
**Retry Loop** (MAX=2): `debugger-agent` 根据 unit_test_results.md + change_card 最小化修复代码（不改测试）→ 重新执行 Step 3b。超限 → AskQuestion「已循环 2 轮：[列出]。(A) 人工修复 (B) 终止」

### Phase 4: 最终报告

输出报告，更新 change_card.json status → `done`：

```markdown
## 🔄 modify 变更流水线执行报告

### 模式
{若 fast=true：⚡ 快速模式（已跳过 GAN 审查）}

### 概览
| 阶段 | Agent | VERDICT | 重试 |
|------|-------|---------|------|
| Phase 0: 变更分析 | modify-command | ✅ | - |
| Phase 1: 代码修改 | generator-agent | ✅ | - |
| Phase 2: 代码审查 | code-reviewer + security-reviewer | PASS/FAIL/⚡SKIP | 0-2 |
| Phase 3: 单元测试 | unit-test-gen-agent + test-runner | PASS/FAIL | 0-2 |

### 变更信息
- 模块: {module} | 接口: {列表} | 向后兼容: {是/否} | 风险: {low/medium/high}

### 改动文件
$(cat .ai/modify/{branch}_{module}/changed_files.txt)

### 测试覆盖
- 单元测试：{N} 用例（变更验证 {N} + 回归保护 {N}），通过率 {X}%

### 审查摘要
- 代码审查：{Critical} Critical / {Improvement} Improvements | 安全审查：{结论}
```

**Checkpoint**: AskQuestion —「变更流水线完毕。(A) 确认 commit (B) 需要调整 (C) 终止」

选 (A) 输出 commit message：
```
modify: {变更描述一句话}
- 涉及接口：{接口列表}
- 涉及文件：{affected_files}
- 单元测试：{N} 例通过
- 向后兼容：{是/否}
```

## Key Principles

- **精准变更**: 只改 change_card 声明的变更点，不做额外重构/修 Bug/改风格
- **向后兼容优先**: 不兼容变更显式标注 BREAKING CHANGE，测试覆盖旧格式异常处理
- **GAN 分离**: Generator 不自评，独立 Reviewer 评判；Debugger 只修复已报告问题
- **轻量 Phase 0**: 接口定位 + 影响分析 + change_card 生成，无需完整需求设计
- **仅单元测试**: 不执行集成测试，基于真实数据的单元测试已足够覆盖改动面
- **2 轮上限**: GAN/测试修复各限 2 轮，超限升级人类（修改是局部变更，超限说明方案有问题）
- **Context Reset**: Agent 间通过文件契约通信，不继承对话历史
- **测试持久化**: 保存到 `tests/{branch}/`，新增用例追加不覆盖
- **歧义必须停下**: 遇到缺失/歧义暂停确认，禁止猜测

## Project Context

> 安装后根据实际项目填写，参考 `fast-harness/project-context.example.md`

**项目路径**: `{{PROJECT_ROOT}}`
**目录结构**: `{{PROJECT_STRUCTURE}}`
**本地数据库**: Host: {{DB_HOST}} | Port: {{DB_PORT}} | User: {{DB_USER}} | Pass: {{DB_PASS}} | DB: {{DB_NAME}}
**本地服务**: `{{DEV_SERVER_CMD}}`
**健康检查**: `{{HEALTH_CHECK_URL}}`
