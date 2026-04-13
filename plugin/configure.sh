#!/usr/bin/env bash
# fast-harness 项目配置脚本（v2 — 分段交互式）
# 生成 project-context.md 和 config/infrastructure.json
# 用法: cd your-project && fast-harness/configure.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         fast-harness 项目配置向导                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
info "项目路径: $PROJECT_ROOT"
info "插件目录: $SCRIPT_DIR"
echo ""

# ================================ [1/4] 项目基本信息 ================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [1/4] 项目基本信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "项目名称 [$(basename "$PROJECT_ROOT")]: " PROJECT_NAME
PROJECT_NAME="${PROJECT_NAME:-$(basename "$PROJECT_ROOT")}"

read -p "技术栈 [Python 3.11 / FastAPI / SQLModel / MySQL]: " TECH_STACK
TECH_STACK="${TECH_STACK:-Python 3.11 / FastAPI / SQLModel / MySQL}"

read -p "API 前缀 [/api]: " API_PREFIX
API_PREFIX="${API_PREFIX:-/api}"

echo ""
echo "请输入项目目录结构（直接回车使用默认 FastAPI 结构）:"
read -p "使用默认结构? [Y/n]: " USE_DEFAULT_STRUCTURE

if [[ "${USE_DEFAULT_STRUCTURE:-Y}" =~ ^[Yy]$ ]]; then
    PROJECT_STRUCTURE='app/
├── routers/     # API 路由（入口层）
├── services/    # 业务逻辑层
├── schemas/     # 请求/响应模型
├── dao/         # 数据访问层
├── models/      # 数据库模型
├── gateways/    # 外部服务集成
└── config/      # 配置文件'
else
    echo "请输入目录结构（输入 END 结束）:"
    PROJECT_STRUCTURE=""
    while IFS= read -r line; do
        [[ "$line" == "END" ]] && break
        PROJECT_STRUCTURE="${PROJECT_STRUCTURE}${line}
"
    done
fi

echo ""

# ================================ [2/4] 本地开发环境 ================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [2/4] 本地开发环境"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "虚拟环境激活命令 [source .venv/bin/activate]: " VENV_CMD
VENV_CMD="${VENV_CMD:-source .venv/bin/activate}"

read -p "开发服务器启动命令 [uvicorn app.main:app --host 0.0.0.0 --port 8000]: " DEV_CMD
DEV_CMD="${DEV_CMD:-uvicorn app.main:app --host 0.0.0.0 --port 8000}"

read -p "健康检查 URL [GET http://localhost:8000/healthz]: " HEALTH_URL
HEALTH_URL="${HEALTH_URL:-GET http://localhost:8000/healthz}"

read -p "响应格式 [{\"code\": 0, \"data\": ..., \"message\": \"success\"}]: " RESPONSE_FORMAT
RESPONSE_FORMAT="${RESPONSE_FORMAT:-{\"code\": 0, \"data\": ..., \"message\": \"success\"}}"

echo ""

# ================================ [3/4] 基础设施配置 ================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [3/4] 基础设施配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

INFRA_JSON="{"

# --- MySQL ---
read -p "使用 MySQL? [Y/n]: " USE_MYSQL
if [[ "${USE_MYSQL:-Y}" =~ ^[Yy]$ ]]; then
    info "配置 MySQL local 环境..."
    read -p "  Host [127.0.0.1]: " MYSQL_HOST; MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
    read -p "  Port [3306]: " MYSQL_PORT; MYSQL_PORT="${MYSQL_PORT:-3306}"
    read -p "  User [root]: " MYSQL_USER; MYSQL_USER="${MYSQL_USER:-root}"
    read -p "  Password [123456]: " MYSQL_PASS; MYSQL_PASS="${MYSQL_PASS:-123456}"
    read -p "  Database [my-db]: " MYSQL_DB; MYSQL_DB="${MYSQL_DB:-my-db}"

    INFRA_JSON="$INFRA_JSON
  \"mysql\": {
    \"local\": {
      \"host\": \"$MYSQL_HOST\",
      \"port\": $MYSQL_PORT,
      \"user\": \"$MYSQL_USER\",
      \"password\": \"$MYSQL_PASS\",
      \"database\": \"$MYSQL_DB\"
    }"

    read -p "  配置 dev 环境堡垒机? [y/N]: " USE_BASTION_DEV
    if [[ "${USE_BASTION_DEV:-N}" =~ ^[Yy]$ ]]; then
        info "  配置 MySQL dev 环境（经堡垒机）..."
        read -p "    RDS Host: " DEV_MYSQL_HOST
        read -p "    RDS Port [3306]: " DEV_MYSQL_PORT; DEV_MYSQL_PORT="${DEV_MYSQL_PORT:-3306}"
        read -p "    User [readonly]: " DEV_MYSQL_USER; DEV_MYSQL_USER="${DEV_MYSQL_USER:-readonly}"
        read -p "    Password: " DEV_MYSQL_PASS
        read -p "    Database: " DEV_MYSQL_DB
        read -p "    堡垒机 Host: " BASTION_HOST
        read -p "    堡垒机 Port [22]: " BASTION_PORT; BASTION_PORT="${BASTION_PORT:-22}"
        read -p "    堡垒机 User [deploy]: " BASTION_USER; BASTION_USER="${BASTION_USER:-deploy}"
        read -p "    SSH Key 路径 [.local/id_rsa]: " KEY_PATH; KEY_PATH="${KEY_PATH:-.local/id_rsa}"
        read -p "    本地隧道端口 [13306]: " TUNNEL_PORT; TUNNEL_PORT="${TUNNEL_PORT:-13306}"

        INFRA_JSON="$INFRA_JSON,
    \"dev\": {
      \"host\": \"$DEV_MYSQL_HOST\",
      \"port\": $DEV_MYSQL_PORT,
      \"user\": \"$DEV_MYSQL_USER\",
      \"password\": \"$DEV_MYSQL_PASS\",
      \"database\": \"$DEV_MYSQL_DB\",
      \"bastion\": {
        \"host\": \"$BASTION_HOST\",
        \"port\": $BASTION_PORT,
        \"user\": \"$BASTION_USER\",
        \"key_path\": \"$KEY_PATH\",
        \"local_port\": $TUNNEL_PORT
      }
    }"
    fi

    INFRA_JSON="$INFRA_JSON
  }"
fi

# --- Redis ---
echo ""
read -p "使用 Redis? [y/N]: " USE_REDIS
if [[ "${USE_REDIS:-N}" =~ ^[Yy]$ ]]; then
    info "配置 Redis local 环境..."
    read -p "  Host [127.0.0.1]: " REDIS_HOST; REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
    read -p "  Port [6379]: " REDIS_PORT; REDIS_PORT="${REDIS_PORT:-6379}"
    read -p "  Password (留空无密码): " REDIS_PASS; REDIS_PASS="${REDIS_PASS:-}"
    read -p "  DB [0]: " REDIS_DB; REDIS_DB="${REDIS_DB:-0}"

    [[ "$INFRA_JSON" != "{" ]] && INFRA_JSON="$INFRA_JSON,"
    INFRA_JSON="$INFRA_JSON
  \"redis\": {
    \"local\": {
      \"host\": \"$REDIS_HOST\",
      \"port\": $REDIS_PORT,
      \"password\": \"$REDIS_PASS\",
      \"db\": $REDIS_DB
    }
  }"
fi

# --- Kafka ---
echo ""
read -p "使用 Kafka? [y/N]: " USE_KAFKA
if [[ "${USE_KAFKA:-N}" =~ ^[Yy]$ ]]; then
    info "配置 Kafka..."
    read -p "  Brokers (逗号分隔) [localhost:9092]: " KAFKA_BROKERS; KAFKA_BROKERS="${KAFKA_BROKERS:-localhost:9092}"
    read -p "  Consumer Group ID [debug-consumer]: " KAFKA_GROUP; KAFKA_GROUP="${KAFKA_GROUP:-debug-consumer}"
    read -p "  环境名 [dev]: " KAFKA_ENV; KAFKA_ENV="${KAFKA_ENV:-dev}"

    BROKER_ARRAY=$(echo "$KAFKA_BROKERS" | python3 -c "import sys; print(str([b.strip() for b in sys.stdin.read().strip().split(',')]).replace(\"'\", '\"'))")

    [[ "$INFRA_JSON" != "{" ]] && INFRA_JSON="$INFRA_JSON,"
    INFRA_JSON="$INFRA_JSON
  \"kafka\": {
    \"$KAFKA_ENV\": {
      \"brokers\": $BROKER_ARRAY,
      \"group_id\": \"$KAFKA_GROUP\"
    }
  }"
fi

INFRA_JSON="$INFRA_JSON
}"

echo ""

# ================================ [4/4] 写入配置文件 ================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [4/4] 生成配置文件"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 写入 project-context.md
cat > "$SCRIPT_DIR/project-context.md" << CTXEOF
# 项目上下文配置

> 此文件被所有 Agent 和 Command 统一引用，修改一处全局生效。
> 由 configure.sh 自动生成于 $(date +%Y-%m-%d)。

## 基本信息

- **项目名称**: $PROJECT_NAME
- **项目路径**: 当前工作目录（Workspace 根目录）
- **技术栈**: $TECH_STACK
- **API 前缀**: $API_PREFIX

## 目录结构

\`\`\`
$PROJECT_STRUCTURE
tests/
├── {branch}/    # 按 Git 分支组织测试
.ai/
├── design/      # 设计文档
├── implement/   # implement 流水线文件
├── fix/         # fix 流水线文件
├── modify/      # modify 流水线文件
└── refactor/    # refactor 流水线文件
\`\`\`

## 本地开发环境

- **虚拟环境激活**: \`$VENV_CMD\`
- **开发服务器**: \`$DEV_CMD\`
- **健康检查**: \`$HEALTH_URL\`

## 编码约定

- **响应格式**: \`$RESPONSE_FORMAT\`
- **注释语言**: 中文
- **Commit 格式**: \`<类型>: <简短描述>\`（中文）

## 基础设施

> 中间件连接配置（MySQL、Redis、Kafka 等）在 \`fast-harness/config/infrastructure.json\` 中管理。
> Agent 通过 Connector Skills（db-connector、redis-connector 等）读取配置并连接。
CTXEOF

ok "已生成: $SCRIPT_DIR/project-context.md"

# 写入 infrastructure.json（格式化 JSON）
mkdir -p "$SCRIPT_DIR/config"
echo "$INFRA_JSON" | python3 -m json.tool > "$SCRIPT_DIR/config/infrastructure.json"
ok "已生成: $SCRIPT_DIR/config/infrastructure.json"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                   配置完成！                          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "已生成的配置文件："
echo "  📄 fast-harness/project-context.md      # 项目上下文（所有 Agent 引用）"
echo "  📄 fast-harness/config/infrastructure.json  # 基础设施配置"
echo ""
echo "下一步："
echo "  1. 查看并微调生成的配置文件"
echo "  2. 开始使用: /implement 我需要实现 XXX 功能"
echo "  3. 添加自定义扩展: 使用 harness-meta-skill 管理扩展点"
echo ""
