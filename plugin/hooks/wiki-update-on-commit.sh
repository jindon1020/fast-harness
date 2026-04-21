#!/usr/bin/env bash
# ============================================================================
# fast-harness hook: wiki incremental update on git commit
#
# 触发事件: post-commit (git 钩子)
# 功能:   - 检测本次 commit 改动的文件
#         - 尝试 LLM 增量更新受影响的 wiki sections（可选）
#         - 回退到 stale 标记（LLM 不可用时）
# ============================================================================

set -euo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
WIKI_DIR="$PROJECT_ROOT/.wiki"
MANIFEST="$WIKI_DIR/MANIFEST.json"
HOOK_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ----- 安全退出：没有 wiki 目录就什么也不做 -----
[[ -d "$WIKI_DIR" ]] || exit 0
[[ -f "$MANIFEST" ]] || exit 0

# ----- 获取本次 commit 改动的文件列表 -----
# 支持：git diff --name-only HEAD~1 HEAD   （post-commit 时 HEAD 就是刚提交的 commit）
COMMIT_RANGE="${1:-HEAD~1..HEAD}"
CHANGED_FILES=$(git diff --name-only "$COMMIT_RANGE" 2>/dev/null || echo "")

[[ -z "$CHANGED_FILES" ]] && exit 0

echo "[wiki-update] Detected changed files:"
echo "$CHANGED_FILES" | sed 's/^/  - /'

# ----- 决定更新模式 -----
# 模式 A: LLM 增量更新（需要 claude CLI + 已安装 code-wiki-gen skill）
# 模式 B: 仅标记 stale（不需要 LLM，fallback）

ENABLE_LLM_UPDATE="${WIKI_AUTO_LLM_UPDATE:-0}"

if [[ "$ENABLE_LLM_UPDATE" == "1" ]]; then
    echo "[wiki-update] LLM update mode enabled, invoking claude..."

    # 调用 claude CLI 做增量更新，--print 模式无交互
    # 传入 CHANGED_FILES 作为参数
    CHANGED_FILES_CSV=$(echo "$CHANGED_FILES" | tr '\n' ',' | sed 's/,$//')

    if command -v claude &>/dev/null; then
        # 使用 claude 调用 code-wiki-gen skill 的增量更新
        # --print 模式确保无交互、无权限审批
        if claude --print "更新wiki，变更文件: $CHANGED_FILES_CSV" &>/dev/null; then
            echo "[wiki-update] LLM update completed."
            exit 0
        else
            echo "[wiki-update] LLM update failed, falling back to stale marking."
        fi
    else
        echo "[wiki-update] claude CLI not found, falling back to stale marking."
    fi
fi

# ----- 模式 B: 调用 Python 脚本标记 stale -----
echo "[wiki-update] Marking stale sections..."

# 将 CHANGED_FILES 转为数组传给 Python 脚本
CHANGED_FILES_ARRAY=()
while IFS= read -r line; do
    [[ -n "$line" ]] && CHANGED_FILES_ARRAY+=("$line")
done <<< "$CHANGED_FILES"

if python3 "$HOOK_SCRIPT_DIR/mark_stale.py" "${CHANGED_FILES_ARRAY[@]}" \
    --manifest "$MANIFEST" \
    --project-root "$PROJECT_ROOT"; then
    echo "[wiki-update] Stale sections marked successfully."
else
    echo "[wiki-update] mark_stale.py failed (non-critical)."
fi

exit 0
