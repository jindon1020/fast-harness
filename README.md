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
| AI 缺信息时猜测 | 倾向猜测而非停下来问 | 每个 Agent 内置 `AskQuestion` 强制卡点 |
| 长流程上下文膨胀 | 40+ 轮工具调用后一致性下降 | **Context Reset** — Sub-agent 从文件契约获取上下文 |
| 代码自我评估失灵 | "看起来对"但有隐患 | **GAN 对抗审查** — Generator 不自评，独立 Reviewer 鉴别 |
| 架构逐渐偏移 | 持续迭代中打破分层约定 | 自动检测跨层引用，违规直接标记 Critical |
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
# 克隆仓库
git clone https://github.com/jindon1020/fast-harness.git /tmp/fast-harness

# 进入你的项目目录并运行安装
cd /path/to/your/project
bash /tmp/.ether/install.sh

# 清理
rm -rf /tmp/fast-harness
```

### 安装后配置

```bash
# 交互式配置项目上下文和基础设施（数据库、Redis、Kafka 等）
.ether/configure.sh

# 生成 project-context.md（项目上下文）和 config/infrastructure.json（中间件配置）
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
- `.cursor/rules/fast-harness.mdc` / `.claude/rules/fast-harness.mdc`
- `.cursor/agents/`、`.cursor/skills/`、`.cursor/commands/` 下的插件文件

**始终保留，不会被覆盖**：

- `.local/` — 密钥、kubeconfig、bastion 配置
- `.ai/` — 流水线运行产物（task_card、审查报告、测试结果等）
- `.ether/project-context.md` — 项目上下文（如已自定义）
- `.ether/config/infrastructure.json` — 基础设施配置（如已自定义）
- `.ether/agents/*/extensions/` — 用户自定义扩展文件
- `AGENTS.md` — 不重复追加 fast-harness 章节

> 大版本更新后建议重新运行 `.ether/configure.sh`，检查是否有新配置项需要填写。

## 目录结构

安装后，你的项目中会新增以下文件：

```
your-project/
├── AGENTS.md                          # AI 认知入口（追加 fast-harness 章节）
├── .cursor/
│   ├── rules/fast-harness.mdc         # Cursor 规则（仅 Cursor 平台）
│   ├── agents/                        # Cursor 自动识别的 Sub-agent（9 个）
│   ├── skills/                        # Cursor 自动识别的 Skill（5 个）
│   └── commands/                      # Cursor 斜杠命令（/implement /modify /fix /refactor）
├── .claude/rules/fast-harness.mdc     # Claude 规则（仅 Claude 平台）
└── .ether/                      # 插件原文目录（规范详细版）
    ├── .claude-plugin/
    │   └── plugin.json                # Claude Code 插件清单
    ├── commands/                      # 纯编排，不含项目细节
    │   ├── implement-command.md       # 需求实现流水线规范
    │   ├── modify-command.md          # 接口功能变更流水线规范
    │   ├── fix-command.md             # Bug 修复流水线规范
    │   └── refactor-command.md        # 代码重构流水线规范
    ├── agents/                        # Agent 目录化（含扩展点）
    │   ├── debugger-agent/
    │   │   ├── debugger-agent.md      # 系统流程 + Extension Points
    │   │   └── extensions/            # 用户自定义扩展（@data-source 等）
    │   ├── generator-agent/
    │   │   ├── generator-agent.md
    │   │   └── extensions/            # 用户自定义扩展（@coding-convention 等）
    │   ├── ... (其余 7 个 Agent 同理)
    │   └── _extension-template.md     # 扩展文件模板
    ├── config/                        # 基础设施配置
    │   ├── infrastructure.json        # 中间件连接配置（MySQL/Redis/Kafka）
    │   └── infrastructure.example.json
    ├── project-context.md             # 集中式项目上下文
    ├── skills/                        # 系统级 Skill
    │   ├── db-connector/              # 统一数据库连接
    │   ├── redis-connector/           # Redis 连接
    │   ├── kafka-connector/           # Kafka 连接
    │   ├── harness-meta-skill/        # 扩展点管理元技能
    │   ├── db-bastion-query/          # MySQL 堡垒机查询（旧版兼容）
    │   ├── kubectl-readonly/          # K8s 只读查询
    │   ├── k8s-monitor-full/          # K8s 诊断全套
    │   ├── loki-log-keyword-search/   # Loki 日志检索
    │   ├── prometheus-metrics-query/  # Prometheus 指标
    │   └── xmind-test-extractor/      # XMind 测试用例提取
    ├── configure.sh                   # 交互式项目配置脚本
    ├── project-context.example.md     # 项目上下文模板
    └── docs/
        └── guide.md                   # 完整使用说明
```

## 快速开始

### 启动第一个任务

```
/implement 我需要实现一个用户积分查询功能
```

流水线自动经过以下阶段：

```
Phase 0  需求设计     → Planner 与你多轮确认需求、API、数据库设计
                        ✋ 人类确认设计方案
Phase 1  代码生成     → Generator 按 task_card.json 编码
Phase 2  GAN 对抗审查 → Code Reviewer + Security Reviewer 并行
                        PASS → 继续 | FAIL → 自动修复（≤3 轮）
Phase 3  单元测试     → 连接本地 DB 查真实数据生成 + 执行
                        PASS → 继续 | FAIL → 自动修复（≤3 轮）
Phase 4  集成测试     → 解析 xmind 脑图生成 + 执行（可选）
Phase 5  最终报告     → 汇总结果 ✋ 确认提交
```

### 四大命令

| 命令 | 用途 | 示例 |
|------|------|------|
| `/implement` | 新功能开发 | `/implement 实现素材转移功能 sprint=sprint_2026_04` |
| `/modify` | 已有接口功能变更 | `/modify 积分查询接口增加时间范围筛选 module=asset` |
| `/fix` | Bug 修复 | `/fix 线上报 500 request_id=abc-123` |
| `/refactor` | 代码重构 | `/refactor 把分页逻辑抽取到 utils` |

所有命令支持 `fast=true` 快速模式（跳过 GAN 审查，节省 30-40% Token）。

### 9 个专职 Agent

| Agent | 角色 | 核心职责 |
|-------|------|----------|
| requirement-design-agent | Planner | 需求 → 结构化 task_card.json |
| generator-agent | Generator | 按任务卡编写实现代码 |
| code-reviewer-agent | Code Reviewer | 六维度代码质量审查 |
| security-reviewer-agent | Security Reviewer | 安全漏洞审查 |
| unit-test-gen-agent | 单元测试 | 连接本地 DB 真实数据驱动测试 |
| integration-test-gen-agent | 集成测试 | 解析 xmind 脑图生成测试 |
| test-runner-agent | Executor | 运行 pytest 输出 VERDICT |
| debugger-agent | Debugger | 本地修复 / 线上排查双路径 |
| monitor-agent | Monitor | K8s + Prometheus 只读监控 |

## 扩展点机制（v2.0 新增）

fast-harness v2.0 引入 Spring 式扩展点架构，用户可在不修改框架代码的前提下注入自定义逻辑：

```
框架层（不可修改）           用户扩展层（自由定制）
┌─────────────────┐       ┌─────────────────────────┐
│ Commands        │       │ project-context.md       │
│ (纯编排调度)      │       │ config/infrastructure.json│
├─────────────────┤       ├─────────────────────────┤
│ Agents          │◄─────│ extensions/*.md           │
│ (系统流程 +      │       │ (YAML frontmatter 声明    │
│  Extension Points)│      │  挂载点和优先级)           │
├─────────────────┤       └─────────────────────────┘
│ Connector Skills │
│ (db/redis/kafka) │
└─────────────────┘
```

### 使用扩展

1. 在 `.ether/agents/{agent}/extensions/` 下创建 `.md` 文件
2. 用 YAML frontmatter 声明挂载的扩展点（如 `@data-source`、`@coding-convention`）
3. Agent 启动时自动扫描并按优先级加载

### 使用 harness-meta-skill

直接告诉 AI：「帮我创建一个扩展」或「查看所有可用扩展点」，harness-meta-skill 会交互式引导完成。

## Token 消耗估算

| 流水线 | 典型消耗 | 典型耗时 |
|--------|---------|----------|
| `/implement`（完整） | 300k – 500k | 15 – 30 min |
| `/implement fast=true` | 100k – 200k | 6 – 12 min |
| `/modify` | 150k – 300k | 8 – 18 min |
| `/modify fast=true` | 80k – 150k | 4 – 10 min |
| `/fix` | 100k – 200k | 5 – 15 min |
| `/fix fast=true` | 50k – 100k | 3 – 8 min |
| `/refactor` | 200k – 400k | 10 – 20 min |
| `/refactor fast=true` | 150k – 300k | 8 – 15 min |

## 卸载

```bash
cd /path/to/your/project

# 删除插件目录
rm -rf .ether/

# 删除 IDE 规则文件
rm -f .cursor/rules/fast-harness.mdc
rm -f .claude/rules/fast-harness.mdc

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
