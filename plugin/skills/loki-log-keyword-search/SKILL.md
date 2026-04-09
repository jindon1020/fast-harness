---
name: loki-log-keyword-search
description: 根据关键词检索线上 Loki 日志。触发词：查 Loki、日志检索、request_id、LogQL、关键词搜日志、排障查日志。
---

# Loki 日志关键词检索

## 自动初始化（首次使用）

**配置文件位置**：`.local/` 目录下（从仓库根目录）

```bash
# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "$(dirname "$(dirname "${BASH_SOURCE[0]}")")")" && pwd)"

# 1. 建立 K8s API 隧道（后台运行）
source "${PROJECT_ROOT}/.local/bastion.env"
ssh -i "${PROJECT_ROOT}/.local/id_rsa" \
  -L 127.0.0.1:16443:172.16.37.101:6443 \
  "${BASTION_USER}@${BASTION_HOST}" -p "${BASTION_PORT}" -Nf &

# 2. 等待隧道建立后，建立 Loki 端口转发
sleep 3
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" \
  kubectl port-forward -n loki svc/loki 3100:3100 --address 127.0.0.1 &
```

## 预设配置

- **Loki API**：`http://127.0.0.1:3100/loki/api/v1/query_range`

## 验证端口状态

```bash
curl -s --max-time 2 http://127.0.0.1:3100/ready && echo " Loki OK"
```

## 适用场景

- 已知 request_id、错误片段、接口路径等关键词，需在 Loki 中检索日志
- 使用 Loki 查询日志，比 kubectl logs 能看到更完整的历史（Pod 重建后仍可查询）

## 常用 LogQL 查询

```logql
# 查询 drama-prod 命名空间的 ERROR 日志
{namespace="drama-prod"} |= "ERROR"

# 按 request_id 查询
{namespace="drama-prod"} | logfmt | request_id="xxx"

# 按接口查询
{namespace="drama-prod"} |= "/drama-api/episodes" |= "500"
```

## 执行命令

```bash
curl -s "http://127.0.0.1:3100/loki/api/v1/query_range" \
  -d 'query={namespace="drama-prod"} |= "ERROR"' \
  -d 'start=now-30m' \
  -d 'end=now' \
  -d 'limit=50'
```

## 输出格式

向用户展示：
- 使用的 LogQL 查询语句
- 时间范围
- 匹配的日志条数
- 关键日志内容

## 注意事项

1. **只读查询**：只能执行读取操作
2. **自动初始化**：首次使用自动建立 SSH 隧道和端口转发
3. **token 有效期**：kubeconfig token 过期后需要重新生成
