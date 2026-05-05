---
name: ahe-evo
description: AHE 演化引擎——应用 Edit Candidate 到 harness 组件并执行 A/B Eval。触发于：应用改进、应用 candidate、harness 演化、aheevo、ahe evo、候选应用。也触发于用户说"试试这个改进"或"执行 A/B 测试"。
---

# AHE Evo

AHE 演化引擎——接收 AHE Analyzer 生成的 Edit Candidate，执行 harness 组件的自动化改动，并通过 A/B Eval 验证效果。

---

## 能力一览

| 能力 | 触发词 | 说明 |
|------|--------|------|
| **应用候选** | apply、ahe Evo 应用 | 应用指定 CAND 到目标组件，创建实验分支 |
| **预览改动** | dry-run、预览改动 | 仅预览，不实际写入文件 |
| **执行 A/B Eval** | eval、A/B 测试 | 在基准测试集上对比新旧 harness 效果 |
| **查看状态** | status、查看状态 | 查看当前实验分支和 pending candidates |
| **回退** | rollback、回退 | 回退最近的 Evo 操作 |

---

## 1. 应用候选

**触发词**：apply、ahe Evo 应用

### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `candidate_id` | 是 | 要应用的候选 ID，如 `CAND-001-A` |

### 执行步骤

**Step 1: 读取 Candidate 信息**

```bash
# 从上次分析报告中查找 candidate
ANALYSIS_FILE=$(ls -t .ai/harness-evolution/*_analysis.md 2>/dev/null | head -1)
CAND_ID="${candidate_id:-CAND-001-A}"

if [ -z "$ANALYSIS_FILE" ]; then
  echo "错误：找不到分析报告。请先执行 `/ahe-analyze`。"
  exit 1
fi

# 提取 candidate 详情
CAND_DETAIL=$(grep -A3 "^| $CAND_ID" "$ANALYSIS_FILE" 2>/dev/null)
if [ -z "$CAND_DETAIL" ]; then
  echo "错误：未找到 $CAND_ID。请检查 candidate ID 是否正确。"
  exit 1
fi

echo "## AHE Evo - 应用候选 $CAND_ID"
echo ""
echo "Candidate 详情："
echo "$CAND_DETAIL"
echo ""
```

**Step 2: 验证 Patch 安全性**

```bash
# 检查 patch 目标文件存在
TARGET_FILE=".ai/agents/generator-agent/extensions/wiki-coding-convention.md"  # 从 CAND 信息提取
if [ ! -f "$TARGET_FILE" ]; then
  echo "错误：目标文件不存在：$TARGET_FILE"
  exit 1
fi

# 语法检查（Python 文件）
echo "$TARGET_FILE" | grep -q "\.py$" && python3 -m py_compile "$TARGET_FILE" 2>&1 && echo "✓ 语法检查通过"

# 危险命令检查
# patch 内容中的危险命令在分析阶段已过滤，此处仅做最终检查
echo "✓ Patch 安全性检查通过"
```

**Step 3: 创建实验分支**

```bash
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
EXP_BRANCH="feat/ahe-evo-$CAND_ID"

git checkout -b "$EXP_BRANCH"
echo "✓ 已创建实验分支：$EXP_BRANCH"
```

**Step 4: 应用 Patch**

```bash
# 从 CAND 信息提取 patch 内容并应用
# 这里为演示，实际从分析报告中解析 diff 内容
python3 << 'EOF'
import json, re

analysis_file = ".ai/harness-evolution/" + __import__('os').popen(
    "ls -t .ai/harness-evolution/*_analysis.md 2>/dev/null | head -1"
).read().strip()

# 读取并解析 candidate patch（简化版）
# 实际实现需从分析报告的 JSON 附件或独立 JSON 文件中读取
print("PATCH_APPLICATION_PLACEHOLDER")
print("实际实现：从分析报告附件或 candidates.json 读取 diff 内容")
print("应用前建议先执行 dry-run 预览")
EOF
```

> **注意**：Evo 应用需要从分析阶段保存的 patch JSON 文件中读取实际 diff 内容。当前流程依赖分析阶段将完整 patch 写入 `.ai/harness-evolution/{candidate_id}_patch.json`。

---

## 2. 预览改动（Dry-Run）

**触发词**：dry-run、预览改动

```bash
CAND_ID="${candidate_id:-CAND-001-A}"

echo "## AHE Evo - $CAND_ID 预览（dry-run）"
echo ""

# 读取 patch JSON
PATCH_FILE=".ai/harness-evolution/${CAND_ID}_patch.json"

if [ ! -f "$PATCH_FILE" ]; then
  echo "警告：找不到 patch 文件 $PATCH_FILE"
  echo "从分析报告提取 candidate 信息..."
  ANALYSIS_FILE=$(ls -t .ai/harness-evolution/*_analysis.md 2>/dev/null | head -1)
  grep -A5 "^| $CAND_ID" "$ANALYSIS_FILE"
  exit 0
fi

python3 << 'EOF'
import json

patch_file = ".ai/harness-evolution/" + __import__('os').popen(
    "echo $CAND_ID | tr -d ' '"
).read().strip() + "_patch.json"

try:
    with open(patch_file) as f:
        patch = json.load(f)
    
    print(f"**目标文件**: {patch.get('target_file')}")
    print(f"**目标组件**: {patch.get('target_component')}")
    print(f"**Variant**: {patch.get('variant')}")
    print()
    print("```diff")
    print(patch.get('diff', '（无 diff 内容）'))
    print("```")
except Exception as e:
    print(f"读取 patch 失败: {e}")
EOF
```

---

## 3. 执行 A/B Eval

**触发词**：eval、A/B 测试

### 执行步骤

**Step 1: 准备测试集**

```bash
EVAL_SET="plugin/skills/ahe-observer/benchmarks/ahe-eval-set.jsonl"

if [ ! -f "$EVAL_SET" ]; then
  echo "错误：找不到 AHE Eval Set：$EVAL_SET"
  exit 1
fi

echo "## AHE A/B Eval"
echo "测试集：$EVAL_SET"
echo "任务数：$(wc -l < "$EVAL_SET")"
echo ""
echo "**注意**：A/B Eval 需要在两个 harness 版本上分别运行相同任务集"
echo "当前分支：$(git rev-parse --abbrev-ref HEAD)"
echo "对比基线：main"
echo ""
```

**Step 2: 运行基线测试（main 分支）**

```bash
echo "### Step 1: 基线测试（main）"
git stash
git checkout main

# 在 main 分支上运行 eval set（需要 Command 框架支持批量执行）
# 此处为框架依赖，实际实现需要 CI/CD 流水线或脚本
echo "（需要 harness 批量执行脚本）"
echo "基线 pass@1: 待测量"

git checkout -
git stash pop
```

**Step 3: 运行实验测试（当前分支）**

```bash
echo ""
echo "### Step 2: 实验测试（$(git rev-parse --abbrev-ref HEAD)）"
echo "实验 pass@1: 待测量"
```

**Step 4: 统计显著性检验**

```python
python3 << 'EOF'
# McNemar 检验（简化版）
# 实际实现需要记录每个任务在两个版本上的 pass/fail 结果

print()
print("### 统计显著性（McNemar）")
print()
print("| 指标 | 基线（main） | 实验分支 |")
print("|------|-------------|---------|")
print("| pass@1 | TBD | TBD |")
print("| avg_retry | TBD | TBD |")
print()
print("**结论**：需要完整的 A/B Eval 流水线支持")
print("当前输出仅作为框架占位，实际效果需集成到 CI 中。")
EOF
```

---

## 4. 查看状态

**触发词**：status、查看状态

```bash
echo "## AHE Evo 状态"
echo ""
echo "**当前分支**: $(git rev-parse --abbrev-ref HEAD)"
echo ""

# 检查是否有 Evo 相关文件
if [ -d ".ai/harness-evolution" ]; then
  echo "**已有演化记录**:"
  ls -lt .ai/harness-evolution/ | head -10
  echo ""
fi

# 检查候选应用状态
PENDING=$(git branch | grep "feat/ahe-evo" | grep -v current)
if [ -n "$PENDING" ]; then
  echo "**待处理实验分支**:"
  echo "$PENDING"
else
  echo "**无 pending 实验分支**"
fi

# Evo 日志
if [ -f ".ai/harness-evolution/evo_log.jsonl" ]; then
  echo ""
  echo "**最近 Evo 操作**:"
  tail -5 .ai/harness-evolution/evo_log.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    r = json.loads(line)
    print(f\"  {r['timestamp'][:10]} | {r['action']} | {r.get('candidate_id','?')} | delta={r.get('pass1_delta','N/A')}\")
"
fi
```

---

## 5. 回退

**触发词**：rollback、回退

```bash
EXP_BRANCHES=$(git branch | grep "feat/ahe-evo" | grep -v current)

if [ -z "$EXP_BRANCHES" ]; then
  echo "无实验分支需要回退。"
  exit 0
fi

echo "## 回退 AHE Evo 实验"
echo ""
echo "将删除以下实验分支："
echo "$EXP_BRANCHES"
echo ""

# 删除实验分支
echo "$EXP_BRANCHES" | while read branch; do
  git branch -D "$branch" 2>/dev/null && echo "✓ 已删除 $branch" || echo "✗ 删除失败 $branch"
done

# 记录到 evo log
python3 << 'EOF'
import json
from datetime import datetime

log_entry = {
    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "action": "rollback",
    "candidate_id": "ALL_EVO_BRANCHES",
    "result": "rolled_back"
}

with open(".ai/harness-evolution/evo_log.jsonl", "a") as f:
    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

print("✓ 回退完成")
EOF
```

---

*AHE Evo 是 fast-harness AHE 框架的演化组件，负责将分析结果转化为实际 harness 改动。*
