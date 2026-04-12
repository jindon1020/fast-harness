#!/usr/bin/env bash
# ============================================================================
# fast-harness hook: 流水线执行归档
#
# 触发事件: stop (Cursor agent 执行结束后)
# 功能: 扫描 .ai/ 下的流水线过程文件，将新增目录索引追加到 AGENTS.md
# 幂等: 已归档的目录不会重复写入
# ============================================================================

cat > /dev/null

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
AI_DIR="$PROJECT_ROOT/.ai"
AGENTS_FILE="$PROJECT_ROOT/AGENTS.md"

[[ -d "$AI_DIR" ]] || exit 0
[[ -f "$AGENTS_FILE" ]] || exit 0

ARCHIVE_MARKER="## 流水线执行归档"

if ! grep -qF "$ARCHIVE_MARKER" "$AGENTS_FILE" 2>/dev/null; then
    cat >> "$AGENTS_FILE" << 'SECTION'

## 流水线执行归档

> 以下为流水线命令执行后自动归档的过程文件索引。查阅历史设计文档、技术方案、审查反馈等，直接读取对应路径下的文件。

| 时间 | 命令 | Pipeline ID | 路径 | 核心文件 |
|------|------|-------------|------|----------|
SECTION
fi

for cmd_type in implement fix refactor modify; do
    cmd_dir="$AI_DIR/$cmd_type"
    [[ -d "$cmd_dir" ]] || continue

    for pipeline_dir in "$cmd_dir"/*/; do
        [[ -d "$pipeline_dir" ]] || continue
        pipeline_id="$(basename "$pipeline_dir")"
        rel_path=".ai/$cmd_type/$pipeline_id/"

        grep -qF "$rel_path" "$AGENTS_FILE" 2>/dev/null && continue

        core_files="$(ls -1 "$pipeline_dir" 2>/dev/null \
            | grep -E '\.(json|md|txt)$' \
            | head -8 \
            | tr '\n' ',' \
            | sed 's/,$//' \
            | sed 's/,/, /g')"
        [[ -z "$core_files" ]] && continue

        timestamp="$(date '+%Y-%m-%d %H:%M')"
        echo "| $timestamp | \`$cmd_type\` | \`$pipeline_id\` | \`$rel_path\` | $core_files |" >> "$AGENTS_FILE"
    done
done

exit 0
