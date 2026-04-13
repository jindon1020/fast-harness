---
name: kafka-connector
description: Kafka 连接 Skill。从 infrastructure.json 读取 Kafka 配置，提供消费消息、查看 topic/consumer group 状态等命令模板。触发词：查 Kafka、消息队列、消费消息、topic 状态、consumer group。
---

# Kafka 连接器（统一配置）

从 `.ether/config/infrastructure.json` 读取 Kafka 连接配置，提供消费消息和状态查询的命令模板。

---

## 配置来源

所有连接参数从 `.ether/config/infrastructure.json` 的 `kafka.{env}` 段读取：

```bash
cat .ether/config/infrastructure.json | python3 -c "
import json, sys
config = json.load(sys.stdin)
kafka_cfg = config.get('kafka', {})
for env in kafka_cfg:
    c = kafka_cfg[env]
    print(f'  {env}: brokers={c[\"brokers\"]} group_id={c.get(\"group_id\", \"N/A\")}')
"
```

---

## 连接方式

### kafka-console-consumer（查看消息）

```bash
CONFIG_FILE=".ether/config/infrastructure.json"
ENV="dev"

eval $(python3 -c "
import json
cfg = json.load(open('$CONFIG_FILE'))['kafka']['$ENV']
brokers = ','.join(cfg['brokers'])
group_id = cfg.get('group_id', 'debug-consumer')
print(f\"BROKERS='{brokers}' GROUP_ID='{group_id}'\")
")

kafka-console-consumer \
  --bootstrap-server $BROKERS \
  --topic {topic_name} \
  --group $GROUP_ID \
  --from-beginning \
  --max-messages 10
```

### Python 消费（confluent-kafka / kafka-python）

```python
import json
from kafka import KafkaConsumer

cfg = json.load(open('.ether/config/infrastructure.json'))['kafka']['dev']
consumer = KafkaConsumer(
    '{topic_name}',
    bootstrap_servers=cfg['brokers'],
    group_id=cfg.get('group_id', 'debug-consumer'),
    auto_offset_reset='earliest',
    enable_auto_commit=False,
    consumer_timeout_ms=10000
)
for msg in consumer:
    print(f"offset={msg.offset} key={msg.key} value={msg.value[:200]}")
    break
consumer.close()
```

---

## 常用查询命令

| 场景 | 命令 |
|------|------|
| 列出所有 topic | `kafka-topics --bootstrap-server $BROKERS --list` |
| 查看 topic 详情 | `kafka-topics --bootstrap-server $BROKERS --describe --topic {name}` |
| 查看 consumer group | `kafka-consumer-groups --bootstrap-server $BROKERS --describe --group $GROUP_ID` |
| 查看 consumer lag | `kafka-consumer-groups --bootstrap-server $BROKERS --describe --group $GROUP_ID` |
| 消费最新 N 条消息 | `kafka-console-consumer --bootstrap-server $BROKERS --topic {name} --max-messages N` |

---

## 安全约束

- 默认只读：消费消息、查看 topic/group 状态
- 禁止删除 topic（`kafka-topics --delete`）
- 禁止修改 consumer group offset（除非用户明确确认）
- 使用独立的 `debug-consumer` group_id，避免影响业务消费者
