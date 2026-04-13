---
name: kubectl-readonly
description: 只读查询 K8s 资源状态。触发词：查 Pod、查 Deployment、查日志、K8s 状态、kubectl。
---

# kubectl 只读查询

## 配置来源

所有连接参数从 `fast-harness/config/infrastructure.json` 的 `kubernetes` 段读取：

```bash
python3 -c "
import json
cfg = json.load(open('fast-harness/config/infrastructure.json'))['kubernetes']
print('kubeconfig:', cfg['kubeconfig_path'])
print('bastion   :', cfg['bastion']['user'] + '@' + cfg['bastion']['host'])
print('namespace :', cfg['namespaces'])
"
```

---

## 自动初始化（首次使用）

**AI 执行以下脚本建立 K8s API 隧道**：

```python
import json, subprocess, socket, time, os, sys

PROJECT_ROOT = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True).strip()
cfg_path = os.path.join(PROJECT_ROOT, 'fast-harness/config/infrastructure.json')

try:
    k8s = json.load(open(cfg_path))['kubernetes']
except (FileNotFoundError, KeyError):
    print('未找到 kubernetes 配置，请先运行 fast-harness/configure.sh'); sys.exit(1)

bastion = k8s['bastion']
bind     = bastion.get('bind_address', '127.0.0.1')
lport    = bastion['local_port']

# 检测隧道是否已建立，避免重复创建
with socket.socket() as s:
    s.settimeout(1)
    already_up = s.connect_ex((bind, lport)) == 0

if not already_up:
    key_path = os.path.join(PROJECT_ROOT, bastion['key_path'])
    cmd = [
        'ssh', '-f', '-N',
        '-o', 'ExitOnForwardFailure=yes',
        '-o', 'StrictHostKeyChecking=accept-new',
        '-i', key_path,
        '-p', str(bastion['port']),
        '-L', f"{bind}:{lport}:{bastion['k8s_api_host']}:{bastion['k8s_api_port']}",
        f"{bastion['user']}@{bastion['host']}"
    ]
    subprocess.run(cmd, check=True)
    time.sleep(2)
    print(f'K8s 隧道已建立: {bind}:{lport} → {bastion["k8s_api_host"]}:{bastion["k8s_api_port"]}')
else:
    print(f'K8s 隧道已就绪: {bind}:{lport}')
```

---

## 验证连接

```python
import json, subprocess, os

PROJECT_ROOT = subprocess.check_output(
    ['git', 'rev-parse', '--show-toplevel'], text=True).strip()
k8s = json.load(open(os.path.join(PROJECT_ROOT, 'fast-harness/config/infrastructure.json')))['kubernetes']
kubeconfig = os.path.join(PROJECT_ROOT, k8s['kubeconfig_path'])
ns_prod    = k8s['namespaces']['prod']

env = {**os.environ, 'KUBECONFIG': kubeconfig}
subprocess.run(['kubectl', 'get', 'pods', '-n', ns_prod, '--request-timeout=5s'], env=env)
```

---

## 适用场景

- 查看 Pod / Deployment 状态
- 查看 Events 了解问题原因
- 查看日志辅助排障

---

## 可用命令

读取配置后构造命令（`KUBECONFIG` 和 `NS_PROD` 从 `infrastructure.json` 获取）：

```bash
# 读取配置（在所有 kubectl 操作前执行）
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
KUBECONFIG="$PROJECT_ROOT/$(python3 -c "import json; print(json.load(open('$PROJECT_ROOT/fast-harness/config/infrastructure.json'))['kubernetes']['kubeconfig_path'])")"
NS_PROD="$(python3 -c "import json; print(json.load(open('$PROJECT_ROOT/fast-harness/config/infrastructure.json'))['kubernetes']['namespaces']['prod'])")"
NS_DEV="$(python3 -c "import json; print(json.load(open('$PROJECT_ROOT/fast-harness/config/infrastructure.json'))['kubernetes']['namespaces']['dev'])")"

# 查看 Pod 列表
KUBECONFIG="$KUBECONFIG" kubectl get pods -n "$NS_PROD"

# 查看 Pod 详情
KUBECONFIG="$KUBECONFIG" kubectl describe pod <pod-name> -n "$NS_PROD"

# 查看 Pod 日志
KUBECONFIG="$KUBECONFIG" kubectl logs <pod-name> -n "$NS_PROD" --tail=100

# 查看 Deployment
KUBECONFIG="$KUBECONFIG" kubectl get deployments -n "$NS_PROD"

# 查看 Events（按时间排序）
KUBECONFIG="$KUBECONFIG" kubectl get events -n "$NS_PROD" --sort-by='.lastTimestamp' | tail -20

# 查看开发环境
KUBECONFIG="$KUBECONFIG" kubectl get pods -n "$NS_DEV"
```

---

## 注意事项

1. **只读**：只能执行 get / describe / logs，禁止 delete / exec / patch / apply
2. **自动初始化**：首次使用自动建立 SSH 隧道，已有隧道时跳过
3. **namespace**：需要指定 `-n`，从 `infrastructure.json` 的 `namespaces` 段读取
4. **日志大小**：日志查询建议加 `--tail` 限制行数
5. **token 有效期**：kubeconfig token 过期后需要重新生成
