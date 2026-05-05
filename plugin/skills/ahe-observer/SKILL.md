# AHE Observer Skill

## Purpose

AHE（Agentic Harness Engineering）观测层——为 fast-harness 框架注入**组件级可观测性**，支撑 harness 自动演化闭环。

## What It Does

在每次 Command 执行过程中，自动记录结构化轨迹数据，包括：
- 各 Phase 参与组件（Agent + Extension + Skill）
- 执行结果（VERDICT、耗时、重试次数）
- 失败根因（由 LLM 分析失败轨迹自动归因）

执行完毕后，将轨迹写入 `.ai/harness-trace/{timestamp}_{command}_{module}_{branch}.jsonl`，供后续 AHE Analyzer 分析。

## Integration Points

### Agent Extension Points

| Extension Point | AHE 注入内容 |
|----------------|------------|
| `@pre-generation` | 记录 generator-agent 启动时的组件状态 |
| `@coding-convention` | 注入 convention 加载事件 |
| `@review-dimension` | 注入 review 各维度结果 |
| `@project-rule` | 注入规则匹配事件 |

### Command Hooks

| Hook | 注入位置 |
|------|---------|
| Pre-flight | 记录 command 启动配置（参数、环境） |
| Phase transition | 记录 phase 切换事件（Agent 委托/响应） |
| VERDICT 输出 | 记录 PASS/FAIL + 失败原因 |
| Retry Loop | 记录重试次数 + 每次失败根因 |
| 最终报告 | 记录完整执行摘要 |

## Trace Schema

```json
{
  "trace_id": "uuid",
  "command": "implement|refactor|fix|...",
  "module": "...",
  "branch": "...",
  "mode": "full|fast",
  "timestamp": "ISO8601",
  "duration_seconds": 0.0,
  "components": [
    {
      "name": "generator-agent",
      "type": "agent",
      "version": "...",
      "extensions": ["@pre-generation", "@coding-convention"],
      "skills": ["code-wiki-gen"],
      "started_at": "ISO8601",
      "verdict": "PASS|FAIL|SKIP",
      "fail_reason": null,
      "retry_count": 0
    }
  ],
  "phases": [
    {
      "phase": "Phase 0: 需求设计",
      "agents": ["requirement-design-agent"],
      "verdict": "PASS|FAIL|SKIP",
      "duration_seconds": 0.0,
      "events": [
        {
          "event": "agent_delegated",
          "agent": "requirement-design-agent",
          "timestamp": "ISO8601"
        },
        {
          "event": "verdict_received",
          "verdict": "PASS",
          "timestamp": "ISO8601"
        }
      ]
    }
  ],
  "root_cause_analysis": {
    "performed": false,
    "failed_phases": [],
    "rca_by_phase": {}
  }
}
```

## Usage

AHE Observer 是一个**被动 Skill**——它由 Command 框架在特定时机自动调用，不需要用户显式触发。

在 `implement-command.md` / `refactor-command.md` 等 Command 文件中，通过 `skill:ahe-observer` 声明依赖：

```yaml
---
skill: ahe-observer
---
```

Observer 会在以下时机自动记录数据：
1. Pre-flight 开始 → `preflight_started` 事件
2. 每个 Phase 开始/结束 → `phase_started` / `phase_completed` 事件
3. 每个 Agent 委托 → `agent_delegated` 事件
4. 每个 VERDICT 收到 → `verdict_received` 事件
5. Retry Loop 触发 → `retry_loop` 事件（含失败原因）
6. Command 结束 → `command_completed` 事件（含完整摘要）

## Root Cause Analysis

当 `root_cause_analysis: performed=true` 时，字段结构如下：

```json
{
  "failed_phases": ["Phase 2: GAN审查", "Phase 3: 单元测试"],
  "rca_by_phase": {
    "Phase 2: GAN审查": {
      "symptom": "code-reviewer-agent VERDICT: FAIL",
      "root_cause": "工具描述措辞过于抽象，导致生成的代码对边界条件处理不完整",
      "attributed_component": "generator-agent.@coding-convention",
      "suggested_fix": "在 @coding-convention 扩展中增加边界条件处理 Checklist",
      "confidence": "high|medium|low"
    }
  }
}
```

## Output

轨迹文件写入 `.ai/harness-trace/` 目录，格式为 JSONL（每条轨迹一行），方便后续批量分析和训练数据生成。

文件命名：`{timestamp}_{command}_{module}_{branch}.jsonl`

---

*This skill is part of the AHE (Agentic Harness Engineering) framework for observability-driven harness evolution.*
