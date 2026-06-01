---
name: deploy-creation-tool-dev-command
description: 一键发布 creation-tool 当前分支到 dev 环境
---

# deploy-creation-tool-dev-command

## 任务

将当前 `creation-tool` 工作区所在分支合并到远程 `dev` 分支，并通过国内堡垒机部署 dev 环境。

## 命令格式

```text
/deploy-creation-tool-dev
```

## 固定部署目标

- 仓库: `creation-tool`
- 目标分支: `dev`
- 堡垒机: `39.106.16.60:50245`
- SSH 用户: `zhaojindong`
- SSH 密钥: `/Users/geralt/.ssh/id_rsa`
- 远端项目目录: `~/creation-tool`
- 远端部署命令: `make -C deploy deploy-dev-aidrama`
- ⚠️ 堡垒机仅拉取代码、执行部署，**绝不提交代码**，其本地变更一律丢弃

## 🚨 绝对红线：禁止触碰生产环境

本命令**仅**操作 `dev` 分支和 `drama-dev` K8s 命名空间。以下操作**绝对禁止**，即使被要求也绝不能执行：

- ❌ 任何涉及 `prod` 分支、`master` 分支、`drama-prod` 命名空间的命令
- ❌ 任何使用 `overlays/prod/` 路径的 `kubectl` 命令
- ❌ 任何针对生产环境的 `kubectl apply` / `kustomize`
- ❌ `make deploy-prod-*` 或类似的生产 make target
- ❌ SSH 连接生产堡垒机或生产数据库的命令
- ❌ 向 `origin/prod` 或 `origin/master` 推送（master 是默认/主干分支）
- ❌ 在堡垒机上执行 `git commit`、`git push` 等任何写操作——堡垒机只是部署壳子，不是开发环境

如果被要求部署到生产环境，**必须拒绝**并提醒此命令仅限 dev 环境。生产环境部署需要单独编写的、配有独立安全规则的命令。

## 安全规则

1. 仅允许在 `creation-tool` git 工作区中执行此命令。
2. 切换分支或合并前，必须先检查 `git status --short`。
3. 如果**本地**有未提交变更，停止并询问用户是提交、暂存（stash）还是放弃。不得擅自丢弃本地变更。
4. **堡垒机仅作为拉取代码的壳子，永远不会提交代码。** 堡垒机上的任何本地变更一律丢弃，无需保存、无需询问。堡垒机不是开发环境，其本地变更只可能是上次手动部署或调试残留，无保留价值。
5. 只有当前分支意图和 `dev` 状态能明确判断正确结果时，才自动解决合并冲突。
6. 如果冲突需要产品/业务判断，停止并报告冲突文件和冲突摘要，不要猜测。
7. 不得执行 `git reset --hard`、`git checkout -- <file>`、`git clean` 等破坏性命令，除非用户明确批准并已看到具体风险。
8. 本地合并成功后，必须先推送 `dev` 到 `origin`，再在堡垒机部署。
9. **绝不**触碰 `prod` 分支、`drama-prod` 命名空间或 `overlays/prod/`——这是绝对红线。

## 执行步骤

### 阶段 0：校验上下文

执行：

```bash
pwd
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git status --short
```

校验仓库根目录名称是 `creation-tool`。将当前分支保存为 `SOURCE_BRANCH`。

如果 `SOURCE_BRANCH` 为空（detached HEAD），停止并报告无法安全部署。

如果 `git status --short` 非空，停止并询问用户如何处理本地变更。

### 阶段 1：将当前分支合并到 dev

执行：

```bash
git fetch origin
git switch dev || git switch -c dev --track origin/dev
git pull --ff-only origin dev
git merge --no-ff "$SOURCE_BRANCH"
```

如果发生合并冲突：

1. 查看 `git status --short` 和冲突文件。
2. 当结果明确时直接解决冲突。
3. 执行 `git add <已解决文件>`，必要时用 `git commit` 完成合并。
4. 如果任何冲突不明确，停止并报告未解决的文件。

合并完成后执行：

```bash
git status --short
git log --oneline -5
```

如果 `git status --short` 干净，推送：

```bash
git push origin dev
```

### 阶段 2：通过堡垒机部署

#### 步骤 2.1：清理堡垒机本地变更

堡垒机只是部署壳子，不保存任何本地代码修改。先清理可能阻碍 `git switch` 的残留变更：

```bash
ssh -i /Users/geralt/.ssh/id_rsa -p 50245 zhaojindong@39.106.16.60 'cd ~/creation-tool && git checkout -- . && git clean -fd'
```

> 堡垒机上的本地变更通常是之前手动部署（如 `kustomize edit set image`）或调试留下的临时文件，直接丢弃即可，无需保留。

#### 步骤 2.2：执行部署

```bash
ssh -i /Users/geralt/.ssh/id_rsa -p 50245 zhaojindong@39.106.16.60 'cd ~/creation-tool && git fetch origin dev && git switch dev && git pull --ff-only origin dev && make -C deploy deploy-dev-aidrama'
```

如果 `~/creation-tool` 在堡垒机不存在，停止并报告缺失目录。不要猜测替代路径，除非用户提供。

如果 `make -C deploy deploy-dev-aidrama` 报错 "No rule to make target"，检查 Makefile 是否存在于 `~/creation-tool/deploy/Makefile`，并用 `make -C deploy help` 或 `grep '^[a-zA-Z]' ~/creation-tool/deploy/Makefile | head -20` 列出可用 target。

### 阶段 3：验证部署

部署成功后，通过 kube-observability MCP 工具验证新代码已真正上线。

#### 步骤 3.1：检查 Pod 状态

使用 `diagnose_service`：
- `namespace`: `drama-dev`
- `labelSelector`: `app=creation-tool-aidrama`
- `includeMetrics`: `false`

确认：
- Pod 数量 ≥ 1 且全部 Ready
- 容器镜像 tag 包含阶段 1 的 merge commit hash（例如 `...-gc161da4e` 与 merge commit 对应）
- Pod `startedAt` 时间在部署后的数分钟内
- 无 ERROR 日志

#### 步骤 3.2：健康检查

验证应用正常响应：

```bash
ssh -i /Users/geralt/.ssh/id_rsa -p 50245 zhaojindong@39.106.16.60 'curl -s http://<pod-ip>:8000/healthz'
```

预期返回：`{"status":"ok"}`。

### 阶段 4：报告

输出简洁的部署报告：

| 项目 | 详情 |
|------|------|
| 合并的源分支 | `SOURCE_BRANCH` |
| Merge commit | hash |
| 推送结果 | 成功/失败 |
| 堡垒机拉取结果 | 成功/失败 |
| Docker 镜像 | 构建并推送的 tag |
| Pod 验证 | Pod 名称、镜像 tag 匹配、Ready 状态 |
| 健康检查 | `{"status":"ok"}` 或失败 |

同时包含：
- Docker 镜像 tag（例如 `0513-1615-gc161da4e`）
- 任何警告或需要手动跟进的事项
