#!/usr/bin/env bash
# ============================================================================
# fast-harness CDN 缓存清除脚本
#
# 用法: bash purge-cdn.sh
#
# 推送代码到 GitHub 后执行此脚本，强制 jsDelivr 从 GitHub 拉取最新版本
# ============================================================================

set -euo pipefail

REPO="jindon1020/fast-harness"
BRANCH="main"
BASE_URL="https://purge.jsdelivr.net/gh/${REPO}@${BRANCH}"

# purge 接口偶发 HTTP 520/522（CDN 瞬时故障），不因单次失败中断整批
PURGE_FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; }
info() { echo -e "${BLUE}[INFO]${NC} $*"; }

purge_file() {
    local path="$1"
    local result=""
    local attempt max=6
    local wait_sec=2

    for ((attempt = 1; attempt <= max; attempt++)); do
        if result=$(curl -fsSL --connect-timeout 20 --max-time 120 "${BASE_URL}/${path}" 2>/dev/null); then
            break
        fi
        if [[ "$attempt" -lt "$max" ]]; then
            echo -e "${YELLOW}[RETRY]${NC} $path（${attempt}/${max}，purge.jsdelivr 瞬时错误，${wait_sec}s 后重试）"
            sleep "$wait_sec"
            wait_sec=$((wait_sec + 2))
        fi
    done

    if [[ -z "$result" ]]; then
        fail "$path（curl 失败，常见为 HTTP 520/522；属 jsDelivr 侧短暂故障，请数分钟后重试本脚本）"
        PURGE_FAIL=$((PURGE_FAIL + 1))
        return 0
    fi

    local throttled status
    throttled=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); p=list(d['paths'].values())[0]; print(p.get('throttled','?'))" 2>/dev/null || echo "?")
    status=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null || echo "?")

    if [[ "$status" == "finished" && "$throttled" == "False" || "$throttled" == "false" ]]; then
        ok "$path"
    elif [[ "$throttled" == "True" || "$throttled" == "true" ]]; then
        echo -e "${YELLOW}[SKIP]${NC} $path (被限流，稍后重试)"
    else
        fail "$path (status=$status，响应非预期 JSON 时请稍后重试)"
        PURGE_FAIL=$((PURGE_FAIL + 1))
    fi
    return 0
}

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         fast-harness CDN 缓存清除                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
info "仓库: ${REPO}@${BRANCH}"
echo ""

# 安装脚本
info "[ 安装脚本 ]"
purge_file "install.sh"
echo ""

# Commands
info "[ Commands ]"
purge_file "plugin/commands/implement-command.md"
purge_file "plugin/commands/fix-command.md"
purge_file "plugin/commands/refactor-command.md"
purge_file "plugin/commands/modify-command.md"
purge_file "plugin/commands/init-command.md"
purge_file "plugin/commands/test-command.md"
purge_file "plugin/commands/wiki-update-command.md"
echo ""

# Hooks
info "[ Hooks ]"
purge_file "plugin/hooks/archive-to-agents.sh"
purge_file "plugin/hooks/mark_stale.py"
purge_file "plugin/hooks/wiki-update-on-commit.sh"
echo ""

# Agents
info "[ Agents ]"
purge_file "plugin/agents/requirement-design-agent/requirement-design-agent.md"
purge_file "plugin/agents/generator-agent/generator-agent.md"
purge_file "plugin/agents/code-reviewer-agent/code-reviewer-agent.md"
purge_file "plugin/agents/security-reviewer-agent/security-reviewer-agent.md"
purge_file "plugin/agents/unit-test-gen-agent/unit-test-gen-agent.md"
purge_file "plugin/agents/integration-test-gen-agent/integration-test-gen-agent.md"
purge_file "plugin/agents/test-runner-agent/test-runner-agent.md"
purge_file "plugin/agents/debugger-agent/debugger-agent.md"
purge_file "plugin/agents/monitor-agent/monitor-agent.md"
echo ""

# Skills
info "[ Skills ]"
purge_file "plugin/skills/k8s-monitor/SKILL.md"
purge_file "plugin/skills/loki-log-keyword-search/SKILL.md"
purge_file "plugin/skills/prometheus-metrics-query/SKILL.md"
purge_file "plugin/skills/xmind-test-extractor/SKILL.md"
purge_file "plugin/skills/db-connector/SKILL.md"
purge_file "plugin/skills/redis-connector/SKILL.md"
purge_file "plugin/skills/kafka-connector/SKILL.md"
purge_file "plugin/skills/harness-meta-skill/SKILL.md"
purge_file "plugin/skills/api-spec-generator/SKILL.md"
purge_file "plugin/skills/feishu-doc-reader/SKILL.md"
purge_file "plugin/skills/code-wiki-gen/SKILL.md"
echo ""

if [[ "$PURGE_FAIL" -eq 0 ]]; then
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║                   清除完成！                          ║"
    echo "╚══════════════════════════════════════════════════════╝"
else
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  清除未全部成功（失败 ${PURGE_FAIL} 项），请稍后重试脚本   ║"
    echo "╚══════════════════════════════════════════════════════╝"
fi
echo ""
echo "用户现在通过以下命令安装将获取最新代码："
echo "  curl -fsSL https://cdn.jsdelivr.net/gh/${REPO}@${BRANCH}/install.sh | bash"
echo ""

if [[ "$PURGE_FAIL" -gt 0 ]]; then
    exit 1
fi
