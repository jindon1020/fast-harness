---
name: deploy-creation-tool-dev-command
description: 一键发布 creation-tool 当前分支到 dev 环境
---

# deploy-creation-tool-dev-command

## Task

将当前 `creation-tool` 工作区所在分支合并到远程 `dev` 分支，并通过国内堡垒机部署 dev 环境。

## Command Format

```text
/deploy-creation-tool-dev
```

## Fixed Deployment Target

- Repository: `creation-tool`
- Target branch: `dev`
- Bastion: `39.106.16.60:50245`
- SSH user: `zhaojindong`
- SSH key: `/Users/geralt/.ssh/id_rsa`
- Remote project directory: `~/creation-tool`
- Remote deploy command: `make deploy-dev-aidrama`

## Safety Rules

1. Only run this command from a `creation-tool` git worktree.
2. Before switching branches or merging, inspect `git status --short`.
3. If there are uncommitted local changes, stop and ask the user whether to commit, stash, or abort. Do not discard local changes.
4. Try to resolve merge conflicts automatically only when the correct resolution is mechanically clear from the current branch intent and `dev` state.
5. If a conflict requires product or business judgment, stop and report the conflicting files and conflict summary instead of guessing.
6. Do not run destructive commands such as `git reset --hard`, `git checkout -- <file>`, or `git clean` unless the user explicitly approves them after seeing the exact risk.
7. After a successful local merge, push `dev` to `origin` before deploying on the bastion.

## Execution Steps

### Phase 0: Validate Context

Run:

```bash
pwd
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git status --short
```

Validate that the repository root basename is `creation-tool`. Save the current branch as `SOURCE_BRANCH`.

If `SOURCE_BRANCH` is empty, stop and report that detached HEAD cannot be deployed safely.

If `git status --short` is non-empty, stop and ask the user how to handle local changes.

### Phase 1: Merge Current Branch Into dev

Run:

```bash
git fetch origin
git switch dev || git switch -c dev --track origin/dev
git pull --ff-only origin dev
git merge --no-ff "$SOURCE_BRANCH"
```

If merge conflicts occur:

1. Inspect `git status --short` and conflicted files.
2. Resolve conflicts directly when the desired result is clear.
3. Run `git add <resolved-files>` and complete the merge commit with `git commit` if needed.
4. If any conflict is ambiguous, stop and report the unresolved files.

After merge completes, run:

```bash
git status --short
git log --oneline -5
```

If `git status --short` is clean, push:

```bash
git push origin dev
```

### Phase 2: Deploy Through Bastion

Connect to the bastion and deploy:

```bash
ssh -i /Users/geralt/.ssh/id_rsa -p 50245 zhaojindong@39.106.16.60 'cd ~/creation-tool && git fetch origin dev && git switch dev && git pull --ff-only origin dev && make deploy-dev-aidrama'
```

If `~/creation-tool` does not exist, stop and report the missing directory. Do not guess alternate production paths unless the user provides one.

### Phase 3: Report

Return a concise deployment report:

- source branch merged
- local dev commit hash
- push result
- bastion pull result
- deploy command result
- any warnings or manual follow-up required
