#!/usr/bin/env bash
# ============================================================================
# fast-harness 一键安装脚本
#
# 基于 Anthropic Harness Design 的 Generator-Evaluator 多 Agent 协作开发套件
# 支持 Cursor 和 Claude Code 两种 AI IDE
#
# 用法:
#   curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash
#   curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --platform cursor
#   curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --platform claude
#   curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --dir my-plugin
#
# 注：使用 jsDelivr CDN 可避免 raw.githubusercontent.com 的缓存问题
# ============================================================================

set -euo pipefail

# ================================ 配置 ================================
REPO_URL="https://github.com/jindon1020/fast-harness.git"
DEFAULT_PLUGIN_DIR="fast-harness"
BRANCH="main"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
skip()  { echo -e "${YELLOW}[SKIP]${NC} $* (已存在，不覆盖)"; }

# ================================ 参数解析 ================================
PLATFORM=""
PLUGIN_DIR="$DEFAULT_PLUGIN_DIR"
PROJECT_DIR="$(pwd)"
SKIP_AGENTS_MD=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --platform)
            PLATFORM="$2"; shift 2 ;;
        --dir)
            PLUGIN_DIR="$2"; shift 2 ;;
        --project)
            PROJECT_DIR="$2"; shift 2 ;;
        --skip-agents)
            SKIP_AGENTS_MD=true; shift ;;
        --force)
            FORCE=true; SKIP_AGENTS_MD=true; shift ;;
        -h|--help)
            echo "用法: install.sh [选项]"
            echo ""
            echo "选项:"
            echo "  --platform <cursor|claude|both>  指定 IDE 平台（默认: 自动检测）"
            echo "  --dir <name>                     插件目录名（默认: fast-harness）"
            echo "  --project <path>                 项目根目录（默认: 当前目录）"
            echo "  --skip-agents                    跳过 AGENTS.md 生成"
            echo "  --force                          强制更新插件文件（覆盖已有，保留 .local/ 和 project-context.md）"
            echo "  -h, --help                       显示帮助"
            exit 0 ;;
        *)
            err "未知参数: $1"; exit 1 ;;
    esac
done

# ================================ 平台检测 ================================
detect_platform() {
    local has_cursor=false
    local has_claude=false

    # 检测 Cursor
    if [[ -d "$PROJECT_DIR/.cursor" ]] || command -v cursor &>/dev/null; then
        has_cursor=true
    fi

    # 检测 Claude Code
    if [[ -d "$PROJECT_DIR/.claude" ]] || command -v claude &>/dev/null; then
        has_claude=true
    fi

    if $has_cursor && $has_claude; then
        echo "both"
    elif $has_cursor; then
        echo "cursor"
    elif $has_claude; then
        echo "claude"
    else
        echo "both"
    fi
}

if [[ -z "$PLATFORM" ]]; then
    PLATFORM="$(detect_platform)"
    info "自动检测到平台: $PLATFORM"
fi

# ================================ 前置检查 ================================
if ! command -v git &>/dev/null; then
    err "需要 git，请先安装"
    exit 1
fi

if [[ ! -d "$PROJECT_DIR" ]]; then
    err "项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         fast-harness 安装程序                        ║"
echo "║  Generator-Evaluator 多 Agent 协作开发套件           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
info "项目路径: $PROJECT_DIR"
info "插件目录: $PLUGIN_DIR"
info "目标平台: $PLATFORM"
echo ""

# ================================ 下载插件 ================================
TEMP_DIR="$(mktemp -d)"
trap "rm -rf $TEMP_DIR" EXIT

info "正在下载 fast-harness..."
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TEMP_DIR/fast-harness" 2>/dev/null || {
    # 如果 main 分支不存在，尝试 master
    git clone --depth 1 "$REPO_URL" "$TEMP_DIR/fast-harness" 2>/dev/null || {
        err "无法克隆仓库: $REPO_URL"
        exit 1
    }
}
ok "下载完成"

# ================================ 复制函数 ================================
# 安全复制（不覆盖已有文件）
safe_copy_file() {
    local src="$1"
    local dst="$2"

    if [[ -f "$dst" ]]; then
        skip "$dst"
        return 1
    fi

    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    ok "创建: $dst"
    return 0
}

# 强制复制（覆盖已有文件）
force_copy_file() {
    local src="$1"
    local dst="$2"

    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    ok "更新: $dst"
    return 0
}

# 根据 FORCE 标志选择复制策略
copy_file() {
    if $FORCE; then
        force_copy_file "$1" "$2"
    else
        safe_copy_file "$1" "$2"
    fi
}

safe_copy_dir() {
    local src="$1"
    local dst="$2"

    if [[ ! -d "$src" ]]; then
        return
    fi

    find "$src" -type f | while read -r file; do
        local rel="${file#$src/}"
        # --force 时跳过 project-context.md（用户已自定义的配置）
        if $FORCE && [[ "$rel" == "project-context.md" ]]; then
            skip "$dst/$rel (用户自定义配置，跳过)"
            continue
        fi
        copy_file "$file" "$dst/$rel"
    done
}

# 追加内容到文件（不重复）
safe_append() {
    local file="$1"
    local marker="$2"
    local content="$3"

    if [[ -f "$file" ]] && grep -qF "$marker" "$file" 2>/dev/null; then
        skip "内容已存在于 $file 中 ($marker)"
        return
    fi

    mkdir -p "$(dirname "$file")"
    echo "" >> "$file"
    echo "$content" >> "$file"
    ok "追加内容到: $file"
}

# ================================ 安装插件文件 ================================
info "安装插件文件到 $PLUGIN_DIR/ ..."

# 复制插件核心文件
safe_copy_dir "$TEMP_DIR/fast-harness/plugin" "$PROJECT_DIR/$PLUGIN_DIR"

# 复制文档
mkdir -p "$PROJECT_DIR/$PLUGIN_DIR/docs"
copy_file "$TEMP_DIR/fast-harness/docs/guide.md" "$PROJECT_DIR/$PLUGIN_DIR/docs/guide.md"

# 复制图片
if [[ -d "$TEMP_DIR/fast-harness/images" ]]; then
    mkdir -p "$PROJECT_DIR/$PLUGIN_DIR/docs/images"
    for img in "$TEMP_DIR/fast-harness/images/"*.png; do
        [[ -f "$img" ]] && copy_file "$img" "$PROJECT_DIR/$PLUGIN_DIR/docs/images/$(basename "$img")"
    done
fi

echo ""

# ================================ 平台特定配置 ================================

# ---------- Claude Code 配置 ----------
install_claude() {
    info "配置 Claude Code 环境..."

    # .claude-plugin/plugin.json 已随插件目录复制
    # 确保 .claude-plugin 目录存在于插件根目录
    if [[ -f "$PROJECT_DIR/$PLUGIN_DIR/.claude-plugin/plugin.json" ]]; then
        ok "Claude 插件清单已就绪: $PLUGIN_DIR/.claude-plugin/plugin.json"
    fi

    # 复制 Hooks → .claude/hooks/
    if [[ -d "$PROJECT_DIR/$PLUGIN_DIR/hooks" ]]; then
        mkdir -p "$PROJECT_DIR/.claude/hooks"
        for hook_file in "$PROJECT_DIR/$PLUGIN_DIR/hooks/"*.sh; do
            [[ -f "$hook_file" ]] && copy_file "$hook_file" "$PROJECT_DIR/.claude/hooks/$(basename "$hook_file")"
        done
        chmod +x "$PROJECT_DIR/.claude/hooks/"*.sh 2>/dev/null || true
    fi

    # 配置 .claude/settings.json 中的 hooks
    local settings_file="$PROJECT_DIR/.claude/settings.json"
    local archive_hook_cmd="bash \$CLAUDE_PROJECT_DIR/.claude/hooks/archive-to-agents.sh"
    if [[ -f "$settings_file" ]]; then
        if grep -qF "archive-to-agents" "$settings_file" 2>/dev/null; then
            skip "$settings_file (archive hook 已配置)"
        elif command -v python3 &>/dev/null; then
            # 用 python3 安全合并 hooks 到已有 settings.json
            python3 -c "
import json, sys
try:
    with open('$settings_file', 'r') as f:
        data = json.load(f)
except:
    data = {}
hooks = data.setdefault('hooks', {})
stop = hooks.setdefault('Stop', [])
stop.append({
    'matcher': '',
    'hooks': [{'type': 'command', 'command': '$archive_hook_cmd'}]
})
with open('$settings_file', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
" && ok "合并 hook 到: $settings_file" || warn "无法自动合并 hooks，请手动添加 Stop hook 到 $settings_file"
        else
            warn "settings.json 已存在且无 python3，请手动将 archive hook 添加到 $settings_file 的 hooks.Stop 中"
        fi
    else
        mkdir -p "$PROJECT_DIR/.claude"
        cat > "$settings_file" << SETTINGSJSON
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "$archive_hook_cmd"
          }
        ]
      }
    ]
  }
}
SETTINGSJSON
        ok "创建: $settings_file"
    fi

    # 创建/更新 .claude/rules 规则文件
    local rule_file="$PROJECT_DIR/.claude/rules/fast-harness.mdc"
    if $FORCE || [[ ! -f "$rule_file" ]]; then
        mkdir -p "$PROJECT_DIR/.claude/rules"
        cat > "$rule_file" << 'MDRULE'
---
description: fast-harness 开发套件规则
globs:
alwaysApply: true
---

# fast-harness 开发套件

本项目已安装 fast-harness 多 Agent 协作开发套件。

## 按需读取原则

收到 `/implement`、`/fix`、`/refactor`、`/modify` 命令时，按以下规则加载：
1. 读取对应的 command 文件获取流水线规范
2. 由 command 按需调度 agent（Sub-agent 方式启动）
3. 不要预加载所有 agent 指令

## 命令入口

| 命令 | 用途 | 规范文件 |
|------|------|----------|
| `/implement` | 端到端需求实现 | `fast-harness/commands/implement-command.md` |
| `/fix` | Bug 修复闭环 | `fast-harness/commands/fix-command.md` |
| `/refactor` | 批量代码重构 | `fast-harness/commands/refactor-command.md` |
| `/modify` | 存量代码精准修改 | `fast-harness/commands/modify-command.md` |

## 历史上下文

流水线执行后，hook 脚本会自动将 `.ai/` 下的过程文件归档到 `AGENTS.md`。
执行命令前应检查 `AGENTS.md` 的「流水线执行归档」章节，复用历史设计文档和审查经验。

## 编码规约

- 所有代码注释使用**中文**
- git commit message 使用**中文**，格式：`<类型>: <简短描述>`
- 遇到歧义**必须停下询问**，禁止猜测
MDRULE
        ok "创建: $rule_file"
    else
        skip "$rule_file"
    fi
}

# ---------- Cursor 配置 ----------
install_cursor() {
    info "配置 Cursor 环境..."

    # 复制 Agents → .cursor/agents/
    if [[ -d "$PROJECT_DIR/$PLUGIN_DIR/agents" ]]; then
        mkdir -p "$PROJECT_DIR/.cursor/agents"
        for agent_file in "$PROJECT_DIR/$PLUGIN_DIR/agents/"*.md; do
            [[ -f "$agent_file" ]] && copy_file "$agent_file" "$PROJECT_DIR/.cursor/agents/$(basename "$agent_file")"
        done
    fi

    # 复制 Skills → .cursor/skills/
    if [[ -d "$PROJECT_DIR/$PLUGIN_DIR/skills" ]]; then
        safe_copy_dir "$PROJECT_DIR/$PLUGIN_DIR/skills" "$PROJECT_DIR/.cursor/skills"
    fi

    # 复制 Commands → .cursor/commands/（去掉 -command 后缀使 /implement 生效）
    if [[ -d "$PROJECT_DIR/$PLUGIN_DIR/commands" ]]; then
        mkdir -p "$PROJECT_DIR/.cursor/commands"
        for cmd_file in "$PROJECT_DIR/$PLUGIN_DIR/commands/"*-command.md; do
            [[ -f "$cmd_file" ]] || continue
            local base
            base="$(basename "$cmd_file" | sed 's/-command\.md$/.md/')"
            copy_file "$cmd_file" "$PROJECT_DIR/.cursor/commands/$base"
        done
    fi

    # 复制 Hooks → .cursor/hooks/
    if [[ -d "$PROJECT_DIR/$PLUGIN_DIR/hooks" ]]; then
        mkdir -p "$PROJECT_DIR/.cursor/hooks"
        for hook_file in "$PROJECT_DIR/$PLUGIN_DIR/hooks/"*.sh; do
            [[ -f "$hook_file" ]] && copy_file "$hook_file" "$PROJECT_DIR/.cursor/hooks/$(basename "$hook_file")"
        done
        chmod +x "$PROJECT_DIR/.cursor/hooks/"*.sh 2>/dev/null || true
    fi

    # 创建/更新 .cursor/hooks.json
    local hooks_json="$PROJECT_DIR/.cursor/hooks.json"
    local archive_hook=".cursor/hooks/archive-to-agents.sh"
    if [[ -f "$hooks_json" ]]; then
        if ! grep -qF "$archive_hook" "$hooks_json" 2>/dev/null; then
            warn "hooks.json 已存在，请手动将以下 hook 添加到 stop 事件中:"
            echo "  {\"command\": \"$archive_hook\"}"
        else
            skip "$hooks_json (archive hook 已配置)"
        fi
    else
        cat > "$hooks_json" << HOOKJSON
{
  "version": 1,
  "hooks": {
    "stop": [
      {
        "command": "$archive_hook"
      }
    ]
  }
}
HOOKJSON
        ok "创建: $hooks_json"
    fi

    # 创建/更新 .cursor/rules 规则文件
    local rule_file="$PROJECT_DIR/.cursor/rules/fast-harness.mdc"
    if $FORCE || [[ ! -f "$rule_file" ]]; then
        mkdir -p "$PROJECT_DIR/.cursor/rules"
        cat > "$rule_file" << 'MDRULE'
---
description: fast-harness 开发套件规则
globs:
alwaysApply: true
---

# fast-harness 开发套件

本项目已安装 fast-harness 多 Agent 协作开发套件。

## 按需读取原则

收到 `/implement`、`/fix`、`/refactor`、`/modify` 命令时，按以下规则加载：
1. 读取对应的 command 文件获取流水线规范
2. 由 command 按需调度 agent（Sub-agent 方式启动）
3. 不要预加载所有 agent 指令

## 命令入口

| 命令 | 用途 | 规范文件 |
|------|------|----------|
| `/implement` | 端到端需求实现 | `fast-harness/commands/implement-command.md` |
| `/fix` | Bug 修复闭环 | `fast-harness/commands/fix-command.md` |
| `/refactor` | 批量代码重构 | `fast-harness/commands/refactor-command.md` |
| `/modify` | 存量代码精准修改 | `fast-harness/commands/modify-command.md` |

## 历史上下文

流水线执行后，hook 脚本会自动将 `.ai/` 下的过程文件归档到 `AGENTS.md`。
执行命令前应检查 `AGENTS.md` 的「流水线执行归档」章节，复用历史设计文档和审查经验。

## 编码规约

- 所有代码注释使用**中文**
- git commit message 使用**中文**，格式：`<类型>: <简短描述>`
- 遇到歧义**必须停下询问**，禁止猜测
MDRULE
        ok "创建: $rule_file"
    else
        skip "$rule_file"
    fi
}

case "$PLATFORM" in
    cursor)
        install_cursor ;;
    claude)
        install_claude ;;
    both)
        install_cursor
        echo ""
        install_claude ;;
    *)
        err "无效平台: $PLATFORM（cursor/claude/both）"
        exit 1 ;;
esac

echo ""

# ================================ AGENTS.md ================================
if [[ "$SKIP_AGENTS_MD" == false ]]; then
    info "配置 AGENTS.md..."

    AGENTS_MARKER="## 开发套件（fast-harness）"

    AGENTS_CONTENT=$(cat << AGENTSEOF
## 开发套件（fast-harness）

本项目配有基于 [Anthropic Harness Design](https://www.anthropic.com/engineering/harness-design-long-running-apps) 的 Generator-Evaluator 分离多 Agent 协作流水线。

> **按需读取原则**: 收到对应命令时才读取详细规范，不要预加载所有 agent 指令。

### Commands — 流水线编排

| 命令 | 用途 | 触发条件 | 详细规范 |
|------|------|----------|----------|
| \`/implement\` | 端到端需求实现 | 用户描述新功能需求 | [$PLUGIN_DIR/commands/implement-command.md]($PLUGIN_DIR/commands/implement-command.md) |
| \`/fix\` | Bug 修复闭环 | 测试 FAIL / 审查 Critical / 线上异常 / 手动报告 | [$PLUGIN_DIR/commands/fix-command.md]($PLUGIN_DIR/commands/fix-command.md) |
| \`/refactor\` | 批量代码重构 | 技术债清理 / 审查 Improvements 积压 | [$PLUGIN_DIR/commands/refactor-command.md]($PLUGIN_DIR/commands/refactor-command.md) |
| \`/modify\` | 存量代码精准修改 | 修改现有功能 / 调整业务逻辑 / 接口改造 | [$PLUGIN_DIR/commands/modify-command.md]($PLUGIN_DIR/commands/modify-command.md) |

> **⚡ 快速模式**: 四个命令均支持 \`fast=true\` 可选参数，跳过 GAN 对抗审查/质量审计环节，节省 30%-40% Token。

### Agents — 由 Command 按需调度

| Agent | 角色 | 调度方 | 写权限 |
|-------|------|--------|--------|
| \`requirement-design-agent\` | Planner — 需求转 task_card.json | implement | 是 |
| \`generator-agent\` | Generator — 按任务卡编码 | implement | 是 |
| \`code-reviewer-agent\` | 六维度代码审查 | implement / fix / refactor | 否 |
| \`security-reviewer-agent\` | 安全漏洞审查 | implement / fix / refactor | 否 |
| \`api-test-agent\` | 连接本地 DB 生成单元测试 | implement / fix / refactor | 是 |
| \`tester-gen-agent\` | 解析 xmind 生成集成测试 | implement | 是 |
| \`test-runner-agent\` | 执行 pytest 输出 VERDICT | implement / fix / refactor | 否 |
| \`debugger-agent\` | 本地修复 / 线上排查 | implement / fix | 是 |
| \`monitor-agent\` | K8s + Prometheus 只读监控 | 独立触发 | 否 |

Agent 详细规范位于 \`$PLUGIN_DIR/agents/{agent-name}.md\`，由 Command 启动 Sub-agent 时自动加载。

### Skills — 运维能力底座

| Skill | 能力 | 触发词 |
|-------|------|--------|
| \`dev-mysql-bastion-query\` | 经堡垒机 SSH 隧道只读查询开发环境 MySQL | 查库、对照数据、堡垒机 |
| \`kubectl-readonly\` | K8s Pod/Deployment/Events 只读查询 | 查 Pod、K8s 状态 |
| \`k8s-monitor-full\` | K8s + Loki + Prometheus 一体化诊断 | 排障、查监控 |
| \`loki-log-keyword-search\` | Loki 日志关键词/request_id 检索 | 查日志、request_id |
| \`prometheus-metrics-query\` | ARMS Prometheus 指标查询 | QPS、错误率、延迟、CPU |

所有 Skill 均为**只读操作**，Skill 详细规范位于 \`$PLUGIN_DIR/skills/{skill-name}/SKILL.md\`。

### 文件契约体系

Agent 间通过文件契约通信，实现 Context Reset（不依赖对话历史）：

| 目录 | 用途 | 核心文件 |
|------|------|----------|
| \`.ai/implement/{sprint}_{module}/\` | implement 流水线 | \`task_card.json\`、\`changed_files.txt\`、\`review_feedback.md\` |
| \`.ai/fix/{fix_id}/\` | fix 流水线 | \`bug_report.md\`、\`diagnosis.md\`、\`changed_files.txt\` |
| \`.ai/refactor/{refactor_id}/\` | refactor 流水线 | \`refactor_plan.md\`、\`baseline_snapshot.md\`、\`changed_files.txt\` |

### 不适用场景

以下场景**不需要**启动流水线，直接编码即可：

| 场景 | 原因 | 建议操作 |
|------|------|----------|
| 单行 bug 修复 / 纯 typo | 改动极小，流水线开销不值得 | 直接改 + 手动验证 |
| 纯配置变更（YAML/环境变量） | 无业务逻辑变更 | 直接改 + 确认配置生效 |
| 只改注释或文档 | 无行为影响 | 直接改 |
| 修改现有接口的返回值新增可选字段 | 向后兼容的小改动 | 直接改 + 补充测试 |

### 流水线执行归档

> 以下为流水线命令执行后自动归档的过程文件索引。查阅历史设计文档、技术方案、审查反馈等，直接读取对应路径下的文件。
>
> **使用方式**：执行 \`/implement\`、\`/fix\`、\`/refactor\`、\`/modify\` 命令前，先查阅此章节：
> - 查找**同模块**的历史记录，复用已有设计文档（\`task_card.json\` / \`change_card.json\`）
> - 参考历史 \`review_feedback.md\` 审查意见，主动规避已知问题
> - 阅读历史 \`diagnosis.md\` 了解已修复 Bug 的根因，避免回归
> - 复用 \`tests/{branch}/\` 下的测试用例和数据，只生成增量测试

| 时间 | 命令 | Pipeline ID | 路径 | 核心文件 |
|------|------|-------------|------|----------|
AGENTSEOF
)

    if [[ -f "$PROJECT_DIR/AGENTS.md" ]]; then
        # 文件已存在，追加内容（不覆盖）
        safe_append "$PROJECT_DIR/AGENTS.md" "$AGENTS_MARKER" "$AGENTS_CONTENT"
    else
        # 文件不存在，创建新的
        cat > "$PROJECT_DIR/AGENTS.md" << HEADEREOF
# AGENTS.md — AI 行为配置

> 本文件是 AI 进入项目时的认知入口。

---

$AGENTS_CONTENT
HEADEREOF
        ok "创建: AGENTS.md"
    fi
fi

echo ""

# ================================ .gitignore ================================
info "检查 .gitignore..."

GITIGNORE_ENTRIES=(
    ".ai/"
    "*.env"
    "id_rsa"
    "kubeconfig-readonly"
)

if [[ -f "$PROJECT_DIR/.gitignore" ]]; then
    for entry in "${GITIGNORE_ENTRIES[@]}"; do
        if ! grep -qxF "$entry" "$PROJECT_DIR/.gitignore" 2>/dev/null; then
            echo "$entry" >> "$PROJECT_DIR/.gitignore"
            ok "追加到 .gitignore: $entry"
        fi
    done
else
    printf '%s\n' "${GITIGNORE_ENTRIES[@]}" > "$PROJECT_DIR/.gitignore"
    ok "创建: .gitignore"
fi

# ================================ 设置可执行权限 ================================
chmod +x "$PROJECT_DIR/$PLUGIN_DIR/configure.sh" 2>/dev/null || true

# ================================ 完成 ================================
echo ""
if $FORCE; then
echo "╔══════════════════════════════════════════════════════╗"
echo "║                   更新完成！                          ║"
echo "╚══════════════════════════════════════════════════════╝"
else
echo "╔══════════════════════════════════════════════════════╗"
echo "║                   安装完成！                          ║"
echo "╚══════════════════════════════════════════════════════╝"
fi
echo ""
echo "已安装的文件："
echo "  📁 $PLUGIN_DIR/                 # 插件核心文件"
echo "  📁 $PLUGIN_DIR/commands/        # 4 个流水线命令（规范原文）"
echo "  📁 $PLUGIN_DIR/agents/          # 9 个专职 Agent（规范原文）"
echo "  📁 $PLUGIN_DIR/skills/          # 5 个运维 Skill（规范原文）"
echo "  📁 $PLUGIN_DIR/hooks/           # Hook 脚本（归档等）"
echo "  📁 $PLUGIN_DIR/docs/            # 完整使用文档"
echo "  📄 AGENTS.md                     # AI 认知入口 + 历史归档索引"

case "$PLATFORM" in
    cursor)
        echo "  📁 .cursor/agents/              # Cursor 可识别的 Agent"
        echo "  📁 .cursor/skills/              # Cursor 可识别的 Skill"
        echo "  📁 .cursor/commands/            # Cursor 可识别的命令（/implement 等）"
        echo "  📁 .cursor/hooks/               # Cursor Hook 脚本"
        echo "  📄 .cursor/hooks.json            # Hook 事件配置"
        echo "  📄 .cursor/rules/fast-harness.mdc" ;;
    claude)
        echo "  📁 .claude/hooks/               # Claude Code Hook 脚本"
        echo "  📄 .claude/settings.json         # Claude Code Hook 配置"
        echo "  📄 .claude/rules/fast-harness.mdc" ;;
    both)
        echo "  📁 .cursor/agents/              # Cursor 可识别的 Agent"
        echo "  📁 .cursor/skills/              # Cursor 可识别的 Skill"
        echo "  📁 .cursor/commands/            # Cursor 可识别的命令（/implement 等）"
        echo "  📁 .cursor/hooks/               # Cursor Hook 脚本"
        echo "  📄 .cursor/hooks.json            # Cursor Hook 事件配置"
        echo "  📄 .cursor/rules/fast-harness.mdc"
        echo "  📁 .claude/hooks/               # Claude Code Hook 脚本"
        echo "  📄 .claude/settings.json         # Claude Code Hook 配置"
        echo "  📄 .claude/rules/fast-harness.mdc" ;;
esac

echo ""
echo "下一步："
echo "  1. 配置项目上下文（二选一）:"
echo "     方式 A: 运行 $PLUGIN_DIR/configure.sh 交互式配置"
echo "     方式 B: 手动编辑 commands/*.md 中的 {{占位符}}"
echo ""
echo "  2. 查看完整使用说明:"
echo "     cat $PLUGIN_DIR/docs/guide.md"
echo ""
echo "  3. 开始使用:"
echo "     /implement 我需要实现 XXX 功能"
echo "     /fix 线上报 500 错误 request_id=abc-123"
echo "     /refactor 把 XXX 模块的重复代码抽取为公共函数"
echo ""
