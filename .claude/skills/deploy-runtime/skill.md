---
skill: deploy-runtime
description: Deploy runtime service to Aliyun server with path verification
tags: [deployment, ssh, remote]
---

# Deploy Runtime to Aliyun

This skill reads server configuration from `runtime/.env` and deploys the latest runtime code to the Aliyun server.

## What it does

1. Reads SSH credentials from `runtime/.env`
2. **Verifies the remote path exists** (prevents deployment failures)
3. Connects to the remote Aliyun server
4. Pulls the latest code from git
5. Restarts the runtime service

## Usage

Simply invoke this skill:
```
/deploy-runtime
```

## Features

### Path Verification
Before deploying, the skill checks if `DEPLOY_REMOTE_PATH` exists on the server:
- ✅ If found: proceeds with deployment
- ❌ If not found: searches for `fast-harness` directories and suggests corrections

### Auto-detection
If the configured path is wrong, the skill will:
1. Search common locations (`/opt`, `/root`, `/home`)
2. Display all found `fast-harness` directories
3. Suggest updating the `.env` configuration

### Smart Service Restart
Automatically detects and uses the appropriate restart method:
1. systemd service (`systemctl restart`)
2. Docker Compose (`docker-compose restart`)
3. Process kill and restart (`pkill` + `uvicorn`)

## Configuration

Server configuration is read from `runtime/.env`:
- `DEPLOY_SSH_HOST`: Server IP address (e.g., `8.137.19.64`)
- `DEPLOY_SSH_USER`: SSH username (e.g., `root`)
- `DEPLOY_SSH_PASSWORD`: SSH password
- `DEPLOY_REMOTE_PATH`: Project path on server (e.g., `/opt/fast-harness`)

## Error Handling

### Wrong Path Error
```
❌ Error: Remote path /root/fast-harness does not exist

🔎 Searching for fast-harness on the server...
📍 Found these paths:
   - /opt/fast-harness

💡 Update DEPLOY_REMOTE_PATH in runtime/.env to one of the above paths
```

### First-time Setup
If no project directory is found:
```
💡 You may need to:
   1. Clone the repository on the server first
   2. Or update DEPLOY_REMOTE_PATH in runtime/.env to the correct path
```
