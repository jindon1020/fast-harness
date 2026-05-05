---
name: ahe-analyzer
description: AHE 根因分析——读取 .ai/harness-trace/ 下的轨迹数据，聚类失败模式并生成改进候选。触发于：分析 harness、分析 AHE、根因分析、harness 改进、生成改进候选、ahe analyze。
---

# AHE Analyzer

AHE 分析引擎——消费 AHE Observer 记录的结构化轨迹，自动进行**失败模式聚类**和**改进候选生成**。

---

## 能力一览

| 能力 | 触发词 | 说明 |
|------|--------|------|
| **分析轨迹** | ahe analyze、分析 harness、根因分析 | 批量读取轨迹，聚类失败模式，生成 RCA + CAND |
| **聚类报告** | 聚类报告、失败模式 | 输出按 phase 和归因标签分类的失败统计 |
| **RCA 详情** | 根因、rca 详情 | 对单条 RCA 进行深入分析，输出归因证据链 |
| **候选预览** | 候选预览、cand 预览 | 预览生成的 Edit Candidate，不实际生成 patch |

---

## 1. 分析轨迹

**触发词**：ahe analyze、分析 harness、分析 AHE、根因分析

### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `limit` | 50 | 分析最近 N 条轨迹 |
| `cluster_by` | phase | 聚类维度：`phase` / `component` / `failure_type` |

### 执行步骤

**Step 1: 收集轨迹**

```bash
TRACE_DIR=".ai/harness-trace"
LIMIT=${limit:-50}
CLUSTER_BY=${cluster_by:-phase}

echo "## AHE 分析报告"
echo "分析时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "分析范围：最近 $LIMIT 条轨迹"
echo ""

# 收集所有轨迹文件（按时间倒序）
TRACES=$(ls -t "$TRACE_DIR"/*.jsonl 2>/dev/null | head "$LIMIT")

if [ -z "$TRACES" ]; then
  echo "暂无轨迹数据。请先执行 Command 积累轨迹（.ai/harness-trace/）。"
  exit 0
fi

echo "**找到 $(echo "$TRACES" | wc -l | tr -d ' ') 条轨迹**"
echo ""
```

**Step 2: 解析失败轨迹**

```python
# 使用 Python 解析所有轨迹，提取失败 phase 信息
python3 << 'PYEOF'
import json, sys
from collections import defaultdict

traces = []
for line in sys.stdin if sys.stdin.isatty() else []:
    pass  # 从文件读取

# 读取轨迹
import subprocess, glob
trace_files = sorted(glob.glob(".ai/harness-trace/*.jsonl"), 
                     key=lambda p: p.mtime(), reverse=True)[:50]

failed_phases = defaultdict(list)
all_verdicts = []

for tf in trace_files:
    with open(tf) as f:
        try:
            trace = json.loads(f.readline())
        except:
            continue
    
    command = trace.get("command", "?")
    module = trace.get("module", "?")
    retry_count = trace.get("retry_count", 0)
    
    # 统计 verdicts
    for v in trace.get("verdicts", []):
        all_verdicts.append({
            "phase": v.get("phase", "?"),
            "verdict": v.get("verdict", "?"),
            "reason": v.get("reason", ""),
            "command": command,
            "module": module
        })
        if v.get("verdict") == "FAIL":
            failed_phases[v.get("phase", "?")].append(v)

# 输出失败统计
print(f"\n## 失败统计（共 {len(all_verdicts)} 条 verdict）")
print(f"失败 phase 数：{len(failed_phases)}")
for phase, items in sorted(failed_phases.items(), key=lambda x: -len(x[1])):
    pct = len(items) / len(all_verdicts) * 100 if all_verdicts else 0
    print(f"  {phase}: {len(items)} 次 ({pct:.1f}%)")

PYEOF
```

**Step 3: 生成 RCA（Root Cause Analysis）**

对每个失败 cluster，执行 LLM 分析：

```
分析以下失败轨迹，给出根因归因：

失败 phase：[phase name]
失败次数：N
失败原因摘要：[从轨迹提取]

请输出：
1. root_cause：一句话描述根本原因（必须归因到具体 harness 组件，如 generator-agent.@coding-convention）
2. attributed_component：具体的组件名
3. evidence：2-3 条支持证据
4. confidence：high/medium/low
```

**Step 4: 生成 Edit Candidate**

对每个 RCA，生成 3 条改进候选：

```
针对以下 Root Cause，生成 3 条改进候选：

Root Cause：[rca.root_cause]
目标组件：[rca.attributed_component]

生成 3 个 variant：
- Variant A（最小改动）：只改措辞/描述，不改结构
- Variant B（中改动）：增加/删除一个检查项
- Variant C（大改动）：重新设计组件逻辑

输出格式：
CAND-{N}-A: {description} | risk: low
CAND-{N}-B: {description} | risk: medium  
CAND-{N}-C: {description} | risk: high
```

**Step 5: 输出分析报告**

```markdown
## AHE 分析报告
分析时间：{timestamp}
分析轨迹数：{N} 条（失败：{M} 条）

### 失败模式聚类

| 模式 | 失败数 | 占比 | 代表 Phase |
|------|--------|------|-----------|
| tool_desc_incomplete | 12 | 40% | Phase 1 |
| context_insufficient | 8 | 27% | Phase 3 |

### Root Cause 详情

#### RC-{N}: {root_cause}
- **归因组件**: {attributed_component}
- **证据**: {evidence}
- **置信度**: {confidence}

### Edit Candidates

| ID | 目标组件 | Variant | 描述 | 风险 |
|----|---------|---------|------|------|
| CAND-001-A | generator-agent.@coding-convention | A | {最小改动描述} | low |
| CAND-001-B | generator-agent.@coding-convention | B | {中改动描述} | medium |
| CAND-002-A | code-reviewer-agent.@review-dimension | A | {...} | low |

### 建议

推荐优先实施 low-risk candidate。
触发 `/ahe-evo apply <candidate_id>` 应用改进。
```

---

## 2. 聚类报告

**触发词**：聚类报告、失败模式

```bash
python3 << 'EOF'
import json, glob
from collections import defaultdict

trace_files = sorted(glob.glob(".ai/harness-trace/*.jsonl"), 
                     key=lambda p: __import__('os').path.getmtime(p), reverse=True)[:100]

failure_by_phase = defaultdict(int)
failure_by_component = defaultdict(int)
failure_by_type = defaultdict(int)

for tf in trace_files:
    with open(tf) as f:
        trace = json.loads(f.readline())
    for v in trace.get("verdicts", []):
        if v.get("verdict") == "FAIL":
            failure_by_phase[v.get("phase", "?")] += 1
            failure_by_component[v.get("component", "?")] += 1
            failure_by_type[v.get("failure_type", "unknown")] += 1

print("### 失败聚类（按 Phase）")
for k, v in sorted(failure_by_phase.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print()
print("### 失败聚类（按组件）")
for k, v in sorted(failure_by_component.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print()
print("### 失败聚类（按类型）")
for k, v in sorted(failure_by_type.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
EOF
```

---

## 3. 候选预览

**触发词**：候选预览、cand 预览

```bash
# 读取上次分析报告中的 candidates
ANALYSIS_FILE=$(ls -t .ai/harness-evolution/*_analysis.md 2>/dev/null | head -1)

if [ -z "$ANALYSIS_FILE" ]; then
  echo "暂无分析报告。请先执行 `/ahe-analyze`。"
  exit 0
fi

echo "## Edit Candidates 预览"
echo ""
grep "^| CAND-" "$ANALYSIS_FILE" | head -10
```

---

*AHE Analyzer 是 fast-harness AHE 框架的分析组件，按需触发，不影响正常 Command 执行流程。*
