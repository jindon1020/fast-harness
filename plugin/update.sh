#!/usr/bin/env bash
# ============================================================================
# fast-harness 一键更新脚本
#
# 用法: bash .ether/update.sh
#
# 从 GitHub 拉取最新版本，强制覆盖更新插件文件。
# 以下内容会被保留（不覆盖）：
#   - project-context.md    （项目上下文配置）
#   - config/infrastructure.json  （基础设施配置）
#   - agents/*/extensions/  （自定义扩展点文件）
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         fast-harness 插件更新                        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
info "正在从 GitHub 拉取最新版本..."
info "用户自定义配置（project-context.md、infrastructure.json、extensions/）将被保留"
echo ""

curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh | bash -s -- --force
