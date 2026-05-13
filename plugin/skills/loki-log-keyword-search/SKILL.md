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

## 自动初始化（带重试与自愈）

**AI 执行以下脚本，建立 K8s API 隧道并启动 Loki 端口转发。脚本含完整重试逻辑，确保每次查询前连接均可用。**

```python
import json, subprocess, socket, time, os, sys, signal
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

MAX_RETRIES = 5          # 最多尝试次数
RETRY_DELAY = 3          # 初始重试间隔（秒），指数退避
LOKI_READY_TIMEOUT = 10  # 单次 /ready 等待秒数

def port_open(host, port, timeout=1):
    with socket.socket() as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0

def loki_ready(port, timeout=LOKI_READY_TIMEOUT):
    """以 HTTP /ready 为准；TCP 可连不代表 Loki 后端真正就绪。"""
    url = f'http://127.0.0.1:{port}/ready'
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.getcode() == 200
    except Exception:
        return False

def kill_port(port):
    """强制杀掉占用指定端口（LISTEN）的所有进程。"""
    try:
        result = subprocess.run(
            ['lsof', '-ti', f'TCP:{port}', '-sTCP:LISTEN'],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGTERM)
                print(f'  已终止占用端口 {port} 的进程 PID={pid}')
        if pids:
            time.sleep(1)
    except Exception as e:
        print(f'  清理端口 {port} 时出错: {e}')

def ensure_ssh_tunnel(retries=MAX_RETRIES):
    """确保 K8s API SSH 隧道存在且可用，失败则重建，带重试。"""
    for attempt in range(1, retries + 1):
        if port_open(bind, k8s_lport):
            print(f'K8s 隧道已就绪: {bind}:{k8s_lport}')
            return True
        print(f'[{attempt}/{retries}] K8s 隧道不可用，尝试建立 SSH 隧道...')
        kill_port(k8s_lport)
        cmd = [
            'ssh', '-f', '-N',
            '-o', 'ExitOnForwardFailure=yes',
            '-o', 'StrictHostKeyChecking=accept-new',
            '-o', 'ServerAliveInterval=30',
            '-o', 'ServerAliveCountMax=3',
            '-o', 'ConnectTimeout=15',
            '-i', key_path,
            '-p', str(bastion['port']),
            '-L', f"{bind}:{k8s_lport}:{bastion['k8s_api_host']}:{bastion['k8s_api_port']}",
            f"{bastion['user']}@{bastion['host']}"
        ]
        try:
            subprocess.run(cmd, check=True, timeout=30)
        except Exception as e:
            print(f'  SSH 建立失败: {e}')
        delay = RETRY_DELAY * (2 ** (attempt - 1))
        time.sleep(min(delay, 20))
        if port_open(bind, k8s_lport):
            print(f'K8s 隧道已建立: {bind}:{k8s_lport}')
            return True
    print('错误: K8s API 隧道建立失败，已达最大重试次数', file=sys.stderr)
    return False

def ensure_loki_pf(retries=MAX_RETRIES):
    """确保 Loki port-forward 存在且 /ready 返回 200，失败则重建，带重试。"""
    for attempt in range(1, retries + 1):
        if loki_ready(loki_lport):
            print(f'Loki 已就绪: http://127.0.0.1:{loki_lport}')
            return True
        print(f'[{attempt}/{retries}] Loki /ready 失败，重建 port-forward...')
        # 先清理残留进程
        kill_port(loki_lport)
        time.sleep(1)
        ns_loki = k8s['namespaces']['loki']
        proc = subprocess.Popen(
            [
                'kubectl', 'port-forward',
                '-n', ns_loki,
                f"svc/{loki_cfg['service']}",
                f"{loki_lport}:{loki_cfg['service_port']}",
                '--address', '127.0.0.1',
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # 等待就绪，每秒检查一次，最多等 LOKI_READY_TIMEOUT 秒
        for _ in range(LOKI_READY_TIMEOUT):
            time.sleep(1)
            if proc.poll() is not None:
                print(f'  kubectl port-forward 进程意外退出 (code={proc.returncode})')
                break
            if loki_ready(loki_lport, timeout=3):
                print(f'Loki 端口转发就绪: http://127.0.0.1:{loki_lport}')
                return True
        delay = RETRY_DELAY * (2 ** (attempt - 1))
        print(f'  等待 {min(delay, 15)}s 后重试...')
        time.sleep(min(delay, 15))

    print(
        '错误: Loki port-forward 建立失败，已达最大重试次数。\n'
        '排查建议：\n'
        f'  1) lsof -iTCP:{loki_lport} -sTCP:LISTEN  # 查看端口占用\n'
        '  2) kubectl get svc -n <loki-ns>           # 确认 svc 名称\n'
        '  3) kubectl logs -n <loki-ns> <loki-pod>   # 查看 Loki 本身状态\n'
        '  4) 修改 kubernetes.loki.local_port 为其他未占用端口',
        file=sys.stderr,
    )
    return False

def verify_loki_stable(port, checks=3, interval=1):
    """连续多次 /ready 确认连接稳定，避免偶发通过后立刻抖动。"""
    for i in range(checks):
        if not loki_ready(port, timeout=5):
            print(f'稳定性验证失败（第 {i+1}/{checks} 次）')
            return False
        if i < checks - 1:
            time.sleep(interval)
    print(f'Loki 连接稳定（{checks} 次 /ready 全部通过）')
    return True

# ── 主流程 ──────────────────────────────────────────────────────────────
print('=== 初始化 Loki 连接 ===')

# 1. 确保 K8s API 隧道（Loki port-forward 需要通过 kubeconfig 连集群）
if not ensure_ssh_tunnel():
    sys.exit(1)

# 2. 确保 Loki port-forward 就绪
if not ensure_loki_pf():
    sys.exit(1)

# 3. 稳定性验证（连续 3 次 /ready 成功才认为可用）
if not verify_loki_stable(loki_lport):
    print('Loki 连接不稳定，尝试重建...', file=sys.stderr)
    kill_port(loki_lport)
    if not ensure_loki_pf():
        sys.exit(1)

print('=== Loki 连接就绪，可以开始查询 ===')
```

---

## 验证状态

```bash
PORT="$(python3 -c "
import json, subprocess, os
r = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()
print(json.load(open(os.path.join(r, '.ether/config/infrastructure.json')))['kubernetes']['loki']['local_port'])
")"
echo "Loki /ready: http://127.0.0.1:${PORT}/ready"
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
2. **就绪判定**：必须以 `GET http://127.0.0.1:<loki.local_port>/ready` 返回 **200** 为准；不要仅凭「端口能连上」就认为 Loki 可用
3. **重试机制**：初始化脚本最多重试 5 次，指数退避（3s、6s、12s…），每次重建前先清理残留进程
4. **稳定性验证**：连续 3 次 /ready 全部通过才认为连接可用，防止偶发抖动
5. **SSH 保活**：SSH 隧道使用 `ServerAliveInterval=30` + `ServerAliveCountMax=3`，减少长期空闲断连
6. **token 有效期**：kubeconfig token 过期后需要重新生成
7. **时间范围与超时**：建议先 **24h/48h**，再分段扩窗；扩窗时同步增大 HTTP 读超时（例如 120～300 秒）
8. **端口冲突**：若本地端口被占用，脚本会自动 SIGTERM 清理后重建；也可修改 `kubernetes.loki.local_port` 避免冲突
