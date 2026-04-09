---
name: prometheus-metrics-query
description: 查询 ARMS Prometheus 监控指标。触发词：查 Prometheus、监控指标、QPS、错误率、延迟、CPU、内存。
---

# Prometheus 监控指标查询

## 自动初始化（首次使用）

**AI 自动检测 skill 目录并执行以下命令**：

```bash
# 获取当前 skill 所在目录
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. 建立 K8s API 隧道（后台运行）
source "${SKILL_DIR}/bastion.env"
ssh -i "${SKILL_DIR}/id_rsa" \
  -L 127.0.0.1:16443:172.16.37.101:6443 \
  "${BASTION_USER}@${BASTION_HOST}" -p "${BASTION_PORT}" -Nf &

# 2. 等待隧道建立后，建立 Prometheus 端口转发
sleep 2
KUBECONFIG="${SKILL_DIR}/kubeconfig-readonly" \
  kubectl port-forward -n arms-prom svc/arms-prom-server 19090:9090 --address 127.0.0.1 &
```

## 预设配置

- **Prometheus API**：`http://127.0.0.1:19090/api/v1/query_range`

## 验证端口状态

```bash
curl -s --max-time 2 http://127.0.0.1:19090/api/v1/status/config && echo " Prometheus OK"
```

## 适用场景

- 查询 QPS、错误率、响应时间等监控指标
- 查询 Pod CPU/内存使用率
- 分析应用性能趋势

## 常用 PromQL 查询

```promql
# 错误率（5xx 错误占比）
sum(rate(http_requests_total{namespace="drama-prod", status=~"5.."}[5m]))
/ sum(rate(http_requests_total{namespace="drama-prod"}[5m]))

# P95 延迟
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{namespace="drama-prod"}[5m])) by (le, handler)
)

# QPS 按接口分组
sum by(handler) (rate(http_requests_total{namespace="drama-prod"}[1m]))

# Pod CPU 使用率
sum(rate(container_cpu_usage_seconds_total{namespace="drama-prod", pod=~"creation-tool-.*"}[5m]))
```

## 执行命令

```bash
curl -s "http://127.0.0.1:19090/api/v1/query_range" \
  -d 'query=sum(rate(http_requests_total{namespace="drama-prod"}[5m]))' \
  -d 'start=now-30m' \
  -d 'end=now' \
  -d 'step=60s'
```

## 输出格式

向用户展示：
- 使用的 PromQL 查询语句
- 时间范围
- 指标数值或趋势
- 简要分析

## 注意事项

1. **只读查询**：只能执行读取操作
2. **自动初始化**：首次使用自动建立 SSH 隧道和端口转发
3. **token 有效期**：kubeconfig token 过期后需要重新生成
