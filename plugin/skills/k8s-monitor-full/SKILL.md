---
name: k8s-monitor-full
description: K8s 监控诊断全套工具，支持查询 Pod/Deployment/Events/Loki 日志/Prometheus 监控指标。触发词：查 K8s、查日志、查监控、查 Pod、查 Prometheus、排障。
---

# K8s 监控诊断全套工具

## 自动初始化（首次使用）

**AI 自动检测项目根目录并执行以下命令**：

```bash
# 获取项目根目录（Git 根）
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
LOCAL_DIR="${PROJECT_ROOT}/.local"

# 1. 建立 K8s API 隧道（后台运行）
source "${LOCAL_DIR}/bastion.env"
ssh -i "${LOCAL_DIR}/id_rsa" \
  -L 127.0.0.1:16443:172.16.37.101:6443 \
  "${BASTION_USER}@${BASTION_HOST}" -p "${BASTION_PORT}" -Nf &

# 2. 等待隧道建立后，建立 Loki 端口转发
sleep 2
KUBECONFIG="${LOCAL_DIR}/openclaw-readonly.kubeconfig" \
  kubectl port-forward -n loki svc/loki 3100:3100 --address 127.0.0.1 &

# 3. 建立 Prometheus 端口转发
KUBECONFIG="${LOCAL_DIR}/openclaw-readonly.kubeconfig" \
  kubectl port-forward -n arms-prom svc/arms-prom-server 19090:9090 --address 127.0.0.1 &
```

## 预设配置

- **Loki API**：`http://127.0.0.1:3100/loki/api/v1/query_range`
- **Prometheus API**：`http://127.0.0.1:19090/api/v1/query_range`

## 验证端口状态

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
curl -s --max-time 2 http://127.0.0.1:3100/ready && echo " Loki OK"
curl -s --max-time 2 http://127.0.0.1:19090/api/v1/status/config && echo " Prometheus OK"
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl get pods -n drama-prod --request-timeout=5s && echo " K8s API OK"
```

## 可用功能

### 1. kubectl 只读查询

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl get pods -n drama-prod
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl get deployments -n drama-prod
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl get events -n drama-prod --sort-by='.lastTimestamp' | tail -20
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl logs <pod-name> -n drama-prod --tail=100
```

### 2. Loki 日志查询

```logql
{namespace="drama-prod"} |= "ERROR"
{namespace="drama-prod"} | logfmt | request_id="xxx"
{namespace="drama-prod"} |= "/drama-api/episodes" |= "500"
```

```bash
curl -s "http://127.0.0.1:3100/loki/api/v1/query_range" \
  -d 'query={namespace="drama-prod"} |= "ERROR"' \
  -d 'start=now-30m' -d 'end=now' -d 'limit=50'
```

### 3. Prometheus 监控查询

```promql
sum(rate(http_requests_total{namespace="drama-prod"}[5m]))
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{namespace="drama-prod"}[5m])) by (le, handler))
```

```bash
curl -s "http://127.0.0.1:19090/api/v1/query_range" \
  -d 'query=sum(rate(http_requests_total{namespace="drama-prod"}[5m]))' \
  -d 'start=now-30m' -d 'end=now' -d 'step=60s'
```

## 注意事项

1. **只读**：所有操作都是只读，禁止 delete/exec/patch/apply
2. **自动初始化**：首次使用自动建立 SSH 隧道和端口转发
3. **token 有效期**：kubeconfig token 过期后需要重新生成
