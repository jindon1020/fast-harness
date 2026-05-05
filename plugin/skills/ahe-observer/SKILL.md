---
name: ahe-observer
description: AHE 轨迹记录——为每次 Command 执行自动记录结构化轨迹数据到 .ai/harness-trace/。触发于：任何 Command 执行完毕、查看轨迹、查看 AHE 数据、harness 观测。也触发于用户说"记录这条执行"或"追踪 harness 组件"。
---

# AHE Observer

AHE（Agentic Harness Engineering）观测层——为 fast-harness Command 执行注入组件级可观测性，自动记录结构化轨迹。

---

## 能力一览

| 能力 | 触发词 | 说明 |
|------|--------|------|
| **记录轨迹** | 执行 Command 时自动触发 | 在 `.ai/harness-trace/` 写入本次执行的 JSONL 轨迹文件 |
| **追加 Phase 事件** | Phase 切换时 | 读取 `.ai/harness-trace/.preflight_meta.json`，追加 phase_events 记录 |
| **追加 Retry 事件** | Retry Loop 触发时 | 记录重试次数、失败原因、涉及组件 |
| **查询轨迹** | 查看轨迹、查看 AHE 数据 | 列出 `.ai/harness-trace/` 下所有轨迹文件及摘要 |
| **轨迹详情** | 查看某条轨迹 | 读取并格式化展示指定轨迹文件内容 |

---

## 1. 记录轨迹（自动触发）

Command 框架在 Pre-flight 阶段已初始化 `.ai/harness-trace/.preflight_meta.json`。Observer Skill 在 Command 执行完毕后消费该文件，生成完整轨迹。

**执行时机**：Command 执行完毕（Phase 5 最终报告后）

**执行步骤**：

```bash
# Step 1: 读取 preflight_meta.json
META_FILE=".ai/harness-trace/.preflight_meta.json"
TRACE_DIR=".ai/harness-trace"

if [ ! -f "$META_FILE" ]; then
  echo "No AHE trace found for this run."
  exit 0
fi

TRACE_ID=$(python3 -c "import json; print(json.load(open('$META_FILE'))['trace_id'])")
COMMAND=$(python3 -c "import json; print(json.load(open('$META_FILE'))['command'])")
MODULE=$(python3 -c "import json; print(json.load(open('$META_FILE'))['module'])")
BRANCH=$(python3 -c "import json; print(json.load(open('$META_FILE'))['branch'])")
```

**Step 2: 从各 File Contract 收集 VERDICT 数据**

```bash
# implement 轨迹
if [ "$COMMAND" = "implement" ]; then
  CONTRACT_DIR=".ai/implement/$MODULE/$BRANCH"
  
  # 提取各 Phase VERDICT（从最终报告或契约文件）
  PHASE0_VERDICT=$(grep -o "Phase 0.*VERDICT.*" "$CONTRACT_DIR"/task_card.json 2>/dev/null || echo "unknown")
  REVIEW_FB="$CONTRACT_DIR/review_feedback.md"
  if [ -f "$REVIEW_FB" ]; then
    GAN_VERDICT=$(grep "VERDICT:" "$REVIEW_FB" | head -1)
  fi
  UNIT_TEST_RES="$CONTRACT_DIR/unit_test_results.md"
  if [ -f "$UNIT_TEST_RES" ]; then
    UNIT_VERDICT=$(grep "VERDICT:" "$UNIT_TEST_RES" | head -1)
  fi
fi

# refactor 轨迹
if [ "$COMMAND" = "refactor" ]; then
  REFACTOR_ID=$(python3 -c "import json; m=json.load(open('$META_FILE')); print(m.get('refactor_id',''))")
  CONTRACT_DIR=".ai/refactor/$REFACTOR_ID"
fi

# fix 轨迹
if [ "$COMMAND" = "fix" ]; then
  FIX_ID=$(python3 -c "import json; m=json.load(open('$META_FILE')); print(m.get('fix_id',''))")
  CONTRACT_DIR=".ai/fix/$FIX_ID"
fi
```

**Step 3: 构建轨迹 JSON 并写入**

```bash
# 生成轨迹 JSONL
python3 << 'EOF'
import json, time, uuid
from pathlib import Path

meta = json.load(open('.ai/harness-trace/.preflight_meta.json'))
trace = {
    "trace_id": meta["trace_id"],
    "command": meta["command"],
    "module": meta["module"],
    "branch": meta["branch"],
    "mode": meta.get("mode", "full"),
    "preflight_at": meta["preflight_at"],
    "preflight_done": meta.get("preflight_done", False),
    "duration_seconds": meta.get("total_duration_sec", 0),
    "components": [],
    "phases": meta.get("phase_events", []),
    "verdicts": meta.get("verdicts", []),
    "retry_count": meta.get("total_retry_count", 0),
    "root_cause_analysis": {
        "performed": False,
        "failed_phases": [],
        "rca_by_phase": {}
    },
    "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
}

output_path = f".ai/harness-trace/{trace['trace_id']}_{trace['command']}_{trace['module']}_{trace['branch']}.jsonl"
with open(output_path, "w") as f:
    f.write(json.dumps(trace, ensure_ascii=False) + "\n")

print(f"TRACE_WRITTEN:{output_path}")
EOF
```

**Step 4: 清理临时文件**

```bash
rm -f .ai/harness-trace/.preflight_meta.json
```

---

## 2. 追加 Phase 事件（Command 框架调用）

Command 框架在各 Phase 开始时调用 Observer Skill，追加 phase_events：

```bash
python3 << EOF
import json, time

meta_path = ".ai/harness-trace/.preflight_meta.json"
if not Path(meta_path).exists():
    print("NO_TRACE_SESSION")
    exit(0)

with open(meta_path) as f:
    meta = json.load(f)

meta.setdefault("phase_events", []).append({
    "phase": "$PHASE_NAME",
    "event": "phase_started",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
})

with open(meta_path, "w") as f:
    json.dump(meta, f, indent=2)

print(f"EVENT_APPENDED:{PHASE_NAME}")
EOF
```

---

## 3. 追加 Retry 事件

每次 Retry Loop 触发时：

```bash
python3 << EOF
import json, time

meta_path = ".ai/harness-trace/.preflight_meta.json"
with open(meta_path) as f:
    meta = json.load(f)

meta.setdefault("phase_events", []).append({
    "phase": "$PHASE_NAME",
    "event": "retry",
    "retry_count": $RETRY_COUNT,
    "reason": "$REASON",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
})

meta["total_retry_count"] = meta.get("total_retry_count", 0) + 1

with open(meta_path, "w") as f:
    json.dump(meta, f, indent=2)
EOF
```

---

## 4. 查询轨迹列表

**触发词**：查看轨迹、查看 AHE 数据、查看 harness 观测数据

**执行步骤**：

```bash
TRACE_DIR=".ai/harness-trace"

echo "## AHE 轨迹列表"
echo ""

if [ ! -d "$TRACE_DIR" ]; then
  echo "暂无轨迹记录。执行 Command 后会自动记录。"
  exit 0
fi

echo "| 轨迹文件 | Command | Module | Branch | 记录时间 |"
echo "|----------|---------|--------|--------|----------|"

for f in $(ls -t "$TRACE_DIR"/*.jsonl 2>/dev/null | head -20); do
  fname=$(basename "$f")
  # 提取 metadata（不解析完整 JSONL，只取第一行）
  first_line=$(head -1 "$f" 2>/dev/null)
  cmd=$(echo "$first_line" | python3 -c "import json,sys; print(json.load(sys.stdin).get('command','?'))" 2>/dev/null || echo "?")
  mod=$(echo "$first_line" | python3 -c "import json,sys; print(json.load(sys.stdin).get('module','?'))" 2>/dev/null || echo "?")
  br=$(echo "$first_line" | python3 -c "import json,sys; print(json.load(sys.stdin).get('branch','?'))" 2>/dev/null || echo "?")
  ts=$(echo "$first_line" | python3 -c "import json,sys; print(json.load(sys.stdin).get('recorded_at','?'))" 2>/dev/null || echo "?")
  echo "| $fname | $cmd | $mod | $br | $ts |"
done

echo ""
echo "**总计**: $(ls "$TRACE_DIR"/*.jsonl 2>/dev/null | wc -l | tr -d ' ') 条轨迹"
echo ""
echo "触发 `/ahe-analyze` 进行根因分析。"
```

---

## 5. 轨迹详情

**触发词**：查看轨迹详情、某条轨迹内容

```bash
# 从用户消息中提取轨迹文件名
TRACE_FILE=".ai/harness-trace/$TRACE_ID.jsonl"

if [ ! -f "$TRACE_FILE" ]; then
  echo "轨迹文件不存在：$TRACE_FILE"
  exit 0
fi

python3 -c "
import json
with open('$TRACE_FILE') as f:
    trace = json.loads(f.readline())

print('## AHE 轨迹详情')
print()
print(f'**Trace ID**: {trace[\"trace_id\"]}')
print(f'**Command**: {trace[\"command\"]}')
print(f'**Module/Branch**: {trace[\"module\"]} / {trace[\"branch\"]}')
print(f'**Mode**: {trace.get(\"mode\", \"full\")}')
print(f'**Duration**: {trace.get(\"duration_seconds\", 0):.2f}s')
print(f'**Retry Count**: {trace.get(\"retry_count\", 0)}')
print()
print('### Phase Events')
for e in trace.get('phase_events', []):
    print(f'  - [{e[\"phase\"]}] {e[\"event\"]} @ {e[\"timestamp\"]}')
print()
print('### Verdicts')
for v in trace.get('verdicts', []):
    print(f'  - {v}')
"
```

---

*AHE Observer 是 fast-harness AHE 框架的被动观测组件，由 Command 框架自动调用，无需用户显式触发。*
