# fast-harness

> 基于 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 三体架构的 Generator-Evaluator 多 Agent 协作开发套件。

将 GAN（生成对抗网络）思想引入 AI 编程：**生成者与评判者分离**，通过多 Agent 流水线实现生产级代码质量控制。

---

## 解决什么问题

在生产级项目中使用 AI 编程，裸对话模式存在以下结构性问题：

| 痛点 | 裸对话模式 | fast-harness 方案 |
|------|-----------|-------------------|
| 重复的 Prompt 模板 | 每次手写相似提示词 | `/implement` 一键启动标准化流水线 |
| 手动拼凑上下文 | 粘贴代码片段、DB 结构、API 文档 | `task_card.json` 文件契约自动传递 |
| AI 不了解项目规范 | 每次重新解释架构约定 | **Code Wiki** — 一次生成，全流水线感知 |
| AI 缺信息时猜测 | 倾向猜测而非停下来问 | 每个 Agent 内置 `AskQuestion` 强制卡点 |
| 长流程上下文膨胀 | 40+ 轮工具调用后一致性下降 | **Context Reset** — Sub-agent 从文件契约获取上下文 |
| 代码自我评估失灵 | "看起来对"但有隐患 | **GAN 对抗审查** — Generator 不自评，独立 Reviewer 鉴别 |
| 架构逐渐偏移 | 持续迭代中打破分层约定 | wiki 驱动的架构规则检查，违规直接标记 Critical |
| 需求到交付容易遗漏 | 缺少结构化追踪 | Phase 0→5 全覆盖，每个 API 都有测试用例 |

## 核心设计

```
Generator (生成)          Discriminator (鉴别)
┌─────────────┐          ┌─────────────────────────┐
│ generator-  │ ──────►  │ Round 1: 代码审查         │
│ agent       │          │   code-reviewer (六维度)   │
│             │          │   security-reviewer        │
└──────▲──────┘          ├─────────────────────────┤
       │                 │ Round 2: 单元测试         │
       │  FAIL+feedback  │   unit-test-gen-agent      │
       │◄────────────── │   test-runner              │
       │                 ├─────────────────────────┤
  debugger-agent         │ Round 3: 集成测试         │
  (最小化修复)            │   integration-test-gen     │
                         │   test-runner              │
                         └─────────────────────────┘
                           VERDICT: PASS / FAIL
```

**所有 Agent 共享同一份 Code Wiki**，统一理解项目架构、接口规范和编码约定。

## 支持平台

| 平台 | 版本要求 | 状态 |
|------|---------|------|
| **Cursor** | Agent Mode | ✅ 完全支持 |
| **Claude Code** | Claude Code with Plugin | ✅ 完全支持 |

## 一键安装

### 方式一：curl 远程安装（推荐）

```bash
# 进入你的项目目录
cd /path/to/your/project

# 自动检测平台，安装到 .ether/ 目录
curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash

# 指定平台
curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --platform cursor
curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --platform claude

# 自定义插件目录名
curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --dir my-ai-plugin
```

> **提示**：使用 jsDelivr CDN（`cdn.jsdelivr.net`）而非 `raw.githubusercontent.com`，可避免 GitHub 原始文件缓存导致拿到旧版本的问题。

### 方式二：克隆后本地安装

```bash
git clone https://github.com/jindon1020/fast-harness.git /tmp/fast-harness
cd /path/to/your/project
bash /tmp/fast-harness/install.sh
rm -rf /tmp/fast-harness
```

### 安装后配置

```bash
# 第一步：交互式配置项目上下文和基础设施（数据库、Redis、Kafka 等）
.ether/configure.sh

# 第二步：初始化 Code Wiki（扫描代码库生成结构化知识，激活全 Agent wiki 感知）
/init
```

### 安全保证

安装脚本遵循以下原则：

- **不覆盖已有文件** — 所有文件操作使用 safe_copy，已存在的文件会跳过并提示
- **不修改已有配置** — AGENTS.md 采用追加模式，不覆盖已有内容
- **不泄露敏感信息** — skills 目录下的密钥文件均为 `.example` 模板
- **可完全回退** — 删除插件目录和对应的 rules 文件即可完全卸载

### 更新到最新版本

```bash
cd /path/to/your/project

# 从远程拉取最新版本（覆盖插件文件）
curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --force

# 指定平台更新
curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --force --platform cursor
curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --force --platform claude
```

`--force` 模式会**覆盖更新**以下内容：

- `.ether/` 目录下所有 commands、agents、skills 规范文件及文档
- `.cursor/rules/ether.mdc` / `.claude/rules/ether.mdc`
- `.cursor/agents/`、`.cursor/skills/`、`.cursor/commands/` 下的插件文件

**始终保留，不会被覆盖**：

- `.local/` — 密钥、kubeconfig、bastion 配置
- `.ai/` — 流水线运行产物（task_card、审查报告、测试结果等）
- `.wiki/` — Code Wiki（项目知识资产，由 `/init` 生成）
- `.ether/project-context.md` — 项目上下文（如已自定义）
- `.ether/config/infrastructure.json` — 基础设施配置（如已自定义）
- `AGENTS.md` — 不重复追加 fast-harness 章节

> 大版本更新后建议重新运行 `.ether/configure.sh`，检查是否有新配置项需要填写。

## 目录结构

安装后，你的项目中会新增以下文件：

```
your-project/
├── AGENTS.md                          # AI 认知入口（追加 fast-harness 章节）
├── .wiki/                             # Code Wiki（/init 生成，建议提交 git）
│   ├── 00-overview.md                 # 系统概览（技术栈、模块图、部署）
│   ├── 01-modules.md                  # 各模块详细说明
│   ├── 02-interfaces.md               # 接口契约（响应格式、依赖注入、权限）
│   ├── 03-data-flow.md                # 请求生命周期与数据流
│   ├── 04-shared-code.md              # 公共工具代码
│   ├── 05-patterns.md                 # 架构模式与编码规范
│   └── MANIFEST.json                  # Section 鲜度追踪（source_hash + stale）
├── .cursor/
│   ├── rules/ether.mdc                # Cursor 规则（仅 Cursor 平台）
│   ├── agents/                        # Cursor 自动识别的 Sub-agent（9 个）
│   ├── skills/                        # Cursor 自动识别的 Skill
│   └── commands/                      # Cursor 斜杠命令（/init /implement /modify /fix /refactor）
├── .claude/rules/ether.mdc            # Claude 规则（仅 Claude 平台）
└── .ether/                            # 插件原文目录（规范详细版）
    ├── .claude-plugin/
    │   └── plugin.json                # Claude Code 插件清单
    ├── commands/
    │   ├── init-command.md            # Code Wiki 初始化
    │   ├── implement-command.md       # 需求实现流水线规范
    │   ├── modify-command.md          # 接口功能变更流水线规范
    │   ├── fix-command.md             # Bug 修复流水线规范
    │   └── refactor-command.md        # 代码重构流水线规范
    ├── agents/                        # Agent 目录化（含 wiki 扩展点）
    │   ├── generator-agent/
    │   │   ├── generator-agent.md
    │   │   └── extensions/
    │   │       ├── wiki-pre-generation.md      # @pre-generation: 加载模块上下文
    │   │       └── wiki-coding-convention.md   # @coding-convention: 编码规范对齐
    │   ├── requirement-design-agent/
    │   │   ├── requirement-design-agent.md
    │   │   └── extensions/
    │   │       └── wiki-design-convention.md   # @design-convention: 接口设计基准
    │   ├── code-reviewer-agent/
    │   │   ├── code-reviewer-agent.md
    │   │   └── extensions/
    │   │       └── wiki-project-rule.md        # @project-rule: 项目架构规则
    │   ├── security-reviewer-agent/
    │   │   ├── security-reviewer-agent.md
    │   │   └── extensions/
    │   │       └── wiki-security-rule.md       # @security-rule: 鉴权模式校验
    │   ├── debugger-agent/
    │   │   ├── debugger-agent.md
    │   │   └── extensions/
    │   │       └── wiki-diagnosis-strategy.md  # @diagnosis-strategy: 请求链路追踪
    │   ├── unit-test-gen-agent/
    │   │   ├── unit-test-gen-agent.md
    │   │   └── extensions/
    │   │       └── wiki-test-pattern.md        # @test-pattern: 断言规范对齐
    │   ├── integration-test-gen-agent/
    │   │   ├── integration-test-gen-agent.md
    │   │   └── extensions/
    │   │       └── wiki-test-context.md        # @test-context: 响应格式与流程覆盖
    │   ├── test-runner-agent/
    │   ├── monitor-agent/
    │   └── _extension-template.md              # 自定义扩展文件模板
    ├── config/
    │   ├── infrastructure.json        # 中间件连接配置（MySQL/Redis/Kafka）
    │   └── infrastructure.example.json
    ├── project-context.md             # 集中式项目上下文
    ├── skills/                        # 系统级 Skill
    │   ├── db-connector/
    │   ├── redis-connector/
    │   ├── kafka-connector/
    │   ├── harness-meta-skill/
    │   ├── k8s-monitor/
    │   ├── loki-log-keyword-search/
    │   ├── prometheus-metrics-query/
    │   ├── xmind-test-extractor/
    │   └── feishu-doc-reader/
    ├── configure.sh                   # 交互式项目配置脚本
    └── docs/
        └── guide.md                   # 完整使用说明
```

## 快速开始

### Step 1：配置项目上下文

```bash
.ether/configure.sh
```

交互式填写项目名称、技术栈、数据库连接等，生成 `project-context.md` 和 `infrastructure.json`。

### Step 2：初始化 Code Wiki

```
/init
```

扫描整个代码库，生成 `.wiki/` 下的 7 个结构化知识文档。完成后，所有 Agent 自动感知项目架构、编码规范和接口契约，无需在每次任务中重新描述。

### Step 3：启动第一个任务

```
/implement 我需要实现一个用户积分查询功能
```

流水线自动经过以下阶段：

```
Phase 0  需求设计     → Planner 与你多轮确认需求、API、数据库设计
                        ✋ 人类确认设计方案
Phase 1  代码生成     → Generator 按 task_card.json 编码（wiki 感知规范）
Phase 2  GAN 对抗审查 → Code Reviewer + Security Reviewer 并行（wiki 驱动规则）
                        PASS → 继续 | FAIL → 自动修复（≤3 轮）
Phase 3  单元测试     → 连接本地 DB 查真实数据生成 + 执行（wiki 规范断言）
                        PASS → 继续 | FAIL → 自动修复（≤3 轮）
Phase 4  集成测试     → 解析 xmind 脑图生成 + 执行（可选）
Phase 5  最终报告     → 汇总结果 ✋ 确认提交
```

### 六大命令

| 命令 | 用途 | 示例 |
|------|------|------|
| `/init` | Code Wiki 初始化 / 刷新 | `/init` 或 `/init force`（重大重构后刷新） |
| `/implement` | 新功能开发（全流水线） | `/implement 实现素材转移功能` |
| `/modify` | 已有接口功能变更 | `/modify 积分查询接口增加时间范围筛选` |
| `/fix` | Bug 修复 | `/fix 线上报 500 request_id=abc-123` |
| `/refactor` | 代码重构 | `/refactor 把分页逻辑抽取到 utils` |
| `/test` | 提交前快速单元测试 | `/test` 或 `/test scope=staged` |

`/implement`、`/modify`、`/fix`、`/refactor` 均支持 `mode=fast` 快速模式（跳过 GAN 审查，节省 30-40% Token）。

> **`/test` 适用场景**：手动改了一个小逻辑、或纯对话 AI 修改后未经流水线，提交前想快速验证改动——无需 task_card，直接从 git diff 识别改动面，生成并执行单元测试。

### 9 个专职 Agent

| Agent | 角色 | 核心职责 | Wiki 注入 |
|-------|------|----------|-----------|
| requirement-design-agent | Planner | 需求 → 结构化 task_card.json | `@design-convention` — 接口设计基准对齐 |
| generator-agent | Generator | 按任务卡编写实现代码 | `@pre-generation` + `@coding-convention` |
| code-reviewer-agent | Code Reviewer | 六维度代码质量审查 | `@project-rule` — 项目架构规则驱动 |
| security-reviewer-agent | Security Reviewer | 安全漏洞审查 | `@security-rule` — 鉴权模式校验 |
| unit-test-gen-agent | 单元测试 | 连接本地 DB 真实数据驱动测试 | `@test-pattern` — 断言格式规范 |
| integration-test-gen-agent | 集成测试 | 解析 xmind 脑图生成测试 | `@test-context` — 响应格式与流程覆盖 |
| test-runner-agent | Executor | 运行 pytest 输出 VERDICT | — |
| debugger-agent | Debugger | 本地修复 / 线上排查双路径 | `@diagnosis-strategy` — 请求链路追踪 |
| monitor-agent | Monitor | K8s + Prometheus 只读监控 | — |

## Code Wiki 系统

### 为什么需要 Code Wiki

传统 AI 编程中，每次任务 Agent 都需要"从零理解"项目��fast-harness 通过 `/init` 一次性将代码库的知识结构化为 wiki，**所有 Agent 共享这份知识**：

```
/init 扫描代码库
       ↓
.wiki/
├── 00-overview.md    → generator 了解模块边界
├── 01-modules.md     → generator / debugger 按模块定位
├── 02-interfaces.md  → requirement-design / code-reviewer / 两个测试 Agent
├── 03-data-flow.md   → debugger 沿链路追踪根因 / integration-test 覆盖流程
├── 04-shared-code.md → generator 复用公共工具
├── 05-patterns.md    → generator / code-reviewer / security-reviewer
└── MANIFEST.json     → /implement Pre-flight 检测 stale section，过期自动告警
```

### Wiki 鲜度管理

`MANIFEST.json` 记录每个 section 的源文件 hash。代码变更后：

- `/implement` 启动时自动检测 stale sections 并告警
- 积累较多变更后运行 `/init force` 全量刷新
- `.wiki/` 建议提交 git，作为项目知识资产持续维护

### Wiki 注入方式

扩展文件随插件安装自动到位，无需手动配置。Agent 启动时通过 Extension Loading Protocol 读取扩展文件，按指令动态加载对应 wiki section：

```
安装插件 → 扩展文件自动复制到 .ether/agents/*/extensions/
运行 /init → .wiki/ 内容生成
Agent 启动 → 读取扩展文件 → 按指令读取对应 .wiki/*.md → wiki 知识进入 context
```

## 扩展点机制

fast-harness 引入 Spring 式扩展点架构，用户可在不修改框架代码的前提下注入自定义逻辑：

```
框架层（不可修改）           用户扩展层（自由定制）
┌─────────────────┐       ┌──────────────────────────────┐
│ Commands        │       │ project-context.md            │
│ (纯编排调度)      │       │ config/infrastructure.json   │
├─────────────────┤       ├──────────────────────────────┤
│ Agents          │◄─────│ extensions/*.md               │
│ (系统流程 +      │       │  ├── wiki-*.md（内置 wiki 扩展）│
│  Extension Points)│      │  └── 自定义扩展（任意添加）    │
├─────────────────┤       └──────────────────���───────────┘
│ Connector Skills │
│ (db/redis/kafka) │
└─────────────────┘
```

### 内置扩展点（wiki 驱动，开箱即有）

| Agent | 扩展点 | 扩展文件 | wiki 来源 |
|-------|--------|---------|-----------|
| generator-agent | `@pre-generation` | wiki-pre-generation.md | `00/01/03-*.md` |
| generator-agent | `@coding-convention` | wiki-coding-convention.md | `05/02-*.md` |
| requirement-design-agent | `@design-convention` | wiki-design-convention.md | `00/01/02-*.md` |
| code-reviewer-agent | `@project-rule` | wiki-project-rule.md | `05/02-*.md` |
| security-reviewer-agent | `@security-rule` | wiki-security-rule.md | `05-patterns.md` |
| debugger-agent | `@diagnosis-strategy` | wiki-diagnosis-strategy.md | `01/03-*.md` |
| unit-test-gen-agent | `@test-pattern` | wiki-test-pattern.md | `02-interfaces.md` |
| integration-test-gen-agent | `@test-context` | wiki-test-context.md | `02/03-*.md` |

### 添加自定义扩展

1. 在 `.ether/agents/{agent}/extensions/` 下创建 `.md` 文件
2. 用 YAML frontmatter 声明挂载的扩展点和优先级
3. Agent 启动时自动扫描并加载

```markdown
---
extension-point: coding-convention
priority: 20
description: 项目特定的日志格式规范
---

所有日志必须包含 request_id 字段，使用 loguru structured JSON 格式...
```

使用 `harness-meta-skill` 可交互式管理所有扩展点：「帮我查看所有可用扩展点」。

## Token 消耗估算

| 流水线 | 典型消耗 | 典型耗时 |
|--------|---------|----------|
| `/init` | 100k – 300k | 5 – 15 min |
| `/implement`（完整） | 300k – 500k | 15 – 30 min |
| `/implement mode=fast` | 100k – 200k | 6 – 12 min |
| `/modify` | 150k – 300k | 8 – 18 min |
| `/fix` | 100k – 200k | 5 – 15 min |
| `/refactor` | 200k ��� 400k | 10 – 20 min |

## 卸载

```bash
cd /path/to/your/project

# 删除插件目录
rm -rf .ether/

# 删除 IDE 规则文件
rm -f .cursor/rules/ether.mdc
rm -f .claude/rules/ether.mdc

# 删除 Code Wiki（可选保留，作为文档）
rm -rf .wiki/

# 手动编辑 AGENTS.md 移除 fast-harness 章节（如果需要）
```

## 完整文档

安装后查看完整使用指南：

```bash
cat .ether/docs/guide.md
```

包含：架构全景、命令详解、实战场景（新需求实现、线上故障排查、批量重构消化审查建议）等。

## 致谢

- [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) — 三体架构设计理念
- [GAN (Generative Adversarial Network)](https://arxiv.org/abs/1406.2661) — Generator-Discriminator 分离思想

## License

MIT
