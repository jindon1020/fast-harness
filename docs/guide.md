# 生产级项目 AI 编程开发套件使用说明

> 基于 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 三体架构，构建 Generator-Evaluator 分离的多 Agent 协作流水线。

---

## 目录

- [1. 为什么需要开发套件](#1-为什么需要开发套件)
- [2. fast-harness 组成](#2-fast-harness-组成)
- [3. 快速启动第一个任务](#3-快速启动第一个任务)
- [4. Token 消耗与成本估算](#4-token-消耗与成本估算)
- [5. 不适用场景](#5-不适用场景)
- [6. 架构全景](#6-架构全景)
- [7. 命令全解](#7-命令全解)
  - [7.1 /implement — 端到端需求实现流水线](#71-implement--端到端需求实现流水线)
  - [7.2 /modify — 已有接口功能变更流水线](#72-modify--已有接口功能变更流水线)
  - [7.3 /fix — Bug 修复闭环流水线](#73-fix--bug-修复闭环流水线)
  - [7.4 /refactor — 批量代码重构流水线](#74-refactor--批量代码重构流水线)
- [8. 实战场景](#8-实战场景)

---

## 1. 为什么需要开发套件

在生产级项目中使用 AI 编程，裸对话模式会遇到一系列结构性问题。本套件针对每个痛点提供系统性解决方案：

| 痛点 | 裸对话模式的问题 | 套件解决方案 |
|------|-----------------|-------------|
| **重复的提示词和模板** | 每次启动任务都要手写相似的 Prompt，格式不统一 | 四大 Command 一键启动标准化流水线，内置完整 Prompt 模板 |
| **人工复制大量辅助信息** | 需要手动粘贴代码片段、数据库结构、API 文档等上下文 | `task_card.json` / `change_card.json` 文件契约自动传递上下文，Agent 间结构化通信 |
| **AI 缺失关键信息时不主动询问** | AI 倾向于"猜测"缺失信息而非停下来问，导致实现偏离需求 | 每个 Agent 内置 `AskQuestion` 强制卡点，遇到歧义**必须停下询问**，禁止猜测 |
| **长流程复杂问题占用大量上下文** | 单对话处理需求→设计→编码→测试，超过 40 轮后一致性显著下降 | **Context Reset** — 每个 Sub-agent 从文件契约获取上下文，独立执行后返回 VERDICT，主流程不膨胀 |
| **缺乏有效的代码审查约束** | AI 生成代码后自我评估失灵，"看起来对"但实际有隐患 | **GAN 对抗审查** — Generator 不自评，由独立的 Code Reviewer（六维度）+ Security Reviewer 并行鉴别 |
| **长期 AI 编程导致架构偏移** | 持续迭代中逐渐打破分层架构约定，跨层引用、职责混乱 | 架构合规性自动检测 — Reviewer 使用 `rg` 命令扫描跨层引用，违反层级依赖规则直接标记 Critical |
| **从需求到交付容易遗漏功能点** | 需求→代码→测试之间缺少结构化追踪，容易漏实现、漏测试 | 端到端流水线 Phase 0→5 全覆盖，契约文件贯穿全程 |

### 核心设计理念

借鉴 GAN（生成对抗网络）的思想 — **将生成者与评判者分离**：

- **Generator**（代码生成 Agent）只负责写代码
- **Evaluator**（审查/测试 Agent）独立评判代码质量
- 两者通过 **VERDICT 协议**（二元信号 PASS/FAIL）通信
- 避免了单 Agent 的两个根本缺陷：**上下文窗口侵蚀**和**自我评估失灵**

---

## 2. fast-harness 组成

### 目录结构

```
.ether/
├── .claude-plugin/
│   └── plugin.json                     # 插件元数据
├── commands/                           # 纯编排，不含项目上下文
│   ├── implement-command.md            # 端到端需求实现流水线
│   ├── modify-command.md               # 已有接口功能变更流水线
│   ├── fix-command.md                  # Bug 修复闭环流水线
│   └── refactor-command.md             # 批量代码重构流水线
├── agents/                             # Agent 目录化（含扩展点）
│   ├── debugger-agent/
│   │   ├── debugger-agent.md           # 系统流程 + Extension Points
│   │   └── extensions/                 # 用户自定义扩展
│   ├── generator-agent/
│   │   ├── generator-agent.md
│   │   └── extensions/
│   ├── ... (其余 7 个 Agent 同理)
│   └── _extension-template.md          # 扩展文件模板
├── config/                             # 基础设施配置层
│   ├── infrastructure.json             # 中间件连接配置（用户填写）
│   └── infrastructure.example.json     # 配置模板
├── project-context.md                  # 集中式项目上下文（用户配置）
├── project-context.example.md          # 项目上下文模板
├── skills/
│   ├── db-connector/                   # 统一数据库连接（替代旧版 bastion-query）
│   ├── redis-connector/                # Redis 连接
│   ├── kafka-connector/                # Kafka 连接
│   ├── harness-meta-skill/             # 扩展点管理元技能
│   ├── k8s-monitor/                    # K8s 监控诊断（含 Loki/Prometheus）
│   ├── loki-log-keyword-search/        # Loki 日志关键词检索
│   ├── prometheus-metrics-query/       # Prometheus 指标查询
│   ├── xmind-test-extractor/           # XMind 测试用例提取
│   └── feishu-doc-reader/              # 飞书云文档提取（含下载直链）
└── configure.sh                        # 交互式项目配置脚本
```

### Commands — 四大流水线

| Command | 定位 | 说明 |
|---------|------|------|
| `/implement` | 新建 | 从需求出发，经设计、生成、GAN 对抗审查、单元测试、集成测试，产出可提交代码 |
| `/modify` | 变更 | 修改**已有**接口的行为（行为变更是目标），无需完整需求设计，不执行集成测试 |
| `/fix` | 修复 | 从 Bug 报告出发，经诊断修复、GAN 对抗审查、回归测试，产出通过全部测试的修复代码 |
| `/refactor` | 重构 | 改善内部结构，**行为不变**是硬约束，先验证行为等价再进行质量审计 |

> **选择指引**：全新接口 → `/implement`；已有接口行为变更 → `/modify`；修 Bug → `/fix`；内部结构优化 → `/refactor`

### Agents — 9 个专职 Agent

| Agent | 角色 | 模型 | 写权限 | 核心职责 | 产出 |
|-------|------|------|--------|----------|------|
| **requirement-design-agent** | Planner | opus | 是 | 将模糊需求转化为结构化 JSON 任务卡 | `task_card.json` + 设计文档 |
| **generator-agent** | Generator | sonnet | 是 | 按任务卡/变更卡编写实现代码 | 实现代码 + `changed_files.txt` |
| **code-reviewer-agent** | Code Reviewer | opus | 否 | 六维度代码质量审查 | VERDICT: PASS/FAIL |
| **security-reviewer-agent** | Security Reviewer | opus | 否 | 安全漏洞审查（与 Code Reviewer 并行） | VERDICT: PASS/FAIL |
| **unit-test-gen-agent** | 单元测试 | opus | 是 | 连接本地 DB 查真实数据，生成 pytest 用例 | `{module}_unit_test.py` + `_unit_data.yaml` |
| **integration-test-gen-agent** | 集成测试 | sonnet | 是 | 解析 xmind 脑图生成 pytest 用例 | `{module}_api_test.py` + `_test_data.yaml` |
| **test-runner-agent** | Executor | sonnet | 否 | 运行测试用例，报告结果 | VERDICT + 结果报告 |
| **debugger-agent** | Debugger | sonnet | 是 | 双路径：本地 FAIL 修复 / 线上问题排查 | 修复代码 + 排查报告 |
| **monitor-agent** | Monitor | - | 否 | K8s + Prometheus 监控查询 | 结构化状态报告 |

> **模型差异化原则**：审查类 Agent（Reviewer）使用 opus 深度推理确保质量；生成类 Agent（Generator/Tester/Executor）使用 sonnet 保证吞吐量。

### Skills — 运维能力底座

| 类型 | Skill | 用途 | 安全级别 |
|------|-------|------|----------|
| **Connector** | `db-connector` | 统一数据库连接（从 infrastructure.json 读取配置） | 只读 |
| **Connector** | `redis-connector` | Redis 连接与查询 | 只读 |
| **Connector** | `kafka-connector` | Kafka 消费与状态查询 | 只读 |
| **Meta** | `harness-meta-skill` | 扩展点管理（查看/创建/管理扩展） | - |
| 运维 | `k8s-monitor` | K8s + Loki + Prometheus 一体化监控诊断 | 只读 |
| 运维 | `loki-log-keyword-search` | Loki 日志关键词检索 | 只读 |
| 运维 | `prometheus-metrics-query` | ARMS Prometheus 监控指标查询 | 只读 |
| 协作 | `feishu-doc-reader` | 飞书文档全文提取（lark-cli）；支持 HTTP 导出/下载直链拉取后解析 | 依赖本机 lark 认证 |

所有运维 Skill 均为**只读操作**，通过 RBAC 权限 + 堡垒机隧道双重保障，不会误操作生产数据。`feishu-doc-reader` 为文档读取与本地下载，不写入飞书侧数据。

### 扩展点机制（v2.0 新增）

每个 Agent 定义了若干 Extension Points，用户可在 `agents/{agent}/extensions/` 下创建 `.md` 文件来注入自定义逻辑：

| Agent | 扩展点 | 说明 |
|-------|--------|------|
| debugger-agent | `@data-source`、`@diagnosis-strategy`、`@fix-validation` | 自定义数据源、诊断策略、修复验证 |
| generator-agent | `@pre-generation`、`@coding-convention`、`@code-template` | 生成前检查、编码规范、代码模板 |
| code-reviewer-agent | `@review-dimension`、`@project-rule` | 额外审查维度、项目审查规则 |
| security-reviewer-agent | `@security-rule` | 项目安全规则 |
| unit-test-gen-agent | `@test-data-source`、`@test-pattern` | 测试数据源、测试模式 |
| integration-test-gen-agent | `@test-context` | 测试环境配置 |
| test-runner-agent | `@pre-test`、`@post-test` | 测试前后处理 |
| monitor-agent | `@metric-source`、`@alert-rule` | 监控源、告警规则 |
| requirement-design-agent | `@design-convention` | 设计规范 |

**扩展文件格式**（YAML frontmatter + Markdown 内容）：

```yaml
---
extension-point: data-source
name: redis-cache-inspector
description: 调试时检查 Redis 缓存状态
priority: 10
requires-config: redis.local
---

## Redis 缓存检查策略
（具体的检查命令和分析步骤...）
```

使用 `harness-meta-skill` 可以交互式创建和管理扩展。

---

## 3. 快速启动第一个任务

### 最简启动

```
/implement 我需要实现一个团队积分查询功能
```

输入这一条命令后，流水线会自动经过以下阶段：

```
Phase 0  需求设计     → Planner Agent 与你多轮确认需求、API 设计、数据库设计
                        [人类确认] ✋ 确认设计方案后继续
Phase 1  代码生成     → Generator Agent 按 task_card.json 编码
Phase 2  GAN 对抗审查 → Code Reviewer + Security Reviewer 并行审查
                        PASS → 继续 | FAIL → 自动修复（最多 3 轮）
Phase 3  单元测试     → unit-test-gen-agent 生成 + test-runner 执行
                        PASS → 继续 | FAIL → 自动修复（最多 3 轮）
Phase 4  集成测试     → integration-test-gen-agent 生成 + test-runner 执行
                        [可选] 需要提供 xmind 测试用例文件
Phase 5  最终报告     → 汇总全部结果
                        [人类确认] ✋ 确认后准备 commit
```

### 带参数启动

```bash
# 指定模块名
/implement 我需要实现素材转移功能 module=asset_transfer

# 附带 xmind 测试用例（启用集成测试）
/implement 我需要实现素材转移功能 xmind=/path/to/asset_transfer.xmind

# 从已有 task_card 继续（跳过需求设计阶段）
/implement task_card=.ai/implement/feature_xxx_asset_transfer/task_card.json

# ⚡ 快速模式（跳过 GAN 对抗审查，节省 Token）
/implement 我需要实现素材转移功能 fast=true

# 修改已有接口（使用 /modify 而非 /implement）
/modify 素材转移接口新增 notify_owner 字段 module=asset_transfer
```

> **branch 自动检测**：所有命令通过 `git rev-parse --abbrev-ref HEAD | tr '/' '_'` 自动获取分支名，用于构建文件契约路径，无需手动指定。

### 你需要做什么

流水线会在以下节点暂停等待你确认：

| 卡点 | 位置 | 你需要做什么 |
|------|------|-------------|
| 需求/变更确认 | Phase 0 每个 Step 结尾 | 确认需求理解、技术方案、数据库设计、API 设计是否准确 |
| 设计完成 | Phase 0 结束 | 确认契约文件是否正确，是否进入编码阶段 |
| GAN 超限 | Phase 2 重试 3 轮仍 FAIL | 选择：人工修复 / 忽略继续 / 终止流水线 |
| 测试超限 | Phase 3/4 重试 3 轮仍 FAIL | 选择：人工修复 / 跳过 / 终止 |
| 最终确认 | 最终报告 | 确认提交，获得建议的 git commit message |

---

## 4. Token 消耗与成本估算

### 各流水线典型消耗

| 流水线 | 典型 Token 消耗 | 典型耗时 | 主要消耗环节 |
|--------|----------------|----------|-------------|
| `/implement`（完整 Phase 0-5） | 300k – 500k | 15 – 30 min | Phase 0 多轮确认 + Phase 2 GAN 循环 |
| `/implement`（从 task_card 继续） | 150k – 300k | 8 – 15 min | Phase 1 编码 + Phase 2 GAN 循环 |
| `/implement fast=true` | 100k – 200k | 6 – 12 min | 跳过 GAN 审查，仅编码 + 测试 |
| `/modify` | 100k – 200k | 5 – 12 min | Phase 0 变更分析 + Phase 2 GAN 循环 |
| `/modify fast=true` | 60k – 120k | 3 – 8 min | 跳过 GAN 审查，仅变更 + 单元测试 |
| `/fix` | 100k – 200k | 5 – 15 min | Phase 1 诊断 + Phase 3 回归 |
| `/fix fast=true` | 50k – 100k | 3 – 8 min | 跳过修复审查，仅诊断 + 回归 |
| `/refactor` | 200k – 400k | 10 – 20 min | Phase 0 诊断扫描 + Phase 2 批量执行 + Phase 3 全量回归 |
| `/refactor fast=true` | 150k – 300k | 8 – 15 min | 跳过质量审计，仅重构 + 行为验证 |

### 降低消耗的建议

1. **准备充分的需求文档**：清晰的 PRD/飞书文档可减少 Phase 0 的确认轮次
2. **从契约文件继续**：已有设计文档时用 `task_card=...` 或 `change_card=...` 跳过 Phase 0
3. **使用快速模式**：`fast=true` 跳过 GAN 对抗审查/质量审计，节省 30%-40% Token。适合原型验证、低风险改动
4. **小范围改动不走流水线**：单行修复、配置变更等直接编码（见下方"不适用场景"）
5. **指定 scope 缩小范围**：`/refactor scope=app/services/asset_service.py` 比全目录扫描省 Token

---

## 5. 不适用场景

流水线不是万能的，以下场景直接编码更高效：

### 不需要 /implement 或 /modify 的场景

| 场景 | 建议操作 |
|------|----------|
| 单行 bug 修复 / 纯 typo | 直接改 + 手动 `pytest` 验证 |
| 纯配置变更（YAML / 环境变量） | 直接改 + 确认配置生效 |
| 只改注释或文档 | 直接改 |
| 现有接口新增可选返回字段 | 直接改 + 补充单元测试（或用 `/modify fast=true`） |

### 不需要 /fix 的场景

| 场景 | 建议操作 |
|------|----------|
| 需求理解有误导致的"Bug" | 用 `/modify` 或 `/implement` 重新走需求对齐 |
| 第三方服务故障导致的报错 | 排查第三方服务，必要时加降级策略 |
| 环境配置问题（数据库连接/权限） | 检查部署配置和环境变量 |

### 不需要 /refactor 的场景

| 场景 | 建议操作 |
|------|----------|
| 涉及接口签名变更的"重构" | 用 `/modify` 作为接口变更 |
| 跨多个模块的大规模重写 | 拆分为多次小范围 refactor，每次验证后再继续 |
| 数据库表结构迁移 | 独立编写迁移方案 |

### 判断标准速查

```
改动文件 ≤ 2 个 && 无新增 API && 无数据库变更  → 直接编码
已有接口行为变更                              → /modify
全新 API 或涉及数据库变更                     → /implement
代码逻辑 Bug                                → /fix
内部结构优化（行为不变）                       → /refactor
```

---

## 6. 架构全景

### 6.1 流水线整体架构

```mermaid
flowchart TD
    UserInput["用户需求"]
    Planner["Phase 0: Planner(requirement-design-agent)"]
    TaskCard["task_card.json(Branch Contract)"]
    Generator["Phase 1: Generator(generator-agent)"]
    ChangedFiles["changed_files.txt"]

    subgraph GAN["Phase 2: GAN 对抗审查"]
        CR["Code Reviewer(六维度审查)"]
        SR["Security Reviewer(安全审查)"]
    end

    Debugger1["Debugger(最小化修复)"]

    subgraph UnitTest["Phase 3: 单元测试"]
        ApiTest["unit-test-gen-agent(真实数据驱动)"]
        Runner1["test-runner-agent"]
    end

    Debugger2["Debugger"]

    subgraph IntegrationTest["Phase 4: 集成测试"]
        TesterGen["integration-test-gen-agent(xmind 驱动)"]
        Runner2["test-runner-agent"]
    end

    Debugger3["Debugger"]
    Report["Phase 5: 最终报告"]
    HumanConfirm["人类确认提交"]

    UserInput --> Planner
    Planner --> TaskCard
    TaskCard --> Generator
    Generator --> ChangedFiles
    ChangedFiles --> CR
    ChangedFiles --> SR
    CR -->|"PASS"| UnitTest
    SR -->|"PASS"| UnitTest
    CR -->|"FAIL"| Debugger1
    SR -->|"FAIL"| Debugger1
    Debugger1 -->|"修复后重审"| CR
    ApiTest --> Runner1
    Runner1 -->|"PASS"| IntegrationTest
    Runner1 -->|"FAIL"| Debugger2
    Debugger2 -->|"修复后重跑"| Runner1
    TesterGen --> Runner2
    Runner2 -->|"PASS"| Report
    Runner2 -->|"FAIL"| Debugger3
    Debugger3 -->|"修复后重跑"| Runner2
    Report --> HumanConfirm
```

### 6.2 Agent 间通信：文件契约

Agent 之间不依赖对话历史传递上下文，而是通过**文件契约**实现 Context Reset：

| 契约文件 | 写入方 | 读取方 | 用途 |
|----------|--------|--------|------|
| `{contract_dir}/task_card.json` | Planner | 全体 Agent | 需求、API、数据库变更等完整上下文（implement 专用） |
| `{contract_dir}/change_card.json` | modify-command | 全体 Agent | 变更现状、目标变更、影响范围（modify 专用） |
| `{contract_dir}/changed_files.txt` | Generator | Reviewer / Tester | 本次改动的文件列表 |
| `{contract_dir}/review_feedback.md` | Reviewer | Debugger / Generator | 审查反馈（Critical/Improvements） |
| `{contract_dir}/unit_test_results.md` | Test Runner | Debugger | 单元测试执行结果 |
| `{contract_dir}/integration_test_results.md` | Test Runner | Debugger | 集成测试执行结果 |
| `tests/{branch}/` | unit-test-gen / integration-test-gen | Test Runner | 持久化测试用例（可复用） |

> **契约目录**按命令分：
> - implement → `.ai/implement/{branch}_{module}/`
> - modify → `.ai/modify/{branch}_{module}/`
> - fix → `.ai/fix/{branch}_{module}_{序号}/`
> - refactor → `.ai/refactor/{branch}_{scope}_{序号}/`

### 6.3 task_card.json（Branch Contract）

Planner 输出的结构化任务卡，是后续所有 Agent 的**唯一上下文来源**：

```json
{
  "branch": "feature_asset-transfer",
  "module": "asset_transfer",
  "feature": "素材转移功能",
  "background": "支持将素材从一个项目转移到另一个项目",
  "apis": [
    {
      "method": "POST",
      "path": "/drama-api/assets/transfer",
      "auth": "Bearer Token",
      "request": { "asset_ids": ["int"], "target_project_id": "int" },
      "response": { "code": 0, "data": { "transferred_count": "int" } }
    }
  ],
  "db_changes": ["asset 表新增 transfer_status 字段"],
  "affected_files": [
    "app/routers/asset_router.py",
    "app/services/asset_transfer_service.py",
    "app/schemas/asset_transfer.py"
  ],
  "test_cases": "xmind/feature_asset-transfer/asset_transfer.xmind",
  "design_doc": ".ai/design/feature_asset-transfer_asset_transfer.md",
  "impact_report": {
    "affected_modules": ["asset_service"],
    "regression_risk": "medium",
    "regression_scope": ["asset_router 现有接口"]
  },
  "status": "inbox"
}
```

**状态流转**：`inbox` → `in_progress` → `done`

### 6.4 VERDICT 协议

所有 Reviewer 和 Executor 输出必须以二元信号结尾：

```
VERDICT: PASS   ← 流水线继续
VERDICT: FAIL   ← 流水线阻断，进入修复循环
```

VERDICT 是质量门控的唯一依据，避免 Reviewer 输出模糊的"建议改进"导致主 Agent 无法判断是否继续。

### 6.5 GAN 对抗循环

本插件的核心质量机制借鉴了 **GAN（Generative Adversarial Network）** 的思想：Generator 生成代码，多层 Discriminator（审查→单元测试→集成测试）独立评判，VERDICT 协议作为 Pipeline Gate，debugger-agent 修复循环作为迭代过程。

与 Harness Pipeline 的对应关系：

| Harness 概念 | 本插件对应 | 作用 |
|---|---|---|
| Pipeline | implement / modify / fix / refactor 命令 | 端到端流水线 |
| Stage | Round 1/2/3（审查/单元测试/集成测试） | 质量关卡 |
| Approval Gate | VERDICT: PASS / FAIL | 二元门控信号 |
| Rollback on Failure | debugger-agent retry ≤ N | 失败自动修复 |
| Artifact Passing | changed_files.txt / review_feedback.md | Agent 间文件契约 |

![GAN 对抗质量提升机制](../images/2026-04-09-gan-adversarial-quality-pipeline.png)

### 6.6 测试分类

| 类型 | 别名 | 生成方式 | Agent | 产出 |
|------|------|----------|-------|------|
| 自发性测试 | 单元测试 | 根据接口变动自动查询本地 DB 真实数据生成 | `unit-test-gen-agent` | `tests/{branch}/{module}_unit_test.py` |
| 外部测试 | 集成测试 | 解析测试人员提供的 xmind 脑图生成 | `integration-test-gen-agent` | `tests/{branch}/{module}_api_test.py` |

---

## 7. 命令全解

### 7.1 /implement — 端到端需求实现流水线

**定位**：全新 API 开发，从需求描述到可提交代码的完整流程。

#### 命令格式

```bash
/implement <需求描述> [module=xxx] [xmind=/path/to/xxx.xmind] [fast=true]
/implement task_card=.ai/implement/{branch}_{module}/task_card.json [xmind=...] [fast=true]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| 需求描述 | 是（与 task_card 二选一） | 自然语言需求，触发 Phase 0 |
| `task_card` | 否 | 已有 task_card.json 路径，跳过 Phase 0 |
| `module` | 否 | 模块名，不传时自动推断 |
| `xmind` | 否 | xmind 测试用例路径，用于 Phase 4 集成测试 |
| `fast` | 否 | `true` 跳过 Phase 2 GAN 审查（省 30-40% Token）。不建议用于核心业务/安全鉴权 |

#### 流水线阶段

| 阶段 | Agent | 核心内容 | 卡点 |
|------|-------|----------|------|
| **Phase 0**: 需求设计 | `requirement-design-agent` | 8 步需求对齐（需求理解→技术方案→DB→API→业务逻辑→侵入性检查），输出 `task_card.json` | 每步 AskQuestion + Phase 0 结束确认 |
| **Phase 1**: 代码生成 | `generator-agent` | 按 task_card.json 分层编码（routers→services→schemas→dao），输出 `changed_files.txt` | 无 |
| **Phase 2**: GAN 对抗审查 | `code-reviewer` + `security-reviewer`（并行）| 六维度代码审查 + 五维度安全审查，任一 FAIL → debugger 修复重审（MAX=3） | 超限人类介入 |
| **Phase 3**: 单元测试 | `unit-test-gen-agent` + `test-runner` | 连接本地 DB 生成 pytest 用例（happy/edge/error path），执行并验证 | 超限人类介入 |
| **Phase 4**: 集成测试 | `integration-test-gen-agent` + `test-runner` | 解析 xmind 生成 tc-p1/p2/p3 用例，执行验证 | 无 xmind 时询问跳过 |
| **Phase 5**: 最终报告 | - | 汇总全部 VERDICT，输出改动文件、测试覆盖摘要 | 确认 commit |

**Code Reviewer 六维度**：架构合规性（`rg` 扫描跨层引用）、圈复杂度（`radon cc`）、重复代码、测试覆盖缺口、代码正确性、Harness 编程实践

**fast=true 效果**：跳过 Phase 2，路径变为：需求设计 → 代码生成 → 单元测试 → 集成测试

---

### 7.2 /modify — 已有接口功能变更流水线

**定位**：修改**已有**接口的行为（行为变更是目标）。比 `/implement` 更轻量：无需完整需求设计，不执行集成测试。

> 接口**已存在**于代码库 → `/modify`；全新接口 → `/implement`

#### 命令格式

```bash
/modify <变更描述> [module=xxx] [fast=true]
/modify <变更描述> from=implement [module=xxx] [fast=true]
/modify change_card=.ai/modify/{branch}_{module}/change_card.json [fast=true]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| 变更描述 | 是（与 change_card 二选一） | 自然语言变更需求，触发 Phase 0 |
| `change_card` | 否 | 已有 change_card.json 路径，跳过 Phase 0 |
| `from` | 否 | `implement` 时从 task_card 读取接口上下文，复用已有测试文件 |
| `module` | 否 | 模块名，不传时自动推断 |
| `fast` | 否 | `true` 跳过 Phase 2 GAN 审查（省 30-40% Token）。不建议用于核心业务/安全鉴权 |

#### change_card.json 结构

```json
{
  "branch": "feature_asset-transfer",
  "module": "asset_transfer",
  "status": "inbox",
  "change_description": "素材转移接口新增 notify_owner 通知字段",
  "existing_interfaces": [
    { "method": "POST", "path": "/drama-api/assets/transfer", "file": "app/routers/asset_router.py", "current_behavior": "批量转移素材，返回转移数量" }
  ],
  "target_changes": [
    { "interface": "/drama-api/assets/transfer", "change_type": "add_field", "description": "请求体新增 notify_owner 布尔字段", "details": "为 true 时转移完成后发送飞书消息给原拥有者" }
  ],
  "affected_files": ["app/routers/asset_router.py", "app/services/asset_transfer_service.py", "app/schemas/asset_transfer.py"],
  "db_changes": [],
  "backward_compatibility": "兼容 — notify_owner 默认 false",
  "risk_level": "low"
}
```

#### 流水线阶段

| 阶段 | 执行者 | 核心内容 | 卡点 |
|------|--------|----------|------|
| **Phase 0**: 变更分析 | modify-command | 定位已有接口 → 追踪调用链 → 影响分析 → 生成 `change_card.json` | AskQuestion 确认变更范围 |
| **Phase 1**: 代码修改 | `generator-agent` | 读取现有代码后精准修改，不做额外重构，不兼容变更标注 BREAKING CHANGE | 无 |
| **Phase 2**: GAN 对抗审查 | `code-reviewer` + `security-reviewer`（并行）| 重点：修改是否精准对应变更点、副作用评估、向后兼容性（MAX=2） | 超限人类介入 |
| **Phase 3**: 单元测试 | `unit-test-gen-agent` + `test-runner` | 变更验证用例 + 回归保护用例，不兼容变更增加旧格式异常处理用例（MAX=2） | 超限人类介入 |
| **Phase 4**: 最终报告 | - | 汇总 VERDICT，输出变更信息、兼容性、测试覆盖 | 确认 commit |

**与 implement 的主要差异**：

| 维度 | implement | modify |
|------|-----------|--------|
| Phase 0 | 完整需求设计（8 步） | 轻量变更分析（定位+影响） |
| 契约文件 | task_card.json | change_card.json |
| 集成测试 | ✅ Phase 4 | ❌ 不执行 |
| GAN/测试重试上限 | 3 轮 | 2 轮 |

---

### 7.3 /fix — Bug 修复闭环流水线

**定位**：修复已有代码的 Bug（行为修正），区别于 implement（新建）/ modify（行为变更）/ refactor（行为不变）。

#### 命令格式

```bash
/fix <Bug 描述> [module=xxx] [fast=true]
/fix from=implement [module=xxx] [fast=true]
/fix bug_report=.ai/fix/{fix_id}/bug_report.md [fast=true]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| Bug 描述 | 是（与 bug_report/from 二选一） | 自然语言 Bug 描述 |
| `from` | 否 | `implement` 时从 implement 失败结果衔接，自动读取失败上下文 |
| `bug_report` | 否 | 已有 bug_report.md 路径，跳过 Phase 0 |
| `module` | 否 | 模块名 |
| `fast` | 否 | `true` 跳过 Phase 2 修复审查（省 30-40% Token）。不建议用于线上异常/安全鉴权 |

#### Bug 来源分类

| 来源 | 输入特征 | Debugger 路径 |
|------|----------|---------------|
| 测试失败 | `VERDICT: FAIL` 或指向测试结果文件 | 路径 A（本地调试） |
| 审查反馈 | `review_feedback.md` 中 Critical 项 | 路径 A（本地调试） |
| 手动报告 | 其他自然语言描述 | 路径 A（本地调试） |
| **线上异常** | `request_id` / 环境名 / 错误描述 | **路径 B（先分析→人类确认→再修复）** |

#### 流水线阶段

| 阶段 | 执行者 | 核心内容 | 卡点 |
|------|--------|----------|------|
| **Phase 0**: 问题收集 | fix-command | 将多种来源标准化为 `bug_report.md`，信息不足时 AskQuestion 补充 | 信息不足时询问 |
| **Phase 1**: 诊断与修复 | `debugger-agent` | 路径 A/B 自动选择；路径 B（线上）根因分析后必须等人类确认才执行修复 | 路径 B 强制卡点 |
| **Phase 2**: 修复审查 | `code-reviewer` + `security-reviewer`（并行）| 重点：精准性、副作用、最小化原则（MAX=2） | 超限人类介入 |
| **Phase 3**: 回归测试 | `unit-test-gen-agent` + `test-runner` | 修复验证用例 + 回归保护用例，追加不覆盖；可选 Phase 3c 集成测试回归（MAX=2） | 超限人类介入 |
| **Phase 4**: 修复报告 | - | 汇总 fix_id、根因、修复文件、回归通过率 | 确认 commit |

![fix 修复闭环流水线](../images/2026-04-09-fix-repair-closed-loop-pipeline.png)

---

### 7.4 /refactor — 批量代码重构流水线

**定位**：改善内部结构，**行为不变是硬约束**。与 implement/modify/fix 的关键区别：**测试在审查之前**。

#### 命令格式

```bash
/refactor <重构目标描述> [module=xxx] [scope=app/services/] [fast=true]
/refactor from=implement [module=xxx] [fast=true]
/refactor plan=.ai/refactor/{refactor_id}/refactor_plan.md [fast=true]
```

| 参数 | 必填 | 说明 |
|------|------|------|
| 重构目标描述 | 是（与 from/plan 三选一） | 自然语言描述重构意图 |
| `from` | 否 | `implement` 时自动提取审查反馈中的 Improvements/Nitpicks |
| `plan` | 否 | 已有 refactor_plan.md 路径，跳过 Phase 0 |
| `module` | 否 | 模块名 |
| `scope` | 否 | 限定重构扫描范围（目录或文件） |
| `fast` | 否 | `true` 跳过 Phase 4 质量审计（省 20-30% Token），行为验证仍执行。适合 rename/move 等低风险重构 |

#### 重构类型与执行顺序

| 类型 | 说明 | 顺序 |
|------|------|------|
| `restructure` | 修复架构违规，恢复层级依赖方向 | 1 |
| `move` | 调整代码归属层级或模块 | 2 |
| `extract` | 提取大函数/重复逻辑为独立函数或模块 | 3 |
| `deduplicate` | 合并重复代码为公共组件 | 4 |
| `simplify` | 降低圈复杂度，消除冗余分支 | 5 |
| `rename` | 统一命名规范，消除歧义 | 6 |

> 先修正结构再动逻辑，最后改命名，避免交叉冲突产生无意义 diff

#### 流水线阶段

| 阶段 | 执行者 | 核心内容 | 卡点 |
|------|--------|----------|------|
| **Phase 0**: 范围定义 | `code-reviewer`（诊断扫描）| 四维诊断（复杂度/重复代码/架构合规/命名），生成 `refactor_plan.md`（含不可触碰边界） | AskQuestion 确认范围 |
| **Phase 1**: 基线快照 | `test-runner` | 运行已有测试记录 PASS/FAIL 基线 + 采集圈复杂度/跨层引用质量指标 | 无基线时询问风险 |
| **Phase 2**: 批量重构 | refactor-command | 按固定顺序逐项执行，原子记录每项改动；Git 检查点支持一键回退 | 无 |
| **Phase 3**: 行为等价验证 | `test-runner` + `debugger`（修复）+ `unit-test-gen`（补充）| 严格验证：基线 PASS → 重构后必须仍 PASS（MAX=2，超限可回退到 Git 检查点） | 超限时可选回退 |
| **Phase 4**: 质量审计 | `code-reviewer` + `security-reviewer`（并行）| 审计结构改善质量；FAIL 不强阻塞，但报告中显著标注（MAX=1） | 无 |
| **Phase 5**: 重构报告 | - | 前后指标对比（圈复杂度/跨层引用/重复代码/行为等价） | 确认 commit 或一键回退 |

![refactor 结构优化流水线](../images/2026-04-09-refactor-optimization-pipeline.png)

#### 四大命令对比

| 维度 | implement | modify | fix | refactor |
|------|-----------|--------|-----|----------|
| **目标** | 新增功能 | 变更行为 | 修复 Bug | 改善结构 |
| **行为变更** | 是（目标） | 是（目标） | 是（修正） | **否（硬约束）** |
| **Phase 0** | 完整需求设计 | 轻量变更分析 | 问题收集 | 范围定义+诊断 |
| **契约文件** | task_card.json | change_card.json | bug_report.md | refactor_plan.md |
| **集成测试** | ✅ | ❌ | ❌（可选回归） | ❌ |
| **质量门控顺序** | 审查 → 测试 | 审查 → 测试 | 审查 → 测试 | **测试 → 审查** |
| **GAN 循环上限** | 3 轮 | 2 轮 | 2 轮 | 行为 2 轮 + 审计 1 轮 |
| **fast 跳过** | Phase 2 GAN 审查 | Phase 2 GAN 审查 | Phase 2 修复审查 | Phase 4 质量审计 |
| **安全回退** | 无 | 无 | 无 | **Git 检查点 + 一键回退** |

---

## 8. 实战场景

### 场景一：新需求端到端实现

```bash
/implement 我需要实现素材转移功能，支持将素材从一个项目批量转移到另一个项目 module=asset_transfer
```

**典型流程**：Planner 逐步确认（边界条件、转移后原项目是否保留引用等）→ Generator 分层编码 → Code Reviewer FAIL（transfer_assets 未校验 target_project_id 存在性）→ Debugger 修复 → 重审 PASS → unit-test-gen-agent 连本地 MySQL 生成 pytest 用例 → test-runner PASS → 最终报告 + commit

---

### 场景二：已有接口功能变更

```bash
/modify 素材转移接口新增 notify_owner 字段，转移完成后通知原拥有者 module=asset_transfer
```

**典型流程**：modify-command 定位 `/drama-api/assets/transfer` 接口，追踪 router→service→schema 调用链，分析向后兼容性（notify_owner 默认 false，兼容）→ Generator 精准修改（不做额外重构）→ Reviewer PASS → 单元测试（变更验证用例 + 回归保护用例）PASS → commit

---

### 场景三：线上故障排查修复

```
线上 drama-dev 环境 creation-tool 服务报 500 错误
request_id: abc-123-def
接口：POST /drama-api/assets/transfer
```

**典型流程**：`/fix` 判断为线上异常（路径 B），切换 plan 模式 → `loki-log-keyword-search` Skill 拉取日志：`KeyError: 'transfer_status'` → `dev-mysql-bastion-query` Skill 比对 DB 确认根因（旧数据 transfer_status 为 NULL）→ 根因分析报告输出 → **等待用户确认** → Debugger 最小化修复（增加 None 防御）→ 本地验证 → commit

---

### 场景四：implement 测试失败后衔接 fix

implement 流水线单元测试 3 轮自动修复仍有顽固失败用例时，启动独立修复闭环：

```bash
/fix from=implement module=asset_transfer
```

fix 自动读取 `.ai/implement/{branch}_asset_transfer/unit_test_results.md` 提取失败用例，生成 `bug_report.md`，Debugger 定位根因（空列表未校验）→ 修复审查 PASS → 回归测试全通过 → commit

---

### 场景五：implement 完成后消化审查改进建议

implement 流水线完成后，Code Reviewer 留下了 5 个 Improvements，使用 `/refactor` 批量消化：

```bash
/refactor from=implement module=asset_transfer
```

自动从审查反馈提取改进建议 → 用户确认重构范围 → 建立测试基线（6 例全 PASS）→ 按顺序执行：R-003 restructure（消除反向引用）→ R-001 extract（提取分页逻辑）→ R-005 deduplicate（合并软删除过滤）→ R-002 simplify（拆解嵌套 if）→ R-004 rename → 行为等价验证（6/6 PASS）→ 质量审计 PASS（圈复杂度 C→A，跨层引用 1→0）→ commit

---

### 场景六：智能运维探测生产潜在问题

通过飞书群聊 @机器人，实时查询生产环境状态：

```
@智能运维机器人 查下 drama-prod 的 creation-tool 服务状态
@智能运维机器人 查询最近 30 分钟的 5xx 错误率
```

Monitor Agent 调用 `k8s-monitor` + `prometheus-metrics-query` Skill，返回结构化报告。所有操作均为 RBAC 只读，不会误操作生产数据。

| 常用触发词 | 场景 |
|-----------|------|
| `查下 drama-prod 的 Pod 状态` | Pod 运行状态、CPU/内存 |
| `查询最近 30 分钟的错误率` | 5xx 错误率按接口分布 |
| `P95 延迟是多少` | 接口延迟分布 |
| `查下哪个 Pod 重启过` | Pod 重启记录 |
| `查看最近的 K8s 事件` | K8s 事件日志 |

---

## 附录

### A. 项目上下文

> 以下为示例值，安装后请根据实际项目修改各 command 文件末尾的 `## Project Context` 部分。

```
项目路径: /path/to/your/project
API 前缀: /api
响应格式: {"code": 0, "data": ..., "message": "success"}
错误处理: BizException（全局 handler 捕获）
日志框架: loguru（带 request_id 上下文）
数据库: PostgreSQL via SQLModel
缓存: Redis
消息队列: Kafka（可选）
```

### B. 分层架构约定

```
routers/    ← 入口层，只做请求解析与响应封装，通过 Depends() 调用 service
    ↓
services/   ← 业务逻辑层，编排 DAO/Gateway，不涉及 HTTP 细节
    ↓
dao/        ← 数据访问层，只做 CRUD，无业务逻辑
models/     ← SQLModel DB 模型，纯数据定义
schemas/    ← Pydantic 请求/响应契约，纯数据定义
gateways/   ← 外部服务调用，封装 HTTP/RPC
config/     ← 配置读取
utils/      ← 纯工具函数，无业务状态
```

**依赖方向：只允许向下引用，严禁向上/跨层引用。** Code Reviewer 会自动检测违反此规则的代码。

### C. 文件索引

| 组件 | 文件位置 | 说明 |
|------|----------|------|
| implement-command | `plugin/commands/implement-command.md` | 需求实现流水线 |
| modify-command | `plugin/commands/modify-command.md` | 接口变更流水线 |
| fix-command | `plugin/commands/fix-command.md` | Bug 修复闭环流水线 |
| refactor-command | `plugin/commands/refactor-command.md` | 批量代码重构流水线 |
| requirement-design-agent | `plugin/agents/requirement-design-agent.md` | Planner |
| generator-agent | `plugin/agents/generator-agent.md` | Generator |
| code-reviewer-agent | `plugin/agents/code-reviewer-agent.md` | Code Reviewer |
| security-reviewer-agent | `plugin/agents/security-reviewer-agent.md` | Security Reviewer |
| unit-test-gen-agent | `plugin/agents/unit-test-gen-agent.md` | 单元测试生成 |
| integration-test-gen-agent | `plugin/agents/integration-test-gen-agent.md` | 集成测试生成 |
| test-runner-agent | `plugin/agents/test-runner-agent.md` | 测试执行 |
| debugger-agent | `plugin/agents/debugger-agent.md` | 调试修复 |
| monitor-agent | `plugin/agents/monitor-agent.md` | K8s 监控 |
| dev-mysql-bastion-query | `plugin/skills/dev-mysql-bastion-query/` | MySQL 查询 |
| k8s-monitor | `plugin/skills/k8s-monitor/` | K8s 监控诊断 |
| loki-log-keyword-search | `plugin/skills/loki-log-keyword-search/` | 日志检索 |
| prometheus-metrics-query | `plugin/skills/prometheus-metrics-query/` | 指标查询 |
| feishu-doc-reader | `plugin/skills/feishu-doc-reader/` | 飞书文档提取与下载直链 |
