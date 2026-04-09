---
name: dev-mysql-bastion-query
description: 经堡垒机 SSH 隧道在本地只读查询开发环境 MySQL（drama-dev 等）。用于编码对照线上数据、排障核对记录。触发词：开发库、堡垒机 MySQL、SSH 隧道查库、本地连 RDS、SHOW TABLES、只读查库。
---

# 开发库 MySQL：经堡垒机本地只读查询

在**本地**通过 **SSH 本地端口转发** 连接阿里云 RDS（开发库），用 `SELECT` / `SHOW` 等与线上一致的数据核对接口与排查问题。

## 硬性禁令（写库操作）

**在未获得用户在当前对话中针对「每一条」拟执行语句的明确确认前（例如用户逐条回复同意某条 `UPDATE`/`DELETE` 全文）：**

- **严禁**执行任何会修改数据库状态或结构的语句，包括但不限于：`INSERT`、`UPDATE`、`DELETE`、`REPLACE`、`MERGE`、`TRUNCATE`、`DROP`、`ALTER`、`CREATE`、`RENAME`、`GRANT`、`REVOKE`、`LOAD DATA`、`OPTIMIZE`、`REPAIR`，以及可能写库的 `CALL` / 动态 SQL。
- **严禁**代用户运行迁移（Alembic/Flyway 等）、ORM `session.commit()` 写操作、或「顺手修一条数据」。
- **严禁**在未经确认时执行 `DELETE`、`UPDATE`、带 `FOR UPDATE` / `LOCK IN SHARE MODE` 的语句。

**默认仅允许（只读）：** `SELECT`、`SHOW`、`DESCRIBE` / `DESC`、`EXPLAIN`（及 `EXPLAIN` 各变体）、**仅由 CTE 组成的只读** `WITH ... SELECT`。

用户若只说「查一下」「看看库里有什么」「对一下数据」，一律按**只读**处理。

---

## 私钥与堡垒机配置（本 Skill 不包含任何私钥内容）

1. **SSH 私钥必须由使用者自行放置**，本仓库**不得**在 Skill 或文档中写入私钥文件内容。
2. **推荐路径**（目录已被 Git 忽略，见 `deploy/monitor/.local/README.md`）：
   - 私钥文件：`deploy/monitor/.local/id_rsa`
   - 权限：`chmod 600 deploy/monitor/.local/id_rsa`
3. **可选覆盖**：环境变量 `CREATION_TOOL_BASTION_SSH_KEY` 指向本机任意私钥路径（仍须 `600` 权限）。
4. **堡垒机连接参数**：在 `deploy/monitor/.local/bastion.env` 中配置（由同目录 `bastion.env.example` 复制而来，**勿提交** `bastion.env`）。至少需要：`BASTION_HOST`、`BASTION_PORT`、`BASTION_USER`。

**若私钥文件不存在且未设置 `CREATION_TOOL_BASTION_SSH_KEY`：**  
必须先向用户说明：请将堡垒机 SSH 私钥放到上述推荐路径，或设置环境变量；**不要**猜测或伪造密钥路径，**不要**在仓库中新增私钥文件。

**若 `bastion.env` 缺失或关键变量为空：**  
提醒用户从 `deploy/monitor/.local/bastion.env.example` 复制为 `bastion.env` 并填写堡垒机地址、端口、用户名后再建立隧道。

---

## 数据库连接信息来源（账号与 RDS 地址）

开发环境 MySQL 主机、端口、库名、账号等以仓库内配置为准（注意其中可能含敏感信息，勿对外泄露）：

- 文件：`deploy/manifests/overlays/dev/config.yaml`
- 节点：`DB.MYSQL` 下的 `HOST`、`PORT`、`USERNAME`、`PASSWORD`、`DB_NAME`

本地连接时**不直连** `HOST:PORT`，而是连 **隧道本地端口**（见下一节）。

---

## 建立 SSH 隧道（后台运行示例）

在**项目根目录**执行前，先 `source deploy/monitor/.local/bastion.env`（若使用 `bastion.env`）。

将下列占位符替换为实际值（`RDS_HOST` / `RDS_PORT` 来自 `config.yaml` 的 `DB.MYSQL`；`LOCAL_PORT` 建议默认 `13306`，避免与本地其它服务冲突）：

```bash
SSH_KEY="${CREATION_TOOL_BASTION_SSH_KEY:-$(pwd)/deploy/monitor/.local/id_rsa}"
if [ ! -f "$SSH_KEY" ]; then
  echo "错误：未找到 SSH 私钥。请将私钥放到 deploy/monitor/.local/id_rsa 或设置 CREATION_TOOL_BASTION_SSH_KEY。"
  exit 1
fi

ssh -f -N -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=accept-new \
  -i "$SSH_KEY" -p "${BASTION_PORT}" \
  -L "${LOCAL_PORT}:${RDS_HOST}:${RDS_PORT}" \
  "${BASTION_USER}@${BASTION_HOST}"
```

排障结束后可结束对应 `ssh` 转发进程（按本机 PID 管理）。

---

## 只读查询方式

- **推荐**：项目虚拟环境中已有 `pymysql`（`requirements.txt`），连接 `127.0.0.1` + `LOCAL_PORT`，库名/用户/密码来自 `config.yaml` 对应字段。
- 若本机已安装 `mysql` 客户端，也可用 `mysql -h 127.0.0.1 -P LOCAL_PORT ...` 执行**只读** SQL。

**示例（列出当前库表名，仅只读）：**

```bash
# 需在另一终端已建立隧道；密码勿写入仓库，可从 config 临时导出环境变量或交互输入
source .venv/bin/activate
python -c "
import pymysql
# 以下占位由使用者从 config.yaml 读取或环境变量注入
conn = pymysql.connect(host='127.0.0.1', port=LOCAL_PORT, user='...', password='...', database='...', connect_timeout=15)
with conn.cursor() as c:
    c.execute('SHOW TABLES')
    for (t,) in c.fetchall():
        print(t)
conn.close()
"
```

---

## Agent 自检清单（执行前）

- [ ] 已确认本次需求为**只读**或已拿到用户对**具体写语句**的明确确认。
- [ ] 私钥路径存在或已设置 `CREATION_TOOL_BASTION_SSH_KEY`；否则已提醒用户放置私钥。
- [ ] `bastion.env`（或等价环境变量）已就绪；否则已提醒用户从 example 复制并填写。
- [ ] 隧道建立后再连 `127.0.0.1:LOCAL_PORT`，勿在未隧道时直连 RDS 公网（通常不可达或策略禁止）。
