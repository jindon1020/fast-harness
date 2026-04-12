---
name: db-bastion-query
description: 经堡垒机 SSH 隧道在本地只读查询 dev/prod 环境 MySQL。用于编码对照数据、排障核对记录。触发词：查库、堡垒机 MySQL、SSH 隧道查库、本地连 RDS、SHOW TABLES、只读查库、查 dev、查 prod、开发库、生产库。
---

# MySQL 数据库查询：经堡垒机本地只读（dev / prod 双环境）

在**本地**通过 **SSH 本地端口转发** 连接阿里云 RDS，支持 **dev** 和 **prod** 两套环境，用 `SELECT` / `SHOW` 等只读语句做数据核对与问题排查。

---

## 环境选择（必须首先确认）

进入查库流程前，**必须先确认目标环境**。根据上下文推断或直接询问用户：

| 环境 | 配置文件 | 本地隧道端口 | 数据库 |
|------|----------|-------------|--------|
| **dev** | `.local/bastion.env` | `13306`（默认） | `drama-dev` |
| **prod** | `.local/bastion-prod.env` | `13307`（默认） | `drama-prod` |

**推断规则**：
- 用户提到 `dev` / `开发` / `测试` → 使用 dev 配置
- 用户提到 `prod` / `生产` / `线上` / `正式` → 使用 prod 配置
- 由 debugger-agent B-Step 2 调度时，沿用 B-Step 0 已确认的环境
- **无法确定时，必须暂停询问**，禁止默认选 dev

---

## 硬性禁令（写库操作）

**在未获得用户在当前对话中针对「每一条」拟执行语句的明确确认前（例如用户逐条回复同意某条 `UPDATE`/`DELETE` 全文）：**

- **严禁**执行任何会修改数据库状态或结构的语句，包括但不限于：`INSERT`、`UPDATE`、`DELETE`、`REPLACE`、`MERGE`、`TRUNCATE`、`DROP`、`ALTER`、`CREATE`、`RENAME`、`GRANT`、`REVOKE`、`LOAD DATA`、`OPTIMIZE`、`REPAIR`，以及可能写库的 `CALL` / 动态 SQL。
- **严禁**代用户运行迁移（Alembic/Flyway 等）、ORM `session.commit()` 写操作、或「顺手修一条数据」。
- **严禁**在未经确认时执行 `DELETE`、`UPDATE`、带 `FOR UPDATE` / `LOCK IN SHARE MODE` 的语句。

**默认仅允许（只读）：** `SELECT`、`SHOW`、`DESCRIBE` / `DESC`、`EXPLAIN`（及 `EXPLAIN` 各变体）、**仅由 CTE 组成的只读** `WITH ... SELECT`。

用户若只说「查一下」「看看库里有什么」「对一下数据」，一律按**只读**处理。

### prod 环境额外安全约束

- 仅允许 `SELECT` 和 `SHOW TABLES`，禁止 `SHOW TABLES` 以外的 `SHOW` 变体
- 每次连接 prod 前必须输出醒目提醒：「⚠️ 当前连接的是 **生产环境** 数据库（drama-prod），请确认查询必要性。」
- 禁止在 prod 环境执行任何写操作，即使用户确认也不执行（需用户自行通过其他渠道操作）

---

## 私钥与堡垒机配置（本 Skill 不包含任何私钥内容）

1. **SSH 私钥必须由使用者自行放置**，本仓库**不得**在 Skill 或文档中写入私钥文件内容。
2. **统一路径**（目录已被 Git 忽略）：
   - 私钥文件：`.local/id_rsa`（相对于项目根目录，dev/prod 共用）
   - 权限：`chmod 600 .local/id_rsa`
3. **可选覆盖**：环境变量 `BASTION_SSH_KEY` 指向本机任意私钥路径（仍须 `600` 权限）。
4. **堡垒机连接参数**：
   - dev：`.local/bastion.env`（由 `.local/bastion.env.example` 复制而来）
   - prod：`.local/bastion-prod.env`（由 `.local/bastion-prod.env.example` 复制而来）
   - 两个文件均须包含：`BASTION_HOST`、`BASTION_PORT`、`BASTION_USER`，以及 `MYSQL_*` 系列变量

**若私钥文件不存在且未设置 `BASTION_SSH_KEY`：**  
必须先向用户说明：请将堡垒机 SSH 私钥放到项目根目录 `.local/id_rsa`，或设置环境变量；**不要**猜测或伪造密钥路径，**不要**在仓库中新增私钥文件。

**若对应环境的 `.env` 缺失或关键变量为空：**  
提醒用户从对应的 `.example` 文件复制并填写后再建立隧道。

---

## 数据库连接信息来源

dev 和 prod 的数据库连接信息（主机、端口、库名、账号密码）**统一从 `.local/` 下的 env 文件读取**：

| 环境 | 配置文件 | 关键变量 |
|------|----------|----------|
| dev | `.local/bastion.env` | `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DB_NAME`、`MYSQL_USERNAME`、`MYSQL_PASSWORD`、`MYSQL_TUNNEL_LOCAL_PORT` |
| prod | `.local/bastion-prod.env` | 同上（值不同） |

本地连接时**不直连** `MYSQL_HOST:MYSQL_PORT`，而是连 **隧道本地端口** `127.0.0.1:MYSQL_TUNNEL_LOCAL_PORT`。

---

## 建立 SSH 隧道（后台运行示例）

根据目标环境选择对应配置文件。以下脚本通过 `ENV` 变量切换：

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
SSH_KEY="${BASTION_SSH_KEY:-${PROJECT_ROOT}/.local/id_rsa}"

if [ ! -f "$SSH_KEY" ]; then
  echo "错误：未找到 SSH 私钥。请将私钥放到 .local/id_rsa 或设置 BASTION_SSH_KEY。"
  exit 1
fi

# 选择环境配置：dev 或 prod
ENV="${1:-dev}"
if [ "$ENV" = "prod" ]; then
  ENV_FILE="${PROJECT_ROOT}/.local/bastion-prod.env"
else
  ENV_FILE="${PROJECT_ROOT}/.local/bastion.env"
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "错误：未找到配置文件 ${ENV_FILE}。请从对应的 .example 文件复制并填写。"
  exit 1
fi

source "$ENV_FILE"

ssh -f -N -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=accept-new \
  -i "$SSH_KEY" -p "${BASTION_PORT}" \
  -L "${MYSQL_TUNNEL_LOCAL_PORT}:${MYSQL_HOST}:${MYSQL_PORT}" \
  "${BASTION_USER}@${BASTION_HOST}"

echo "隧道已建立：127.0.0.1:${MYSQL_TUNNEL_LOCAL_PORT} → ${MYSQL_HOST}:${MYSQL_PORT}（${ENV} 环境，库名 ${MYSQL_DB_NAME}）"
```

> dev 隧道默认 `13306`，prod 隧道默认 `13307`，两条隧道可并存互不干扰。

排障结束后可结束对应 `ssh` 转发进程（按本机 PID 管理）。

---

## 只读查询方式

- **推荐**：项目虚拟环境中已有 `pymysql`（`requirements.txt`），连接 `127.0.0.1` + `MYSQL_TUNNEL_LOCAL_PORT`，库名/用户/密码来自对应 env 文件。
- 若本机已安装 `mysql` 客户端，也可用 `mysql -h 127.0.0.1 -P $MYSQL_TUNNEL_LOCAL_PORT ...` 执行**只读** SQL。

**示例（通用查询，根据环境变量自动切换）：**

```bash
# 需在另一终端已建立对应环境的隧道
# ENV_FILE 在建隧道时已 source，此处直接使用变量
source .venv/bin/activate
python -c "
import pymysql, os
conn = pymysql.connect(
    host='127.0.0.1',
    port=int(os.environ['MYSQL_TUNNEL_LOCAL_PORT']),
    user=os.environ['MYSQL_USERNAME'],
    password=os.environ['MYSQL_PASSWORD'],
    database=os.environ['MYSQL_DB_NAME'],
    connect_timeout=15
)
with conn.cursor() as c:
    c.execute('SHOW TABLES')
    for (t,) in c.fetchall():
        print(t)
conn.close()
"
```

---

## Agent 自检清单（执行前）

- [ ] 已确认目标环境（dev / prod）并向用户回显确认。
- [ ] 已确认本次需求为**只读**或已拿到用户对**具体写语句**的明确确认。
- [ ] 若为 prod 环境，已输出生产环境醒目提醒，且仅使用 `SELECT` / `SHOW TABLES`。
- [ ] 私钥路径（`.local/id_rsa`）存在或已设置 `BASTION_SSH_KEY`；否则已提醒用户放置私钥。
- [ ] 对应环境的 `.env` 文件（`.local/bastion.env` 或 `.local/bastion-prod.env`）已就绪；否则已提醒用户从 `.example` 复制并填写。
- [ ] 隧道建立后再连 `127.0.0.1:MYSQL_TUNNEL_LOCAL_PORT`，勿在未隧道时直连 RDS 公网。
