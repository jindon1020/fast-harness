---
name: harness-meta-skill
description: fast-harness 扩展点管理元技能。查看所有 Agent 扩展点目录、创建用户扩展文件、管理基础设施配置、查看当前扩展状态。触发词：创建扩展、添加扩展点、查看扩展、扩展点目录、harness 扩展、新增 skill 扩展、管理配置。
---

# fast-harness 扩展点管理元技能

帮助用户管理 fast-harness 框架的扩展点系统：查看可用扩展点、创建扩展文件、管理基础设施配置、查看扩展状态。

---

## 能力一览

| 能力 | 触发词 | 说明 |
|------|--------|------|
| **查看扩展点目录** | 查看扩展点、列出扩展点、extension points | 列出所有 Agent 支持的扩展点 |
| **创建扩展文件** | 创建扩展、添加扩展、新建扩展 | 交互式引导创建扩展 .md 文件 |
| **管理基础设施配置** | 添加配置、管理 infrastructure | 向 infrastructure.json 添加中间件配置 |
| **查看扩展状态** | 查看已有扩展、扩展状态、已安装扩展 | 扫描并报告所有已安装的扩展 |

---

## 1. 查看扩展点目录

扫描所有 Agent 的 .md 文件，提取 Extension Points 信息并汇总展示。

**执行步骤**：

```bash
PLUGIN_DIR="fast-harness"

echo "## fast-harness 扩展点目录"
echo ""

for agent_dir in "$PLUGIN_DIR"/agents/*/; do
  agent_name=$(basename "$agent_dir")
  agent_file="$agent_dir/${agent_name}.md"
  if [ -f "$agent_file" ]; then
    echo "### $agent_name"
    # 提取 Extension Points 表格
    sed -n '/Available Extension Points/,/^---$/p' "$agent_file" | head -20
    echo ""
  fi
done
```

**输出格式**（汇总表）：

| Agent | Extension Point | 阶段 | 说明 |
|---|---|---|---|
| debugger-agent | `@data-source` | B-Step 1~2 | 自定义数据源（Redis/ES/MQ） |
| debugger-agent | `@diagnosis-strategy` | B-Step 3 | 额外诊断策略 |
| debugger-agent | `@fix-validation` | A-Step 4 / B-Step 6 | 自定义修复后验证 |
| generator-agent | `@pre-generation` | Step 1 | 生成前额外检查 |
| generator-agent | `@coding-convention` | Step 2 | 项目编码规范 |
| generator-agent | `@code-template` | Step 2 | 自定义代码模板 |
| code-reviewer-agent | `@review-dimension` | 审查后 | 额外审查维度 |
| code-reviewer-agent | `@project-rule` | 审查中 | 项目审查规则 |
| security-reviewer-agent | `@security-rule` | 审查中 | 项目安全规则 |
| unit-test-gen-agent | `@test-data-source` | 步骤 4 | 自定义测试数据源 |
| unit-test-gen-agent | `@test-pattern` | 步骤 5~6 | 项目测试模式 |
| integration-test-gen-agent | `@test-context` | Step 3 | 测试环境配置 |
| test-runner-agent | `@pre-test` | Phase 1.5 | 测试前置准备 |
| test-runner-agent | `@post-test` | Phase 2.5 | 测试后置处理 |
| monitor-agent | `@metric-source` | 查询阶段 | 自定义监控源 |
| monitor-agent | `@alert-rule` | 告警阶段 | 自定义告警规则 |
| requirement-design-agent | `@design-convention` | Step 2~6 | 项目设计规范 |

---

## 2. 创建扩展文件

交互式引导用户创建扩展 .md 文件。

**Step 1 — 选择目标 Agent**：

调用 `AskQuestion` 让用户选择要扩展的 Agent：

```
请选择要扩展的 Agent：
(A) debugger-agent    (B) generator-agent
(C) code-reviewer-agent    (D) security-reviewer-agent
(E) unit-test-gen-agent    (F) integration-test-gen-agent
(G) test-runner-agent    (H) monitor-agent
(I) requirement-design-agent
```

**Step 2 — 选择扩展点**：

根据选定 Agent 的 Available Extension Points，让用户选择要挂载的扩展点。

**Step 3 — 收集扩展信息**：

| 字段 | 说明 | 示例 |
|------|------|------|
| name | 扩展名称（kebab-case） | `redis-cache-inspector` |
| description | 一句话描述 | `调试时检查 Redis 缓存状态` |
| priority | 执行优先级（默认 10） | `10` |
| requires-config | 依赖的配置段（可选） | `redis.local` |

**Step 4 — 生成文件**：

基于 `fast-harness/agents/_extension-template.md` 模板，填充用户提供的信息，生成扩展文件：

```bash
AGENT="debugger-agent"
EXT_NAME="data-source-redis"
TARGET="fast-harness/agents/$AGENT/extensions/${EXT_NAME}.md"
```

写入文件内容，包含：
1. 完整的 YAML frontmatter（extension-point、name、description、priority、requires-config）
2. 基础的 Markdown 结构（触发条件、执行步骤、命令模板、结果解读）
3. 提示用户填写具体策略内容的占位文字

**Step 5 — 验证**：

确认文件已创建，提示用户编辑具体策略内容。

---

## 3. 管理基础设施配置

帮助用户向 `fast-harness/config/infrastructure.json` 添加新的中间件配置段。

**Step 1 — 检查当前配置**：

```bash
cat fast-harness/config/infrastructure.json | python3 -c "
import json, sys
config = json.load(sys.stdin)
print('当前已配置的中间件：')
for key in config:
    if key.startswith('\$'): continue
    envs = list(config[key].keys())
    print(f'  {key}: {envs}')
"
```

**Step 2 — 选择操作**：

```
(A) 添加新中间件类型（如 mongodb、rabbitmq 等）
(B) 为已有中间件添加新环境（如为 mysql 添加 staging 环境）
(C) 修改已有配置
```

**Step 3 — 收集配置信息**：

根据中间件类型收集必要的连接参数，写入 `infrastructure.json`。

**Step 4 — 验证 JSON 格式**：

```bash
python3 -c "import json; json.load(open('fast-harness/config/infrastructure.json')); print('JSON 格式正确')"
```

---

## 4. 查看扩展状态

扫描所有 Agent 的 `extensions/` 目录，报告已安装扩展的完整清单。

**执行步骤**：

```bash
PLUGIN_DIR="fast-harness"

echo "## fast-harness 扩展状态报告"
echo ""

total=0
for agent_dir in "$PLUGIN_DIR"/agents/*/; do
  agent_name=$(basename "$agent_dir")
  ext_dir="$agent_dir/extensions"
  if [ -d "$ext_dir" ]; then
    files=$(find "$ext_dir" -name "*.md" -not -name "_*" 2>/dev/null)
    if [ -n "$files" ]; then
      count=$(echo "$files" | wc -l | tr -d ' ')
      total=$((total + count))
      echo "### $agent_name ($count 个扩展)"
      for f in $files; do
        fname=$(basename "$f" .md)
        # 提取 frontmatter 中的关键信息
        ext_point=$(grep "^extension-point:" "$f" 2>/dev/null | sed 's/extension-point: *//')
        desc=$(grep "^description:" "$f" 2>/dev/null | sed 's/description: *//')
        echo "  - **$fname** → @$ext_point — $desc"
      done
      echo ""
    fi
  fi
done

if [ "$total" -eq 0 ]; then
  echo "暂无用户扩展。使用「创建扩展」功能添加你的第一个扩展。"
fi

echo ""
echo "**总计**: $total 个扩展"
```

**输出格式**：

```markdown
## fast-harness 扩展状态报告

### debugger-agent (2 个扩展)
  - **data-source-redis** → @data-source — 调试时检查 Redis 缓存状态
  - **diagnosis-strategy-tracing** → @diagnosis-strategy — 链路追踪分析

### generator-agent (1 个扩展)
  - **coding-convention-myproject** → @coding-convention — 项目编码规范

**总计**: 3 个扩展
```

---

## 快速使用示例

### 示例 1：为 debugger-agent 添加 Redis 数据源扩展

```
用户：我想在调试时能查看 Redis 缓存
→ 选择 Agent: debugger-agent
→ 选择扩展点: @data-source
→ 名称: redis-cache-inspector
→ 描述: 调试时检查 Redis 缓存状态排查不一致
→ requires-config: redis.local
→ 生成文件: fast-harness/agents/debugger-agent/extensions/data-source-redis.md
→ 用户编辑具体的 Redis 查询策略
```

### 示例 2：查看当前所有扩展

```
用户：查看已有扩展
→ 执行扩展状态扫描
→ 输出所有 Agent 的扩展清单
```

### 示例 3：为 generator-agent 添加编码规范

```
用户：我想让代码生成遵循我们项目的规范
→ 选择 Agent: generator-agent
→ 选择扩展点: @coding-convention
→ 创建扩展文件，用户填写项目特定的编码约定
```
