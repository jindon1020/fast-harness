---
name: loki-log-keyword-search
description: 根据关键词检索线上 Loki 日志。触发词：查 Loki、日志检索、request_id、LogQL、关键词搜日志、排障查日志。
---

# Loki 日志关键词检索

## 配置来源

所有连接参数从 `.ether/config/infrastructure.json` 的 `kubernetes` 段读取：

```bash
python3 -c "
import json
cfg = json.load(open('.ether/config/infrastructure.json'))['kubernetes']
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
import urllib.request
import urllib.error

PROJECT_ROOT = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True).strip()
cfg_path = os.path.join(PROJECT_ROOT, '.ether/config/infrastructure.json')

try:
    k8s = json.load(open(cfg_path))['kubernetes']
except (FileNotFoundError, KeyError):
    print('未找到 kubernetes 配置，请先运行 .ether/configure.sh'); sys.exit(1)

if 'loki' not in k8s:
    print('未找到 loki 配置，请先运行 .ether/configure.sh 并启用 Loki'); sys.exit(1)

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

def loki_ready(port, timeout=5):
    """以 HTTP /ready 为准；仅 TCP 通连会误判（例如 SSH -L 占用了同端口但不是集群里的 Loki）。"""
    url = f'http://127.0.0.1:{port}/ready'
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.getcode() == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False

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

# 2. Loki 端口转发：/ready 失败则强制尝试 kubectl port-forward（不再仅凭端口通断跳过）
if loki_ready(loki_lport):
    print(f'Loki 已就绪: http://127.0.0.1:{loki_lport} (/ready OK)')
else:
    if port_open('127.0.0.1', loki_lport):
        print(
            f'警告: 127.0.0.1:{loki_lport} 可连接但 /ready 失败，'
            '常见于 SSH 本地转发与 kubectl 复用同一端口。将尝试 kubectl port-forward；'
            '若 bind 失败请先停止占用该端口的进程，或把 kubernetes.loki.local_port 改为未占用端口。',
            file=sys.stderr,
        )
    ns_loki = k8s['namespaces']['loki']
    subprocess.Popen([
        'kubectl', 'port-forward',
        '-n', ns_loki,
        f"svc/{loki_cfg['service']}",
        f"{loki_lport}:{loki_cfg['service_port']}",
        '--address', '127.0.0.1'
    ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    if not loki_ready(loki_lport, timeout=8):
        print(
            'Loki 在启动 port-forward 后仍不可用。'
            '请确认：1) 本地端口未被其他隧道占用；2) kubeconfig 与 loki 命名空间/svc 正确；'
            '3) 必要时先 `lsof -iTCP:%s -sTCP:LISTEN` 释放端口后重试。' % loki_lport,
            file=sys.stderr,
        )
        sys.exit(1)
    print(f'Loki 端口转发就绪: http://127.0.0.1:{loki_lport}')
```

---

## 验证状态

```bash
PORT="$(python3 -c "
import json, subprocess, os
r = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
print(json.load(open(os.path.join(r, '.ether/config/infrastructure.json'))))['kubernetes']['loki']['local_port'])
")"
echo "Loki /ready: http://127.0.0.1:${PORT}/ready"
# 与初始化脚本一致：以 HTTP /ready 成功为准（max-time 不宜过短）
curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/ready" && echo " Loki OK"
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

大时间窗（如近 7 天）在 Loki 侧扫描更久，客户端若仍用默认短超时会被 `TimeoutError` 打断，看起来像「查不到」实为未返回。优先用 **24h～48h** 等窄窗排查，确认有结果后再分段扩大；跨天查询建议把 `urlopen(..., timeout=)` 提到 **120～300** 秒。

```python
import json, subprocess, os
import urllib.request, urllib.parse, json as _json

PROJECT_ROOT = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
k8s      = json.load(open(os.path.join(PROJECT_ROOT, '.ether/config/infrastructure.json')))['kubernetes']
loki_url = f"http://127.0.0.1:{k8s['loki']['local_port']}/loki/api/v1/query_range"
ns_prod  = k8s['namespaces']['prod']

query  = f'{{namespace="{ns_prod}"}} |= "ERROR"'
# 默认先用较窄时间窗；需要多天时再改 start 并同步增大 read_timeout_sec
params = urllib.parse.urlencode({
    'query': query,
    'start': 'now-24h',
    'end': 'now',
    'limit': 50,
})
read_timeout_sec = 120
with urllib.request.urlopen(f"{loki_url}?{params}", timeout=read_timeout_sec) as r:
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
2. **就绪判定**：必须以 `GET http://127.0.0.1:<loki.local_port>/ready` 返回 **200** 为准；**不要**仅凭「3100 端口能连上」就认为 Loki 可用（SSH `-L` 与 `kubectl port-forward` 抢同一本地端口时，TCP 通但后端不是集群里的 Loki，会出现 reset、读超时等）。初始化脚本在 `/ready` 失败时会强制尝试 `kubectl port-forward`；若本地端口已被占用，需先释放或修改 `kubernetes.loki.local_port`
3. **按需初始化**：K8s API 隧道仍可按端口检测跳过；Loki 侧按 `/ready` 跳过或拉起 port-forward
4. **token 有效期**：kubeconfig token 过期后需要重新生成
5. **时间范围与超时**：保留策略上可查约 7 天不代表应一次 `query_range` 拉满 7 天；窗越大 Loki 越慢。建议先 **24h/48h**，再分段扩窗；扩窗时同步增大 HTTP 读超时（例如 120～300 秒），避免 60s 级默认超时误报失败
6. **端口规划**：避免多条隧道复用同一本地端口（常见为 3100），与示例配置冲突时改掉 `loki.local_port` 即可
