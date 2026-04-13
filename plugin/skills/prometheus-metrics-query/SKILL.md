---
name: prometheus-metrics-query
description: 查询 ARMS Prometheus 监控指标。触发词：查 Prometheus、监控指标、QPS、错误率、延迟、CPU、内存。
---

# Prometheus 监控指标查询

## 配置来源

所有连接参数从 `.ether/config/infrastructure.json` 的 `kubernetes` 段读取：

```bash
python3 -c "
import json
cfg = json.load(open('.ether/config/infrastructure.json'))['kubernetes']
prom = cfg.get('prometheus', {})
print('Prometheus 本地端口:', prom.get('local_port', 19090))
print('Prometheus namespace:', cfg['namespaces']['prometheus'])
print('Prometheus API:', f'http://127.0.0.1:{prom.get(\"local_port\", 19090)}/api/v1/query_range')
"
```

---

## 自动初始化（首次使用）

**AI 执行以下脚本，建立 K8s API 隧道并启动 Prometheus 端口转发**：

```python
import json, subprocess, socket, time, os, sys

PROJECT_ROOT = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True).strip()
cfg_path = os.path.join(PROJECT_ROOT, '.ether/config/infrastructure.json')

try:
    k8s = json.load(open(cfg_path))['kubernetes']
except (FileNotFoundError, KeyError):
    print('未找到 kubernetes 配置，请先运行 .ether/configure.sh'); sys.exit(1)

if 'prometheus' not in k8s:
    print('未找到 prometheus 配置，请先运行 .ether/configure.sh 并启用 Prometheus'); sys.exit(1)

bastion    = k8s['bastion']
bind       = bastion.get('bind_address', '127.0.0.1')
k8s_lport  = bastion['local_port']
prom_cfg   = k8s['prometheus']
prom_lport = prom_cfg['local_port']
kubeconfig = os.path.join(PROJECT_ROOT, k8s['kubeconfig_path'])
key_path   = os.path.join(PROJECT_ROOT, bastion['key_path'])
env        = {**os.environ, 'KUBECONFIG': kubeconfig}

def port_open(host, port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0

# 1. K8s API 隧道
if not port_open(bind, k8s_lport):
    cmd = [
        'ssh', '-f', '-N',
        '-o', 'ExitOnForwardFailure=yes',
        '-o', 'StrictHostKeyChecking=accept-new',
        '-i', key_path,
        '-p', str(bastion['port']),
        '-L', f"{bind}:{k8s_lport}:{bastion['k8s_api_host']}:{bastion['k8s_api_port']}",
        f"{bastion['user']}@{bastion['host']}"
    ]
    subprocess.run(cmd, check=True)
    time.sleep(2)
    print(f'K8s 隧道已建立: {bind}:{k8s_lport}')
else:
    print(f'K8s 隧道已就绪: {bind}:{k8s_lport}')

# 2. Prometheus 端口转发
if not port_open('127.0.0.1', prom_lport):
    ns_prom = k8s['namespaces']['prometheus']
    subprocess.Popen([
        'kubectl', 'port-forward',
        '-n', ns_prom,
        f"svc/{prom_cfg['service']}",
        f"{prom_lport}:{prom_cfg['service_port']}",
        '--address', '127.0.0.1'
    ], env=env)
    time.sleep(2)
    print(f'Prometheus 端口转发就绪: http://127.0.0.1:{prom_lport}')
else:
    print(f'Prometheus 已就绪: http://127.0.0.1:{prom_lport}')
```

---

## 验证状态

```bash
python3 -c "
import json, subprocess, os
PROJECT_ROOT = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
port = json.load(open(os.path.join(PROJECT_ROOT, '.ether/config/infrastructure.json')))['kubernetes']['prometheus']['local_port']
print(f'Prometheus API: http://127.0.0.1:{port}/api/v1/status/config')
"
# 然后执行：
curl -s --max-time 2 http://127.0.0.1:<prometheus.local_port>/api/v1/status/config && echo " Prometheus OK"
```

---

## 适用场景

- 查询 QPS、错误率、响应时间等监控指标
- 查询 Pod CPU / 内存使用率
- 分析应用性能趋势

---

## 常用 PromQL 查询

namespace 从 `infrastructure.json` 的 `kubernetes.namespaces.prod` 读取：

```promql
# 错误率（5xx 错误占比）
sum(rate(http_requests_total{namespace="<namespaces.prod>", status=~"5.."}[5m]))
/ sum(rate(http_requests_total{namespace="<namespaces.prod>"}[5m]))

# P95 延迟
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{namespace="<namespaces.prod>"}[5m])) by (le, handler)
)

# QPS 按接口分组
sum by(handler) (rate(http_requests_total{namespace="<namespaces.prod>"}[1m]))

# Pod CPU 使用率
sum(rate(container_cpu_usage_seconds_total{namespace="<namespaces.prod>", pod=~"my-service-.*"}[5m]))

# Pod 内存使用量（MB）
sum(container_memory_working_set_bytes{namespace="<namespaces.prod>"}) by (pod) / 1024 / 1024
```

---

## 执行查询

```python
import json, subprocess, os, urllib.request, urllib.parse

PROJECT_ROOT = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
k8s      = json.load(open(os.path.join(PROJECT_ROOT, '.ether/config/infrastructure.json')))['kubernetes']
prom_url = f"http://127.0.0.1:{k8s['prometheus']['local_port']}/api/v1/query_range"
ns_prod  = k8s['namespaces']['prod']

query  = f'sum(rate(http_requests_total{{namespace="{ns_prod}"}}[5m]))'
params = urllib.parse.urlencode({
    'query': query, 'start': 'now-30m', 'end': 'now', 'step': '60s'
})
with urllib.request.urlopen(f"{prom_url}?{params}") as r:
    import json as _json
    data = _json.load(r)
    for series in data['data']['result']:
        print(series['metric'], '→', series['values'][-1])
```

---

## 输出格式

向用户展示：
- 使用的 PromQL 查询语句
- 时间范围
- 指标数值或趋势（最近一个采样点 + 趋势描述）
- 简要分析（是否异常、与正常水位的对比）

---

## 注意事项

1. **只读查询**：只能执行读取操作
2. **按需初始化**：已建立的隧道/转发自动跳过
3. **token 有效期**：kubeconfig token 过期后需要重新生成
4. **时间精度**：`step` 参数影响数据精度，建议短时间范围用小 step（如 `15s`），长时间用大 step（如 `5m`）
