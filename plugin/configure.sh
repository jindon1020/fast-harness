#!/usr/bin/env bash
# fast-harness 项目上下文配置脚本
# 用法: cd your-project && fast-harness/configure.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== fast-harness 项目上下文配置 ==="
echo ""
echo "当前项目路径: $PROJECT_ROOT"
echo ""

# 收集配置
read -p "项目路径 [$PROJECT_ROOT]: " input_root
PROJECT_PATH="${input_root:-$PROJECT_ROOT}"

read -p "开发服务器启动命令 [uvicorn app.main:app --host 0.0.0.0 --port 8000]: " input_cmd
DEV_CMD="${input_cmd:-uvicorn app.main:app --host 0.0.0.0 --port 8000}"

read -p "健康检查 URL [GET http://localhost:8000/healthz]: " input_health
HEALTH_URL="${input_health:-GET http://localhost:8000/healthz}"

read -p "数据库 Host [127.0.0.1]: " input_db_host
DB_HOST="${input_db_host:-127.0.0.1}"

read -p "数据库 Port [3306]: " input_db_port
DB_PORT="${input_db_port:-3306}"

read -p "数据库 User [root]: " input_db_user
DB_USER="${input_db_user:-root}"

read -p "数据库 Password [123456]: " input_db_pass
DB_PASS="${input_db_pass:-123456}"

read -p "数据库名 [my-db]: " input_db_name
DB_NAME="${input_db_name:-my-db}"

echo ""
echo "请输入项目目录结构（输入 END 结束，直接回车使用默认）:"
echo "提示：可以直接粘贴 tree 命令输出"
read -p "使用默认结构? [Y/n]: " use_default

if [[ "${use_default:-Y}" =~ ^[Yy]$ ]]; then
    PROJECT_STRUCTURE="app/\n├── routers/     # API 路由\n├── services/    # 业务逻辑层\n├── schemas/     # 请求/响应模型\n├── dao/         # 数据访问层\n├── models/      # 数据库模型\n├── gateways/    # 外部服务集成\n└── config/      # 配置文件"
else
    PROJECT_STRUCTURE=""
    while IFS= read -r line; do
        [[ "$line" == "END" ]] && break
        PROJECT_STRUCTURE="${PROJECT_STRUCTURE}${line}\n"
    done
fi

# 替换 commands 中的占位符
for cmd_file in "$SCRIPT_DIR/commands/"*.md; do
    if [[ -f "$cmd_file" ]]; then
        sed -i.bak \
            -e "s|{{PROJECT_ROOT}}|$PROJECT_PATH|g" \
            -e "s|{{DEV_SERVER_CMD}}|$DEV_CMD|g" \
            -e "s|{{HEALTH_CHECK_URL}}|$HEALTH_URL|g" \
            -e "s|{{DB_HOST}}|$DB_HOST|g" \
            -e "s|{{DB_PORT}}|$DB_PORT|g" \
            -e "s|{{DB_USER}}|$DB_USER|g" \
            -e "s|{{DB_PASS}}|$DB_PASS|g" \
            -e "s|{{DB_NAME}}|$DB_NAME|g" \
            "$cmd_file"
        rm -f "${cmd_file}.bak"
        echo "✅ 已配置: $(basename "$cmd_file")"
    fi
done

# 替换目录结构（多行替换比较复杂，用 python）
if command -v python3 &>/dev/null; then
    python3 - "$SCRIPT_DIR" "$PROJECT_STRUCTURE" << 'PYEOF'
import sys, os, glob
plugin_dir = sys.argv[1]
structure = sys.argv[2].replace("\\n", "\n")
for f in glob.glob(os.path.join(plugin_dir, "commands", "*.md")):
    with open(f, "r") as fh:
        content = fh.read()
    content = content.replace("{{PROJECT_STRUCTURE}}", structure)
    with open(f, "w") as fh:
        fh.write(content)
PYEOF
    echo "✅ 已替换目录结构"
fi

echo ""
echo "=== 配置完成 ==="
echo "你现在可以在 IDE 中使用 /implement、/fix、/refactor 命令了。"
