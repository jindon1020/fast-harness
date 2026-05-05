# AHE Analyzer Skill

## Purpose

AHE 分析引擎——消费 AHE Observer 记录的结构化轨迹，自动进行**失败根因分析**（Root Cause Analysis）和**改进候选生成**（Edit Candidate Generation）。

## What It Does

当 `.ai/harness-trace/` 目录下积累了一定数量的轨迹数据后，AHE Analyzer 可以：
1. 读取轨迹数据，识别失败模式
2. 将失败轨迹按根因分类（prompt 措辞问题 / 工具描述不清 / 流程顺序不当 / skill 缺失）
3. 为每个失败模式生成具体可操作的 harness 改进建议
4. 输出可执行的 patch 方案（对 Agent prompt / extension / skill 的修改）

## Integration Points

Analyzer 不是流水线的常驻组件，而是**按需调用**：

```bash
# 手动触发（分析最近 N 条轨迹）
/ahe-analyze [limit=50]

# 自动触发（每 N 条命令执行后）
# → 由 Command 框架在执行完一定数量后自动触发
```

## Analysis Pipeline

### Step 1: Load Traces

从 `.ai/harness-trace/` 读取最近 `limit` 条轨迹，筛选其中 `verdict=FAIL` 的条目。

### Step 2: Pattern Clustering

将失败轨迹按**失败 phase** 和**归因标签**进行聚类：

```
标签分类：
- prompt_ambiguous        → prompt 措辞模糊或有歧义
- tool_desc_incomplete    → 工具描述缺少必要参数或示例
- skill_missing           → 缺少某个领域的 skill
- context_insufficient    → 上下文信息不足（如 wiki 缺失）
- flow_order_suboptimal   → 流程顺序安排不当
- assertion_too_strict    → 测试断言过于严格
- infra_unstable          → 基础设施问题（非 harness 原因）
```

### Step 3: Root Cause Analysis

对每个失败 cluster，运行 LLM 分析：

**Prompt 输入**（从轨迹提取）：
- 失败 phase 的 VERDICT + 重试次数
- 失败轨迹中的具体错误信息（review_feedback.md / unit_test_results.md 摘要）
- 涉及的 Agent 和 Extension 版本
- 该类任务的历史成功案例（如有）

**Prompt 要求**：
```
你是一个 AHE（Agentic Harness Engineering）分析引擎。
分析以下失败轨迹，找出根本原因（Root Cause）。
Root Cause 必须是**可直接归因到某个 harness 组件**的问题，
而不是"模型能力不足"这类模糊解释。

输出格式：
{
  "root_cause": "一句话描述根本原因",
  "attributed_component": "具体组件名，如 generator-agent.@coding-convention",
  "evidence": ["证据1", "证据2"],
  "confidence": "high|medium|low"
}
```

### Step 4: Edit Candidate Generation

对每个确认的 Root Cause，生成 3 条改进候选：

**生成策略**：
- **Variant A**：最小改动（只改措辞/描述，不改结构）
- **Variant B**：中改动（增加/删除一个检查项或步骤）
- **Variant C**：大改动（重新设计组件逻辑）

**输出格式**：
```json
{
  "candidate_id": "CAND-001",
  "target_component": "generator-agent.@coding-convention",
  "variant": "A|B|C",
  "description": "在 coding-convention 中增加边界条件处理 Checklist",
  "patch": {
    "type": "extension_patch|skill_patch|prompt_patch",
    "file": ".ai/agents/generator-agent/extensions/wiki-coding-convention.md",
    "diff": "- 原始内容\n+ 新增内容"
  },
  "expected_impact": "修复 {failure_pattern}，预期 pass@1 提升 X%",
  "risk": "low|medium|high"
}
```

## Usage

### 手动触发

```
/ahe-analyze limit=50 cluster_by=phase
```

### 自动触发（集成到 Command）

在 Command 的最终报告阶段，可以插入：

```markdown
### AHE 观测数据
- 轨迹已记录：`.ai/harness-trace/{timestamp}_{command}_{module}_{branch}.jsonl`
- 如需分析 harness 改进方向，触发 `/ahe-analyze`
```

## Output

Analyzer 的输出写入 `.ai/harness-evolution/{timestamp}_analysis.md`：

```markdown
# AHE Analysis Report
生成时间：{timestamp}
分析轨迹数：{N} 条（失败：{M} 条）

## 失败模式聚类

| 模式 | 失败数 | 占比 | 代表 phase |
|------|--------|------|-----------|
| tool_desc_incomplete | 12 | 40% | Phase 1 |
| context_insufficient | 8 | 27% | Phase 3 |

## Root Cause 详情

### RC-001: tool_desc_incomplete
- **根因**：generator-agent 对 router 的 tool description 缺少参数示例
- **证据**：...（2条）
- **置信度**：high
- **涉及 phase**：Phase 1（代码生成）

## Edit Candidates

### CAND-001-A（最小改动）
- **目标组件**：generator-agent.@coding-convention
- **改动描述**：在 extension 中增加"必填参数必须包含示例值"规则
- **预期影响**：减少因参数描述不清导致的返工
- **风险**：low

[CAND-002...]

## 建议

推荐优先实施 CAND-001（CAND-002 次之）。
高风险改动（CAND-003）建议在 staging 环境验证后再合并。
```

---

*This skill is part of the AHE (Agentic Harness Engineering) framework for observability-driven harness evolution.*
