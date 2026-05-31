"""
Git operations — clone, pull, status, branch management.
Supports GitHub, 阿里云·云效 (Codeup), and generic Git providers.
"""

import logging
import subprocess
import re
import shlex
import shutil
from urllib.parse import quote
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from src.config import settings

logger = logging.getLogger(__name__)

FAST_HARNESS_INSTALL_COMMAND = (
    "curl -fsSL https://cdn.jsdelivr.net/gh/jindon1020/fast-harness@main/install.sh "
    "| bash -s -- --force"
)
FAST_HARNESS_MANAGED_PATHS = [
    ".cursor",
    ".ether",
    ".qoder",
    ".claude",
    ".codex",
    ".gemini",
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "QODER.md",
]


class GitProvider(str, Enum):
    github = "github"
    codeup = "codeup"  # 阿里云·云效
    gitlab = "gitlab"
    generic = "generic"


# Known host patterns for auto-detection
PROVIDER_HOSTS = {
    GitProvider.github: ["github.com"],
    GitProvider.codeup: ["codeup.aliyun.com", "codeup.aliyuncs.com"],
    GitProvider.gitlab: ["gitlab.com"],
}


def detect_provider(url: str) -> GitProvider:
    for provider, hosts in PROVIDER_HOSTS.items():
        for host in hosts:
            if host in url:
                return provider
    return GitProvider.generic


def _build_auth_url(url: str, provider: GitProvider) -> str:
    """Inject token into HTTPS URL for authentication."""
    if not url.startswith("https://"):
        return url
    if provider == GitProvider.github and settings.git_github_token:
        token = quote(settings.git_github_token, safe="")
        return re.sub(r"https://", f"https://{token}@", url, count=1)
    if provider == GitProvider.codeup and settings.git_codeup_token:
        token = quote(settings.git_codeup_token, safe="")
        if settings.git_codeup_user:
            user = quote(settings.git_codeup_user, safe="")
            return re.sub(r"https://", f"https://{user}:{token}@", url, count=1)
        return re.sub(r"https://", f"https://{token}@", url, count=1)
    return url


def _strip_auth_from_url(url: str) -> str:
    return re.sub(r"https://[^@/\s]+@", "https://", url)


def _sanitize_git_output(output: str) -> str:
    return _strip_auth_from_url(output)


@dataclass
class RepoInfo:
    name: str
    url: str
    provider: GitProvider
    branch: str = "main"
    local_path: Optional[Path] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "provider": self.provider.value,
            "branch": self.branch,
            "local_path": str(self.local_path) if self.local_path else None,
        }


@dataclass
class GitStatus:
    branch: str = ""
    ahead: int = 0
    behind: int = 0
    modified: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    clean: bool = True


def _run(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    env = {}
    if settings.git_ssh_key_path:
        ssh_key = str(Path(settings.git_ssh_key_path).expanduser().resolve())
        env["GIT_SSH_COMMAND"] = f"ssh -i {shlex.quote(ssh_key)} -o StrictHostKeyChecking=accept-new"

    try:
        r = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, env={**__import__("os").environ, **env},
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def _detect_default_branch(auth_url: str) -> str:
    """Detect remote HEAD branch via ls-remote."""
    rc, stdout, stderr = _run(
        ["git", "ls-remote", "--symref", auth_url, "HEAD"],
        Path.cwd(), timeout=30
    )
    if rc == 0 and stdout:
        for line in stdout.split("\n"):
            if "ref:" in line and "HEAD" in line:
                # Format: "ref: refs/heads/BRANCH\tHEAD"
                ref = line.strip().split("\t")[0]
                branch = ref.split("/")[-1]
                return branch
    return settings.git_default_branch


def remote_branches(url: str) -> list[str]:
    """List branch names directly from the remote repository."""
    provider = detect_provider(url)
    auth_url = _build_auth_url(url, provider)
    rc, stdout, _stderr = _run(["git", "ls-remote", "--heads", auth_url], Path.cwd(), timeout=30)
    if rc != 0 or not stdout:
        return []
    branches_list = []
    for line in stdout.split("\n"):
        if "refs/heads/" not in line:
            continue
        branches_list.append(line.rsplit("refs/heads/", 1)[1].strip())
    return sorted(set(branches_list))


def _fetch_remote_heads(repo_path: Path, url: Optional[str] = None, timeout: int = 60) -> tuple[int, str, str]:
    """Fetch remote heads using freshly configured credentials, not cached origin auth."""
    remote_url = url or _get_remote_url(repo_path)
    provider = detect_provider(remote_url)
    auth_url = _build_auth_url(remote_url, provider)
    return _run(
        ["git", "fetch", "--prune", auth_url, "+refs/heads/*:refs/remotes/origin/*"],
        repo_path,
        timeout=timeout,
    )


def _install_fast_harness_suite(repo_path: Path) -> None:
    """Install or refresh fast-harness project files inside a workspace worktree."""
    logger.info("Installing fast-harness suite in %s", repo_path)
    rc, stdout, stderr = _run(
        ["bash", "-lc", FAST_HARNESS_INSTALL_COMMAND],
        repo_path,
        timeout=300,
    )
    if rc != 0:
        message = stderr or stdout or "unknown error"
        raise RuntimeError(f"fast-harness install failed: {message}")


def _reset_fast_harness_managed_paths(repo_path: Path) -> None:
    """Discard installer-managed file changes before switching branches."""
    rc, stdout, _stderr = _run(["git", "ls-files", *FAST_HARNESS_MANAGED_PATHS], repo_path, timeout=30)
    if rc == 0 and stdout:
        tracked_paths = [line for line in stdout.splitlines() if line.strip()]
        if tracked_paths:
            _run(["git", "checkout", "--", *tracked_paths], repo_path, timeout=60)
    _run(["git", "clean", "-fd", "--", *FAST_HARNESS_MANAGED_PATHS], repo_path, timeout=60)


def clone(url: str, target_dir: Path, branch: Optional[str] = None, directory_name: Optional[str] = None) -> RepoInfo:
    """Clone a repository into target_dir. Auto-detects default branch if not specified."""
    provider = detect_provider(url)
    auth_url = _build_auth_url(url, provider)

    # Derive repo name from URL (used as directory name unless overridden)
    url_name = url.rstrip("/").split("/")[-1]
    if url_name.endswith(".git"):
        url_name = url_name[:-4]
    dir_name = directory_name or url_name

    repo_path = target_dir / dir_name
    if repo_path.exists():
        logger.info("Repo %s already exists at %s, pulling instead", dir_name, repo_path)
        return pull(repo_path)

    # Detect branch
    if branch is None:
        branch = _detect_default_branch(auth_url)
        logger.info("Detected default branch: %s", branch)

    cmd = ["git", "clone", "--branch", branch, auth_url, dir_name]
    logger.info("Cloning %s (provider=%s, branch=%s) into %s", dir_name, provider.value, branch, target_dir)
    rc, stdout, stderr = _run(cmd, target_dir)
    if rc != 0:
        raise RuntimeError(f"Clone failed: {stderr}")

    return RepoInfo(name=dir_name, url=url, provider=provider, branch=branch, local_path=repo_path)


def create_worktree(url: str, source_dir: Path, worktree_path: Path, branch: Optional[str] = None) -> RepoInfo:
    """Create an isolated git worktree for a branch from a shared source clone."""
    provider = detect_provider(url)
    auth_url = _build_auth_url(url, provider)
    repo_name = worktree_path.name
    source_repo = source_dir / repo_name
    source_dir.mkdir(parents=True, exist_ok=True)
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    if source_repo.exists() and not (source_repo / ".git").exists():
        logger.warning("Removing invalid source clone cache at %s", source_repo)
        shutil.rmtree(source_repo)

    if not source_repo.exists():
        rc, _stdout, stderr = _run(["git", "clone", auth_url, repo_name], source_dir)
        if rc != 0:
            raise RuntimeError(f"Source clone failed: {_sanitize_git_output(stderr)}")
        _run(["git", "remote", "set-url", "origin", url], source_repo)
    else:
        _run(["git", "remote", "set-url", "origin", url], source_repo)

    rc, _stdout, stderr = _fetch_remote_heads(source_repo, url=url, timeout=60)
    if rc != 0:
        raise RuntimeError(f"Source fetch failed: {_sanitize_git_output(stderr)}")

    if branch is None:
        branch = _detect_default_branch(auth_url)

    rc, _stdout, stderr = _run(
        ["git", "worktree", "add", str(worktree_path), f"origin/{branch}"],
        source_repo,
        timeout=120,
    )
    if rc != 0:
        raise RuntimeError(f"Worktree creation failed: {_sanitize_git_output(stderr)}")

    try:
        _install_fast_harness_suite(worktree_path)
    except RuntimeError:
        _run(["git", "worktree", "remove", "--force", str(worktree_path)], source_repo, timeout=60)
        raise

    return RepoInfo(name=repo_name, url=url, provider=provider, branch=branch, local_path=worktree_path)


def pull(repo_path: Path, branch: Optional[str] = None) -> RepoInfo:
    """Pull latest changes in an existing repo."""
    if not (repo_path / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_path}")

    if branch:
        _run(["git", "checkout", branch], repo_path)

    current_branch = _get_current_branch(repo_path)
    rc, stdout, stderr = _fetch_remote_heads(repo_path)
    if rc == 0:
        rc, stdout, stderr = _run(["git", "merge", "--ff-only", f"origin/{current_branch}"], repo_path)
    if rc != 0:
        logger.warning("Pull may have conflicts: %s", _sanitize_git_output(stderr))

    # Read remote info
    remote_url = _get_remote_url(repo_path)
    return RepoInfo(
        name=repo_path.name, url=remote_url,
        provider=detect_provider(remote_url),
        branch=current_branch, local_path=repo_path,
    )


def checkout(repo_path: Path, branch: str) -> RepoInfo:
    """Checkout a local or remote branch and fast-forward it when possible."""
    if not (repo_path / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_path}")

    _fetch_remote_heads(repo_path, timeout=60)
    _reset_fast_harness_managed_paths(repo_path)
    rc, _stdout, stderr = _run(["git", "checkout", branch], repo_path)
    if rc != 0:
        rc, _stdout, stderr = _run(["git", "checkout", "-B", branch, f"origin/{branch}"], repo_path)
    if rc != 0:
        rc, _stdout, stderr = _run(["git", "checkout", "--detach", f"origin/{branch}"], repo_path)
    if rc != 0:
        raise RuntimeError(f"Checkout failed: {stderr}")

    rc, _stdout, stderr = _run(["git", "merge", "--ff-only", f"origin/{branch}"], repo_path)
    if rc != 0:
        logger.warning("Pull may have conflicts: %s", _sanitize_git_output(stderr))

    _install_fast_harness_suite(repo_path)

    remote_url = _get_remote_url(repo_path)
    return RepoInfo(
        name=repo_path.name,
        url=remote_url,
        provider=detect_provider(remote_url),
        branch=branch,
        local_path=repo_path,
    )


def status(repo_path: Path) -> GitStatus:
    """Get the working tree status of a repo."""
    if not (repo_path / ".git").exists():
        return GitStatus()

    branch = _get_current_branch(repo_path)

    # Fetch to get ahead/behind
    _fetch_remote_heads(repo_path, timeout=30)

    # Ahead/behind
    ahead = behind = 0
    rc, stdout, _ = _run(["git", "rev-list", "--left-right", "--count", f"{branch}...origin/{branch}"], repo_path)
    if rc == 0 and stdout:
        parts = stdout.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])

    # Modified files
    _, modified_out, _ = _run(["git", "diff", "--name-only"], repo_path)
    modified = [f for f in modified_out.split("\n") if f]

    # Untracked files
    _, untracked_out, _ = _run(["git", "ls-files", "--others", "--exclude-standard"], repo_path)
    untracked = [f for f in untracked_out.split("\n") if f]

    return GitStatus(
        branch=branch, ahead=ahead, behind=behind,
        modified=modified, untracked=untracked,
        clean=not modified and not untracked,
    )


def branches(repo_path: Path) -> list[str]:
    """List branches in a repo."""
    if not (repo_path / ".git").exists():
        return []
    _fetch_remote_heads(repo_path, timeout=60)
    rc, stdout, _ = _run(["git", "branch", "-a"], repo_path)
    if rc != 0:
        return []
    lines = []
    for line in stdout.split("\n"):
        line = line.strip().lstrip("*").strip()
        if line and not line.startswith("remotes/"):
            lines.append(line)
        elif line and "HEAD" not in line:
            lines.append(line.replace("remotes/origin/", ""))
    return sorted(set(lines))


def _get_remote_url(repo_path: Path) -> str:
    rc, stdout, _ = _run(["git", "remote", "get-url", "origin"], repo_path)
    # Strip embedded tokens from URL for safe display
    url = stdout if rc == 0 else ""
    return _strip_auth_from_url(url)


def _get_current_branch(repo_path: Path) -> str:
    rc, stdout, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    return stdout if rc == 0 else settings.git_default_branch
