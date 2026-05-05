# AHE: Agentic Harness Engineering in fast-harness

> Observability-Driven Automatic Evolution of Coding-Agent Harnesses

## 概述

本文档说明 AHE 框架如何集成到 fast-harness，为 Command/Agent/Skill 三层架构注入**组件级可观测性**，支撑 harness 的自动分析 → 演化闭环。

## 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                     fast-harness                         │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │   Command    │   │    Agent     │   │    Skill     │  │
│  │  implement   │   │ generator-   │   │ code-wiki-   │  │
│  │  refactor    │   │    agent     │   │     gen      │  │
│  │    fix       │   │ code-review- │   │   db-        │  │
│  │              │   │    agent     │   │  connector   │  │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘  │
│         │                  │                   │          │
│         └──────────────────┼───────────────────┘          │
│                            │                              │
│              ┌─────────────┴─────────────┐                │
│              │    Extension Protocol     │                │
│              │  (可观测性注入点)          │                │
│              └─────────────┬─────────────┘                │
│                            │                              │
│              ┌─────────────┴─────────────┐                │
│              │      AHE Observer         │  ← 轨迹记录    │
│              │  (被动收集，无侵入)        │                │
│              └─────────────┬─────────────┘                │
│                            │                              │
│              ┌─────────────┴─────────────┐                │
│              │     .ai/harness-trace/    │  ← 轨迹存储   │
│              └─────────────┬─────────────┘                │
└────────────────────────────┼─────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │        AHE Analyzer         │  ← 根因分析
              │   (按需触发，批量分析)       │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │       AHE Evo Engine        │  ← 自动演化
              │   (patch + A/B eval)        │
              └──────────────────────────────┘
```

## 三大可观测性支柱

### 1. 组件可观测性（Component Observability）

fast-harness 的 Extension Protocol 本身就是**组件级抽象**：
- 每个 Agent 的 `@pre-generation` / `@coding-convention` / `@review-dimension` 等扩展点即 AHE 组件
- Extension 版本的变更 → 直接记录到轨迹的 `components[].extensions[]` 字段
- Extension 内容的 diff → 演化的 patch 目标

```
修改粒度：从"改动了哪些文件"细化到"改了哪个组件的哪个扩展点"
```

### 2. 轨迹可观测性（Trajectory Observability）

**无侵入收集**：Observer Skill 在 Command 执行过程中被动记录，不改变业务逻辑。

每次 Command 执行后写入一条 JSONL：
```jsonl
{"trace_id":"...","command":"implement","phase":"Phase 1","agents":["generator-agent"],"verdict":"PASS","duration":12.3,...}
```

### 3. 效果可观测性（Effect Observability）

**Edit → Delta 因果链**：
- 每条轨迹记录本次执行涉及的**具体组件版本**
- Evo 后同一任务在新旧 harness 上各跑一次，对比 pass@1
- McNemar 检验判断改进是否统计显著

## 目录结构

```
plugin/skills/
├── ahe-observer/          # AHE 观测层（被动收集轨迹）
│   ├── SKILL.md
│   └── benchmarks/
│       └── ahe-eval-set.jsonl  # A/B Eval 测试集
│
├── ahe-analyzer/          # AHE 分析引擎（根因 + 候选生成）
│   ├── SKILL.md
│   └── prompts/
│
└── ahe-evo/               # AHE 演化引擎（patch + A/B 验证）
    ├── SKILL.md
    └── prompts/

.ai/harness-trace/         # 轨迹数据（自动生成）
.ai/harness-evolution/     # 演化记录（分析报告 + Evo 日志）
```

## 使用流程

### 阶段 1：积累轨迹（Observing）

正常执行 Command，Observer 自动记录轨迹：
```
/implement 实现xxx [module=project]
→ 执行完毕
→ .ai/harness-trace/20260505_implement_project_featurex.jsonl 已写入
```

### 阶段 2：分析根因（Analyzing）

积累 30+ 条轨迹后，触发分析：
```
/ahe-analyze limit=50 cluster_by=phase
→ .ai/harness-evolution/20260505_analysis.md 已生成
→ 包含失败模式聚类、Root Cause、Edit Candidates
```

### 阶段 3：自动演化（Evolving）

对候选改动执行 A/B Eval：
```
/ahe-evo apply CAND-001-A
→ 创建实验分支 feat/ahe-evo-CAND-001-A
→ 应用 patch
→ 触发 A/B Eval
→ 输出 pass@1 delta + 统计显著性
```

推荐实施策略：
- delta > +2% 且统计显著（p<0.05）→ 自动合并
- delta 在 -2%~+2% 之间 → 人工决策
- delta < -2% → 丢弃

## 与现有框架的兼容性

| fast-harness 已有特性 | AHE 叠加方式 |
|---------------------|------------|
| Command 流水线 | 在各 Phase 切换点插入 Observer 事件 |
| Agent 分权（Generator/Reviewer/Tester） | 每个 Agent 的 VERDICT 作为独立观测点 |
| File Contract 通信 | 契约文件路径 + VERDICT 结果同时记录 |
| Extension Protocol | Extension 加载本身即组件事件，无需额外埋点 |
| Retry Loop | 重试次数 + 每次失败原因作为关键信号 |
| 人类确认卡点（HARD STOP） | 卡点前后状态作为轨迹分隔标记 |

## 演进路线

### Phase 1（当前）
- [x] AHE Observer：轨迹记录框架
- [x] AHE Analyzer：根因分析 + Edit Candidate 生成
- [x] AHE Evo Engine：patch 应用 + A/B Eval
- [x] AHE Eval Set：基准测试集

### Phase 2（规划中）
- [ ] Extension 版本管理（自动追踪 Extension 文件变更）
- [ ] 动态 Harness Config（根据任务类型自动切换 harness 变体）
- [ ] 多-harness 灰度（同一任务在 N 个 harness 变体上并行跑）

### Phase 3（愿景）
- [ ] 完全自动化的 Evolution Loop（无需人工触发 Analyze → Evo）
- [ ] Learned Harness Prior（基于历史轨迹训练的 harness 初始化策略）

---

*AHE 框架论文：[arXiv:2604.25850](https://arxiv.org/abs/2604.25850) | Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses*
