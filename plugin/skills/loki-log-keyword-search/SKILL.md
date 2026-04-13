---
name: loki-log-keyword-search
description: 根据关键词检索线上 Loki 日志。触发词：查 Loki、日志检索、request_id、LogQL、关键词搜日志、排障查日志。
---

# Loki 日志关键词检索

## 配置来源

所有连接参数从 `fast-harness/config/infrastructure.json` 的 `kubernetes` 段读取：

```bash
python3 -c "
import json
cfg = json.load(open('fast-harness/config/infrastructure.json'))['kubernetes']
loki = cfg.get('loki', {})
print('Loki 本地端口:', loki.get('local_port', 3100))
print('Loki namespace:', cfg['namespaces']['loki'])
print('Loki API:', f'http://127.0.0.1:{loki.get(\"local_port\", 3100)}/loki/api/v1/query_range')
"
```

---

## 自动初始化（首次使用）

**AI 执行以下脚本，建立 K8s API 隧道并启动 Loki 端口转发**：

```python
import json, subprocess, socket, time, os, sys

PROJECT_ROOT = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True).strip()
cfg_path = os.path.join(PROJECT_ROOT, 'fast-harness/config/infrastructure.json')

try:
    k8s = json.load(open(cfg_path))['kubernetes']
except (FileNotFoundError, KeyError):
    print('未找到 kubernetes 配置，请先运行 fast-harness/configure.sh'); sys.exit(1)

if 'loki' not in k8s:
    print('未找到 loki 配置，请先运行 fast-harness/configure.sh 并启用 Loki'); sys.exit(1)

bastion    = k8s['bastion']
bind       = bastion.get('bind_address', '127.0.0.1')
k8s_lport  = bastion['local_port']
loki_cfg   = k8s['loki']
loki_lport = loki_cfg['local_port']
kubeconfig = os.path.join(PROJECT_ROOT, k8s['kubeconfig_path'])
key_path   = os.path.join(PROJECT_ROOT, bastion['key_path'])
env        = {**os.environ, 'KUBECONFIG': kubeconfig}

def port_open(host, port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0

# 1. K8s API 隧道（Loki port-forward 依赖 kubeconfig 通过隧道连接）
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
    print(f'Loki 端口转发就绪: http://127.0.0.1:{loki_lport}')
else:
    print(f'Loki 已就绪: http://127.0.0.1:{loki_lport}')
```

---

## 验证状态

```bash
python3 -c "
import json, subprocess, os
PROJECT_ROOT = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
port = json.load(open(os.path.join(PROJECT_ROOT, 'fast-harness/config/infrastructure.json')))['kubernetes']['loki']['local_port']
print(f'Loki API: http://127.0.0.1:{port}/ready')
"
# 然后执行：
curl -s --max-time 2 http://127.0.0.1:<loki.local_port>/ready && echo " Loki OK"
```

---

## 适用场景

- 已知 request_id、错误片段、接口路径等关键词，在 Loki 中检索历史日志
- Pod 已重建导致 kubectl logs 无法查看历史，改用 Loki 查询

---

## 常用 LogQL 查询

namespace 从 `infrastructure.json` 的 `kubernetes.namespaces.prod` 读取：

```logql
# 查询生产命名空间的 ERROR 日志
{namespace="<namespaces.prod>"} |= "ERROR"

# 按 request_id 查询
{namespace="<namespaces.prod>"} | logfmt | request_id="xxx"

# 按接口路径 + 状态码查询
{namespace="<namespaces.prod>"} |= "/api/episodes" |= "500"

# 近 1 小时内某服务的所有日志
{namespace="<namespaces.prod>", app="my-service"} | logfmt
```

---

## 执行查询

```python
import json, subprocess, os

PROJECT_ROOT = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
k8s      = json.load(open(os.path.join(PROJECT_ROOT, 'fast-harness/config/infrastructure.json')))['kubernetes']
loki_url = f"http://127.0.0.1:{k8s['loki']['local_port']}/loki/api/v1/query_range"
ns_prod  = k8s['namespaces']['prod']

import urllib.request, urllib.parse, json as _json

query  = f'{{namespace="{ns_prod}"}} |= "ERROR"'
params = urllib.parse.urlencode({
    'query': query, 'start': 'now-30m', 'end': 'now', 'limit': 50
})
with urllib.request.urlopen(f"{loki_url}?{params}") as r:
    data = _json.load(r)
    for stream in data['data']['result']:
        for ts, line in stream['values']:
            print(line)
```

---

## 输出格式

向用户展示：
- 使用的 LogQL 查询语句
- 时间范围
- 匹配的日志条数
- 关键日志内容（去重后最多展示 20 条）

---

## 注意事项

1. **只读查询**：只能执行读取操作
2. **按需初始化**：已建立的隧道/转发自动跳过
3. **token 有效期**：kubeconfig token 过期后需要重新生成
4. **时间范围**：Loki 默认保留最近 7 天日志，超出范围无法查询
