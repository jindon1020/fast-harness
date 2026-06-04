#!/usr/bin/env python3
"""
Deploy runtime service to Aliyun server.
Reads configuration from runtime/.env and executes remote deployment.
"""

import os
import sys
import subprocess
from pathlib import Path


def load_env_config(env_path: Path) -> dict:
    """Load deployment configuration from .env file."""
    if not env_path.exists():
        print(f"❌ Error: {env_path} not found", file=sys.stderr)
        sys.exit(1)

    config = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

    required = ["DEPLOY_SSH_HOST", "DEPLOY_SSH_USER", "DEPLOY_SSH_PASSWORD", "DEPLOY_REMOTE_PATH"]
    missing = [k for k in required if k not in config]
    if missing:
        print(f"❌ Missing configuration in .env: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    return config


def check_sshpass():
    """Check if sshpass is installed, attempt to install if not."""
    try:
        subprocess.run(["which", "sshpass"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        print("⚠️  sshpass not found. Attempting to install via Homebrew...")
        try:
            subprocess.run(["brew", "install", "sshpass"], check=True)
            print("✅ sshpass installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install sshpass. Please install manually:", file=sys.stderr)
            print("   brew install sshpass", file=sys.stderr)
            return False


def check_remote_path(host: str, user: str, password: str, remote_path: str) -> bool:
    """Check if remote path exists on the server."""
    check_cmd = [
        "sshpass", "-p", password,
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{user}@{host}",
        f"test -d {remote_path} && echo 'EXISTS' || echo 'NOT_FOUND'"
    ]

    try:
        result = subprocess.run(check_cmd, check=True, capture_output=True, text=True)
        return "EXISTS" in result.stdout
    except subprocess.CalledProcessError:
        return False


def find_remote_paths(host: str, user: str, password: str) -> list:
    """Search for common deployment paths on the server."""
    search_cmd = [
        "sshpass", "-p", password,
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{user}@{host}",
        "find /opt /root /home -maxdepth 3 -name 'fast-harness' -type d 2>/dev/null || true"
    ]

    try:
        result = subprocess.run(search_cmd, check=True, capture_output=True, text=True)
        paths = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
        return paths
    except subprocess.CalledProcessError:
        return []


def deploy(config: dict):
    """Execute remote deployment via SSH."""
    host = config["DEPLOY_SSH_HOST"]
    user = config["DEPLOY_SSH_USER"]
    password = config["DEPLOY_SSH_PASSWORD"]
    remote_path = config["DEPLOY_REMOTE_PATH"]

    print(f"🚀 Deploying to {user}@{host}:{remote_path}")

    # Verify remote path exists
    print("🔍 Verifying remote path...")
    if not check_remote_path(host, user, password, remote_path):
        print(f"❌ Error: Remote path {remote_path} does not exist", file=sys.stderr)
        print("\n🔎 Searching for fast-harness on the server...")
        found_paths = find_remote_paths(host, user, password)

        if found_paths:
            print("📍 Found these paths:")
            for path in found_paths:
                print(f"   - {path}")
            print(f"\n💡 Update DEPLOY_REMOTE_PATH in runtime/.env to one of the above paths")
        else:
            print("📍 No fast-harness directory found on the server")
            print("\n💡 You may need to:")
            print("   1. Clone the repository on the server first")
            print("   2. Or update DEPLOY_REMOTE_PATH in runtime/.env to the correct path")

        sys.exit(1)

    # Build remote command
    remote_commands = [
        f"cd {remote_path}",
        "git fetch origin",
        "git pull origin main",
        "cd runtime",
        # Try to restart service (handle different deployment methods)
        "(systemctl restart fast-harness-runtime 2>/dev/null || "
        "docker-compose restart runtime 2>/dev/null || "
        "pkill -f 'uvicorn.*main:app' && nohup python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &) || "
        "echo '⚠️  Could not restart service automatically. Please restart manually.'"
    ]

    remote_cmd = " && ".join(remote_commands)

    # Execute SSH command with sshpass
    ssh_cmd = [
        "sshpass", "-p", password,
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{user}@{host}",
        remote_cmd
    ]

    try:
        print("📡 Connecting to server...")
        result = subprocess.run(ssh_cmd, check=False, capture_output=False, text=True)

        if result.returncode == 0:
            print("✅ Deployment completed successfully!")
        else:
            print(f"⚠️  Deployment completed with warnings (exit code: {result.returncode})")
            print("Check server logs if the service didn't restart properly")

    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Deployment interrupted by user")
        sys.exit(130)


def main():
    """Main entry point."""
    # Find project root and .env path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent  # .claude/skills/deploy-runtime -> project root
    env_path = project_root / "runtime" / ".env"

    print(f"📋 Reading configuration from {env_path}")
    config = load_env_config(env_path)

    if not check_sshpass():
        sys.exit(1)

    deploy(config)


if __name__ == "__main__":
    main()
