---
name: k8s-monitor-full
description: K8s 监控诊断全套工具，支持查询 Pod/Deployment/Events/Loki 日志/Prometheus 监控指标。触发词：查 K8s、查日志、查监控、查 Pod、查 Prometheus、排障。
---

# K8s 监控诊断全套工具

## 配置来源

所有连接参数从 `.ether/config/infrastructure.json` 的 `kubernetes` 段读取：

```bash
python3 -c "
import json
cfg = json.load(open('.ether/config/infrastructure.json'))['kubernetes']
print('kubeconfig :', cfg['kubeconfig_path'])
print('bastion    :', cfg['bastion']['user'] + '@' + cfg['bastion']['host'])
print('namespaces :', cfg['namespaces'])
print('loki       :', cfg.get('loki', '未配置'))
print('prometheus :', cfg.get('prometheus', '未配置'))
"
```

---

## 自动初始化（首次使用）

**AI 执行以下脚本，一次性建立 K8s 隧道 + Loki + Prometheus 端口转发**：

```python
import json, subprocess, socket, time, os, sys

PROJECT_ROOT = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True).strip()
cfg_path = os.path.join(PROJECT_ROOT, '.ether/config/infrastructure.json')

try:
    k8s = json.load(open(cfg_path))['kubernetes']
except (FileNotFoundError, KeyError):
    print('未找到 kubernetes 配置，请先运行 .ether/configure.sh'); sys.exit(1)

bastion    = k8s['bastion']
bind       = bastion.get('bind_address', '127.0.0.1')
k8s_lport  = bastion['local_port']
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

# 2. Loki 端口转发
loki_cfg = k8s.get('loki')
if loki_cfg:
    loki_lport = loki_cfg['local_port']
    if not port_open('127.0.0.1', loki_lport):
        ns_loki = k8s['namespaces']['loki']
        subprocess.Popen([
            'kubectl', 'port-forward',
            '-n', ns_loki,
            f"svc/{loki_cfg['service']}",
            f"{loki_lport}:{loki_cfg['service_port']}",
            '--address', '127.0.0.1'
        ], env=env)
        time.sleep(2)
        print(f'Loki 端口转发: 127.0.0.1:{loki_lport}')
    else:
        print(f'Loki 已就绪: 127.0.0.1:{loki_lport}')
else:
    print('跳过 Loki（未配置）')

# 3. Prometheus 端口转发
prom_cfg = k8s.get('prometheus')
if prom_cfg:
    prom_lport = prom_cfg['local_port']
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
        print(f'Prometheus 端口转发: 127.0.0.1:{prom_lport}')
    else:
        print(f'Prometheus 已就绪: 127.0.0.1:{prom_lport}')
else:
    print('跳过 Prometheus（未配置）')
```

---

## 验证端口状态

```python
import json, subprocess, os

PROJECT_ROOT = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True).strip()
k8s = json.load(open(os.path.join(PROJECT_ROOT, '.ether/config/infrastructure.json')))['kubernetes']
kubeconfig = os.path.join(PROJECT_ROOT, k8s['kubeconfig_path'])
env = {**os.environ, 'KUBECONFIG': kubeconfig}

loki_port = k8s.get('loki', {}).get('local_port', 3100)
prom_port = k8s.get('prometheus', {}).get('local_port', 19090)
ns_prod   = k8s['namespaces']['prod']

import subprocess
subprocess.run(['curl', '-s', '--max-time', '2', f'http://127.0.0.1:{loki_port}/ready'])
subprocess.run(['curl', '-s', '--max-time', '2', f'http://127.0.0.1:{prom_port}/api/v1/status/config'])
subprocess.run(['kubectl', 'get', 'pods', '-n', ns_prod, '--request-timeout=5s'], env=env)
```

---

## 可用功能

### 1. kubectl 只读查询

配置读取后按 `kubectl-readonly` skill 方式执行，namespace 从 `infrastructure.json` 读取。

### 2. Loki 日志查询

```python
import json, requests, os, subprocess

PROJECT_ROOT = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
k8s = json.load(open(os.path.join(PROJECT_ROOT, '.ether/config/infrastructure.json')))['kubernetes']
loki_url  = f"http://127.0.0.1:{k8s['loki']['local_port']}/loki/api/v1/query_range"
ns_prod   = k8s['namespaces']['prod']

# 查询示例
params = {
    'query': f'{{namespace="{ns_prod}"}} |= "ERROR"',
    'start': 'now-30m', 'end': 'now', 'limit': 50
}
resp = requests.get(loki_url, params=params)
print(resp.json())
```

常用 LogQL：
```logql
{namespace="<namespaces.prod>"} |= "ERROR"
{namespace="<namespaces.prod>"} | logfmt | request_id="xxx"
{namespace="<namespaces.prod>"} |= "/api/episodes" |= "500"
```

### 3. Prometheus 监控查询

```python
import json, requests, os, subprocess

PROJECT_ROOT = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
k8s = json.load(open(os.path.join(PROJECT_ROOT, '.ether/config/infrastructure.json')))['kubernetes']
prom_url = f"http://127.0.0.1:{k8s['prometheus']['local_port']}/api/v1/query_range"
ns_prod  = k8s['namespaces']['prod']

params = {
    'query': f'sum(rate(http_requests_total{{namespace="{ns_prod}"}}[5m]))',
    'start': 'now-30m', 'end': 'now', 'step': '60s'
}
resp = requests.get(prom_url, params=params)
print(resp.json())
```

---

## 注意事项

1. **只读**：所有操作只读，禁止 delete / exec / patch / apply
2. **按需初始化**：已建立的隧道/转发自动跳过，不重复创建
3. **token 有效期**：kubeconfig token 过期后需要重新生成
4. **配置缺失**：Loki / Prometheus 未在 `infrastructure.json` 中配置时自动跳过
