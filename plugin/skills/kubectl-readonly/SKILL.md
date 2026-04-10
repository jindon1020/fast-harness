---
name: kubectl-readonly
description: 只读查询 K8s 资源状态。触发词：查 Pod、查 Deployment、查日志、K8s 状态、kubectl。
---

# kubectl 只读查询

## 自动初始化（首次使用）

**AI 自动检测项目根目录并执行以下命令**：

```bash
# 获取项目根目录（Git 根）
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
LOCAL_DIR="${PROJECT_ROOT}/.local"

# 建立 K8s API 隧道（后台运行）
source "${LOCAL_DIR}/bastion.env"
ssh -i "${LOCAL_DIR}/id_rsa" \
  -L 127.0.0.1:16443:172.16.37.101:6443 \
  "${BASTION_USER}@${BASTION_HOST}" -p "${BASTION_PORT}" -Nf &
```

## 验证端口状态

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" \
  kubectl get pods -n drama-prod --request-timeout=5s && echo " K8s API OK"
```

## 适用场景

- 查看 Pod/Deployment 状态
- 查看 Events 了解问题原因
- 查看日志辅助排障

## 可用 namespace

- `drama-prod` - 生产环境
- `drama-dev` - 开发环境
- `loki` - 日志服务
- `arms-prom` - 监控服务

## 可用命令

```bash
# 获取项目根目录（Git 根）
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig"

# 查看 Pod 列表
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl get pods -n drama-prod

# 查看 Pod 详情
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl describe pod <pod-name> -n drama-prod

# 查看 Pod 日志
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl logs <pod-name> -n drama-prod --tail=100

# 查看 Deployment
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl get deployments -n drama-prod

# 查看 Events
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl get events -n drama-prod --sort-by='.lastTimestamp' | tail -20
```

## 命令格式

```bash
KUBECONFIG="${PROJECT_ROOT}/.local/openclaw-readonly.kubeconfig" kubectl <command> -n <namespace>
```

## 注意事项

1. **只读**：只能执行 get/describe/logs，禁止 delete/exec/patch/apply
2. **自动初始化**：首次使用自动建立 SSH 隧道
3. **命名空间**：需要指定 namespace（-n 参数）
4. **日志大小**：日志查询建议加 --tail 限制行数
5. **token 有效期**：kubeconfig token 过期后需要重新生成
