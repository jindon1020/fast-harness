# AHE Evo Skill

## Purpose

AHE 演化引擎——接收 AHE Analyzer 生成的 Edit Candidate，执行 **harness 组件的自动化改动**，并通过 **A/B Eval** 验证效果。

## What It Does

1. 读取 Analyzer 输出的 patch 方案
2. 验证 patch 语法和安全性（不会破坏框架结构）
3. 应用 patch 到目标文件（Agent prompt / Extension / Skill）
4. 创建 Git branch 存储实验性改动
5. 触发 A/B Eval 在相同测试集上对比新旧 harness
6. 输出报告：pass@1 delta、是否建议合并

## Evo Loop 流程

```
Analyzer 输出 Edit Candidate
        ↓
  [Evo] 验证 patch 安全性
        ↓
  创建实验分支 feat/ahe-evo-{candidate_id}
        ↓
  应用 patch 到目标组件
        ↓
  触发 A/B Eval（同一批任务在新旧 harness 上各跑一次）
        ↓
  比较 pass@1：
    - delta > 0 → 建议合并
    - delta ≤ 0 → 丢弃，保留 candidate 记录
    - 统计显著 → 自动合并
    - 统计不显著 → 人工决策
```

## A/B Eval 设计

### 测试集

使用 `.ai/benchmarks/ahe-eval-set.jsonl`——从历史轨迹中筛选出的**代表性任务集**：
- 覆盖主要 command 类型（implement / refactor / fix）
- 覆盖主要 module
- 每个 category 至少 5 个任务

### 评估指标

| 指标 | 说明 |
|------|------|
| pass@1 | 第一次尝试通过率 |
| pass@3 | 三次尝试内通过率 |
| avg_retry | 平均重试次数 |
| avg_duration | 平均执行时长 |

### 统计显著性

使用 **McNemar 检验** 判断新旧 harness 差异是否显著：
- p < 0.05 → 差异显著
- p ≥ 0.05 → 差异不显著，建议人工判断

## Patch 安全性检查

在应用 patch 前，必须验证：

```bash
# 1. 检查 patch 目标文件存在
test -f {target_file} || error "目标文件不存在"

# 2. 检查 patch 格式正确（标准的 diff 格式或 JSON patch）
python3 -c "import json; json.loads('{patch}')" 2>/dev/null || echo "NOT_JSON_PATCH"

# 3. 检查应用后语法正确
python3 -m py_compile {target_file} || error "语法错误，patch 被拒绝"

# 4. 检查不包含恶意内容（敏感路径、rm -rf 等）
echo '{patch}' | rg "rm -rf|/dev/sd|eval\s*\(" && error "危险命令检测，patch 被拒绝"
```

## Usage

```
/ahe-evo apply CAND-001-A   # 应用指定 candidate
/ahe-evo dry-run CAND-001-A # 仅预览，不实际改动
/ahe-evo eval CAND-001-A    # 单独对某个 candidate 做 A/B Eval
/ahe-evo status             # 查看当前实验状态
/ahe-evo rollback           # 回退最近的 Evo 操作
```

## Evo 操作日志

每次 Evo 操作记录到 `.ai/harness-evolution/evo_log.jsonl`：

```jsonl
{"timestamp":"ISO8601","action":"apply|dry-run|eval|rollback","candidate_id":"CAND-001-A","target":"generator-agent.@coding-convention","result":"success|rejected|rolled_back","pass1_delta":+0.05,"statistical_significance":true}
```

---

*This skill is part of the AHE (Agentic Harness Engineering) framework for observability-driven harness evolution.*
