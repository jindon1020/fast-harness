---
name: db-connector
description: 统一数据库连接 Skill。从 infrastructure.json 读取 MySQL 配置，支持 local 直连和 bastion SSH 隧道两种模式。触发词：查库、数据库、MySQL、bastion、堡垒机、SSH 隧道查库、只读查库、查 dev、查 prod。
---

# MySQL 数据库连接器（统一配置）

从 `.ether/config/infrastructure.json` 读取 MySQL 连接配置，支持 **local 直连** 和 **bastion SSH 隧道** 两种模式。

---

## 配置来源

所有连接参数从 `.ether/config/infrastructure.json` 的 `mysql.{env}` 段读取：

```bash
cat .ether/config/infrastructure.json | python3 -c "
import json, sys
config = json.load(sys.stdin)
mysql = config.get('mysql', {})
for env in mysql:
    print(f'  {env}: host={mysql[env][\"host\"]} port={mysql[env][\"port\"]} db={mysql[env][\"database\"]}')
"
```

| 环境 | 配置路径 | 连接方式 |
|------|----------|----------|
| **local** | `mysql.local` | 直连 `host:port` |
| **dev** | `mysql.dev` | 若有 `bastion` 字段，通过 SSH 隧道；否则直连 |
| **prod** | `mysql.prod` | 若有 `bastion` 字段，通过 SSH 隧道；否则直连 |

---

## 环境选择（必须首先确认）

进入查库流程前，**必须先确认目标环境**：

- 用户提到 `local` / `本地` → 使用 `mysql.local`
- 用户提到 `dev` / `开发` / `测试` → 使用 `mysql.dev`
- 用户提到 `prod` / `生产` / `线上` → 使用 `mysql.prod`
- 由 debugger-agent 或 unit-test-gen-agent 调度时，沿用调用方已确认的环境
- **无法确定时，必须暂停询问**，禁止默认选择

---

## 硬性禁令

**默认仅允许只读操作：** `SELECT`、`SHOW`、`DESCRIBE`、`EXPLAIN`。

- **严禁** 未经用户逐条确认的写操作（`INSERT`、`UPDATE`、`DELETE`、`ALTER` 等）
- **prod 环境额外约束**：仅允许 `SELECT` 和 `SHOW TABLES`，连接前必须输出：「⚠️ 当前连接的是 **生产环境** 数据库，请确认查询必要性。」

---

## Local 直连

```bash
# 从 infrastructure.json 读取 local 配置
CONFIG=$(python3 -c "
import json
cfg = json.load(open('.ether/config/infrastructure.json'))['mysql']['local']
print(f\"-h {cfg['host']} -P {cfg['port']} -u {cfg['user']} -p'{cfg['password']}' {cfg['database']}\")
")

mysql $CONFIG -e "SHOW TABLES"
```

或使用 Python：

```python
import json, pymysql

cfg = json.load(open('.ether/config/infrastructure.json'))['mysql']['local']
conn = pymysql.connect(
    host=cfg['host'], port=cfg['port'],
    user=cfg['user'], password=cfg['password'],
    database=cfg['database'], connect_timeout=15
)
```

---

## Bastion SSH 隧道连接

当 `mysql.{env}` 含有 `bastion` 字段时，需先建立 SSH 隧道：

```bash
CONFIG_FILE=".ether/config/infrastructure.json"
ENV="dev"  # 或 prod

python3 -c "
import json, subprocess, sys

config = json.load(open('$CONFIG_FILE'))['mysql']['$ENV']
bastion = config.get('bastion')
if not bastion:
    print('此环境无需堡垒机，可直连'); sys.exit(0)

key_path = bastion.get('key_path', '.local/id_rsa')
local_port = bastion.get('local_port', 13306)
bind_addr = bastion.get('bind_address', '127.0.0.1')

cmd = [
    'ssh', '-f', '-N', '-o', 'ExitOnForwardFailure=yes',
    '-o', 'StrictHostKeyChecking=accept-new',
    '-i', key_path, '-p', str(bastion.get('port', 22)),
    '-L', f'{bind_addr}:{local_port}:{config[\"host\"]}:{config[\"port\"]}',
    f'{bastion[\"user\"]}@{bastion[\"host\"]}'
]
print('建立隧道:', ' '.join(cmd))
subprocess.run(cmd, check=True)
print(f'隧道就绪: {bind_addr}:{local_port} → {config[\"host\"]}:{config[\"port\"]}')
"
```

隧道建立后，连接 `{bind_address}:{local_port}`（`bind_address` 默认 `127.0.0.1`）。

---

## Agent 自检清单

- [ ] 已确认目标环境并向用户回显
- [ ] `.ether/config/infrastructure.json` 中存在对应环境的 MySQL 配置
- [ ] 若需堡垒机：SSH 私钥文件存在，否则提醒用户放置
- [ ] 连接类型为只读（或已拿到用户对写语句的逐条确认）
- [ ] prod 环境已输出生产环境醒目提醒
