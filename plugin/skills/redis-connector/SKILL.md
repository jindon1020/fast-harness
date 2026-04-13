---
name: redis-connector
description: Redis 连接 Skill。从 infrastructure.json 读取 Redis 配置，提供标准化的连接和查询命令模板。触发词：查 Redis、缓存查询、Redis 状态、缓存检查。
---

# Redis 连接器（统一配置）

从 `.ether/config/infrastructure.json` 读取 Redis 连接配置，提供标准化的连接命令和查询模板。

---

## 配置来源

所有连接参数从 `.ether/config/infrastructure.json` 的 `redis.{env}` 段读取：

```bash
cat .ether/config/infrastructure.json | python3 -c "
import json, sys
config = json.load(sys.stdin)
redis_cfg = config.get('redis', {})
for env in redis_cfg:
    c = redis_cfg[env]
    print(f'  {env}: host={c[\"host\"]} port={c[\"port\"]} db={c.get(\"db\", 0)}')
"
```

---

## 连接方式

### redis-cli 直连

```bash
CONFIG_FILE=".ether/config/infrastructure.json"
ENV="local"

eval $(python3 -c "
import json
cfg = json.load(open('$CONFIG_FILE'))['redis']['$ENV']
pwd_flag = f\"-a '{cfg['password']}'\" if cfg.get('password') else ''
print(f\"REDIS_CLI='redis-cli -h {cfg['host']} -p {cfg['port']} -n {cfg.get('db', 0)} {pwd_flag}'\")
")

$REDIS_CLI PING
$REDIS_CLI INFO keyspace
```

### Python 连接

```python
import json, redis

cfg = json.load(open('.ether/config/infrastructure.json'))['redis']['local']
r = redis.Redis(
    host=cfg['host'], port=cfg['port'],
    password=cfg.get('password') or None,
    db=cfg.get('db', 0), decode_responses=True
)
print(r.ping())
```

---

## 常用查询模板

| 场景 | 命令 |
|------|------|
| 检查连接 | `PING` |
| 查看 keyspace 统计 | `INFO keyspace` |
| 按模式搜索 key | `SCAN 0 MATCH "prefix:*" COUNT 100` |
| 查看 key 类型和 TTL | `TYPE {key}` + `TTL {key}` |
| 获取 string 值 | `GET {key}` |
| 获取 hash 全部字段 | `HGETALL {key}` |
| 获取 list 范围 | `LRANGE {key} 0 -1` |
| 获取 set 全部成员 | `SMEMBERS {key}` |
| 内存分析 | `MEMORY USAGE {key}` |

---

## 安全约束

- 默认只读操作：`GET`、`HGETALL`、`LRANGE`、`SMEMBERS`、`SCAN`、`INFO`、`TYPE`、`TTL`、`EXISTS`
- 写操作（`SET`、`DEL`、`FLUSHDB` 等）需用户明确确认
- 禁止在 prod 环境执行 `FLUSHDB`、`FLUSHALL`、`DEBUG`
