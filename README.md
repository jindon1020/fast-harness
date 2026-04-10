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
       │  FAIL+feedback  │   api-test-agent          │
       │◄────────────── │   test-runner              │
       │                 ├─────────────────────────┤
  debugger-agent         │ Round 3: 集成测试         │
  (最小化修复)            │   tester-gen-agent        │
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

# 自动检测平台，安装到 fast-harness/ 目录
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
bash /tmp/fast-harness/install.sh

# 清理
rm -rf /tmp/fast-harness
```

### 安装后配置

```bash
# 交互式配置项目上下文（数据库、服务地址等）
fast-harness/configure.sh

# 或手动编辑 commands 中的 {{占位符}}
```

### 安全保证

安装脚本遵循以下原则：

- **不覆盖已有文件** — 所有文件操作使用 safe_copy，已存在的文件会跳过并提示
- **不修改已有配置** — AGENTS.md 采用追加模式，不覆盖已有内容
- **不泄露敏感信息** — skills 目录下的密钥文件均为 `.example` 模板
- **可完全回退** — 删除插件目录和对应的 rules 文件即可完全卸载

## 目录结构

安装后，你的项目中会新增以下文件：

```
your-project/
├── AGENTS.md                          # AI 认知入口（追加 fast-harness 章节）
├── .cursor/
│   ├── rules/fast-harness.mdc         # Cursor 规则（仅 Cursor 平台）
│   ├── agents/                        # Cursor 自动识别的 Sub-agent（9 个）
│   ├── skills/                        # Cursor 自动识别的 Skill（5 个）
│   └── commands/                      # Cursor 斜杠命令（/implement /fix /refactor）
├── .claude/rules/fast-harness.mdc     # Claude 规则（仅 Claude 平台）
└── fast-harness/                      # 插件原文目录（规范详细版）
    ├── .claude-plugin/
    │   └── plugin.json                # Claude Code 插件清单
    ├── commands/
    │   ├── implement-command.md       # 需求实现流水线规范
    │   ├── fix-command.md             # Bug 修复流水线规范
    │   └── refactor-command.md        # 代码重构流水线规范
    ├── agents/
    │   ├── requirement-design-agent.md  # Planner
    │   ├── generator-agent.md           # Generator
    │   ├── code-reviewer-agent.md       # Code Reviewer
    │   ├── security-reviewer-agent.md   # Security Reviewer
    │   ├── api-test-agent.md            # 单元测试生成
    │   ├── tester-gen-agent.md          # 集成测试生成
    │   ├── test-runner-agent.md         # 测试执行
    │   ├── debugger-agent.md            # 调试修复
    │   └── monitor-agent.md             # K8s 监控
    ├── skills/
    │   ├── dev-mysql-bastion-query/     # MySQL 堡垒机查询
    │   ├── kubectl-readonly/            # K8s 只读查询
    │   ├── k8s-monitor-full/            # K8s 诊断全套
    │   ├── loki-log-keyword-search/     # Loki 日志检索
    │   └── prometheus-metrics-query/    # Prometheus 指标
    ├── configure.sh                     # 项目上下文配置脚本
    ├── project-context.example.md       # 项目上下文模板
    └── docs/
        └── guide.md                     # 完整使用说明
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

### 三大命令

| 命令 | 用途 | 示例 |
|------|------|------|
| `/implement` | 新功能开发 | `/implement 实现素材转移功能 sprint=sprint_2026_04` |
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
| api-test-agent | 单元测试 | 连接本地 DB 真实数据驱动测试 |
| tester-gen-agent | 集成测试 | 解析 xmind 脑图生成测试 |
| test-runner-agent | Executor | 运行 pytest 输出 VERDICT |
| debugger-agent | Debugger | 本地修复 / 线上排查双路径 |
| monitor-agent | Monitor | K8s + Prometheus 只读监控 |

## Token 消耗估算

| 流水线 | 典型消耗 | 典型耗时 |
|--------|---------|----------|
| `/implement`（完整） | 300k – 500k | 15 – 30 min |
| `/implement fast=true` | 100k – 200k | 6 – 12 min |
| `/fix` | 100k – 200k | 5 – 15 min |
| `/fix fast=true` | 50k – 100k | 3 – 8 min |
| `/refactor` | 200k – 400k | 10 – 20 min |
| `/refactor fast=true` | 150k – 300k | 8 – 15 min |

## 卸载

```bash
cd /path/to/your/project

# 删除插件目录
rm -rf fast-harness/

# 删除 IDE 规则文件
rm -f .cursor/rules/fast-harness.mdc
rm -f .claude/rules/fast-harness.mdc

# 手动编辑 AGENTS.md 移除 fast-harness 章节（如果需要）
```

## 完整文档

安装后查看完整使用指南：

```bash
cat fast-harness/docs/guide.md
```

包含：架构全景、命令详解、实战场景（新需求实现、线上故障排查、批量重构消化审查建议）等。

## 致谢

- [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) — 三体架构设计理念
- [GAN (Generative Adversarial Network)](https://arxiv.org/abs/1406.2661) — Generator-Discriminator 分离思想

## License

MIT
