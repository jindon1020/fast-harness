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


def _user_git_config(user_id: Optional[str] = None) -> dict[str, str]:
    if not user_id:
        return {}
    try:
        user = settings.get_user(user_id)
    except ValueError:
        return {}
    return user.get("git", {}) or {}


def _build_auth_url(url: str, provider: GitProvider, user_id: Optional[str] = None) -> str:
    """Inject token into HTTPS URL for authentication."""
    if not url.startswith("https://"):
        return url
    user_git = _user_git_config(user_id)
    if provider == GitProvider.github and (user_git.get("github_token") or settings.git_github_token):
        token = quote(user_git.get("github_token") or settings.git_github_token, safe="")
        return re.sub(r"https://", f"https://{token}@", url, count=1)
    if provider == GitProvider.codeup and (user_git.get("codeup_token") or settings.git_codeup_token):
        token = quote(user_git.get("codeup_token") or settings.git_codeup_token, safe="")
        codeup_user = user_git.get("codeup_user") or settings.git_codeup_user
        if codeup_user:
            user = quote(codeup_user, safe="")
            return re.sub(r"https://", f"https://{user}:{token}@", url, count=1)
        return re.sub(r"https://", f"https://{token}@", url, count=1)
    return url


def _strip_auth_from_url(url: str) -> str:
    return re.sub(r"https://[^@/\s]+@", "https://", url)


def _sanitize_git_output(output: str) -> str:
    return _strip_auth_from_url(output)


def _fallback_email(user_id: str) -> str:
    safe_user = re.sub(r"[^A-Za-z0-9_.-]+", "-", user_id).strip(".-") or "user"
    return f"{safe_user}@fast-harness.local"


def configure_worktree_identity(repo_path: Path, user_id: Optional[str] = None) -> None:
    """Apply per-user git author and HTTPS credentials to this worktree only."""
    if not user_id or not (repo_path / ".git").exists():
        return
    try:
        user = settings.get_user(user_id)
    except ValueError:
        return

    user_git = user.get("git", {}) or {}
    name = user_git.get("name") or user.get("name") or user_id
    email = user_git.get("email") or _fallback_email(user_id)
    _run(["git", "config", "extensions.worktreeConfig", "true"], repo_path, timeout=30)
    _run(["git", "config", "--worktree", "user.name", name], repo_path, timeout=30)
    _run(["git", "config", "--worktree", "user.email", email], repo_path, timeout=30)

    helper = _credential_helper(user_git)
    if helper:
        _run(["git", "config", "--worktree", "credential.helper", helper], repo_path, timeout=30)


def _credential_helper(user_git: dict[str, str]) -> str:
    codeup_user = user_git.get("codeup_user", "")
    codeup_token = user_git.get("codeup_token", "")
    codeup_token_env = user_git.get("codeup_token_env", "")
    if not codeup_user or not (codeup_token or codeup_token_env):
        return ""
    username = f"username={_shell_single_quote(codeup_user)}"
    if codeup_token_env:
        password = f"password=\"${{{codeup_token_env}}}\""
    else:
        password = f"password={_shell_single_quote(codeup_token)}"
    return (
        "!f() { "
        "test \"$1\" = get || exit 0; "
        "while IFS= read -r line; do "
        "test \"$line\" = host=codeup.aliyun.com && match=1; "
        "test \"$line\" = host=codeup.aliyuncs.com && match=1; "
        "done; "
        "test \"$match\" = 1 || exit 0; "
        f"printf '%s\\n' {username}; "
        f"printf '%s\\n' {password}; "
        "}; f"
    )


def _shell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


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


@dataclass
class GitActionResult:
    status: str
    branch: str = ""
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "branch": self.branch,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


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


def remote_branches(url: str, user_id: Optional[str] = None) -> list[str]:
    """List branch names directly from the remote repository."""
    provider = detect_provider(url)
    auth_url = _build_auth_url(url, provider, user_id=user_id)
    rc, stdout, _stderr = _run(["git", "ls-remote", "--heads", auth_url], Path.cwd(), timeout=30)
    if rc != 0 or not stdout:
        return []
    branches_list = []
    for line in stdout.split("\n"):
        if "refs/heads/" not in line:
            continue
        branches_list.append(line.rsplit("refs/heads/", 1)[1].strip())
    return sorted(set(branches_list))


def _fetch_remote_heads(
    repo_path: Path,
    url: Optional[str] = None,
    timeout: int = 60,
    user_id: Optional[str] = None,
) -> tuple[int, str, str]:
    """Fetch remote heads using freshly configured credentials, not cached origin auth."""
    remote_url = url or _get_remote_url(repo_path)
    provider = detect_provider(remote_url)
    auth_url = _build_auth_url(remote_url, provider, user_id=user_id)
    return _run(
        ["git", "fetch", "--prune", auth_url, "+refs/heads/*:refs/remotes/origin/*"],
        repo_path,
        timeout=timeout,
    )


def normalize_branch_name(branch: Optional[str]) -> Optional[str]:
    """Normalize branch labels copied from git branch output or UI fallbacks."""
    if branch is None:
        return None
    value = branch.strip()
    while value[:1] in {"*", "+"}:
        value = value[1:].strip()
    for prefix in ("remotes/origin/", "origin/", "refs/heads/"):
        if value.startswith(prefix):
            value = value[len(prefix):].strip()
    return value or None


def _install_fast_harness_suite(repo_path: Path) -> None:
    """Install or refresh fast-harness project files inside a workspace worktree."""
    logger.info("Installing fast-harness suite in %s", repo_path)
    rc, stdout, stderr = _run(
        ["bash", "-lc", _fast_harness_install_command()],
        repo_path,
        timeout=300,
    )
    if rc != 0:
        message = stderr or stdout or "unknown error"
        raise RuntimeError(f"fast-harness install failed: {message}")


def _fast_harness_install_command() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    install_script = repo_root / "install.sh"
    if install_script.exists():
        return (
            f"bash {shlex.quote(str(install_script))} --force "
            f"--local {shlex.quote(str(repo_root))}"
        )
    return FAST_HARNESS_INSTALL_COMMAND


def _reset_fast_harness_managed_paths(repo_path: Path) -> None:
    """Discard installer-managed file changes before switching branches."""
    rc, stdout, _stderr = _run(["git", "ls-files", *FAST_HARNESS_MANAGED_PATHS], repo_path, timeout=30)
    if rc == 0 and stdout:
        tracked_paths = [line for line in stdout.splitlines() if line.strip()]
        if tracked_paths:
            _run(["git", "checkout", "--", *tracked_paths], repo_path, timeout=60)
    _run(["git", "clean", "-fd", "--", *FAST_HARNESS_MANAGED_PATHS], repo_path, timeout=60)


def clone(
    url: str,
    target_dir: Path,
    branch: Optional[str] = None,
    directory_name: Optional[str] = None,
    user_id: Optional[str] = None,
) -> RepoInfo:
    """Clone a repository into target_dir. Auto-detects default branch if not specified."""
    provider = detect_provider(url)
    auth_url = _build_auth_url(url, provider, user_id=user_id)

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
    configure_worktree_identity(repo_path, user_id=user_id)

    return RepoInfo(name=dir_name, url=url, provider=provider, branch=branch, local_path=repo_path)


def create_worktree(
    url: str,
    source_dir: Path,
    worktree_path: Path,
    branch: Optional[str] = None,
    user_id: Optional[str] = None,
) -> RepoInfo:
    """Create an isolated git worktree for a branch from a shared source clone."""
    provider = detect_provider(url)
    auth_url = _build_auth_url(url, provider, user_id=user_id)
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

    rc, _stdout, stderr = _fetch_remote_heads(source_repo, url=url, timeout=60, user_id=user_id)
    if rc != 0:
        raise RuntimeError(f"Source fetch failed: {_sanitize_git_output(stderr)}")

    if branch is None:
        branch = _detect_default_branch(auth_url)
    branch = normalize_branch_name(branch)
    if not branch:
        raise RuntimeError("Branch is required")

    rc, _stdout, stderr = _run(
        ["git", "worktree", "add", str(worktree_path), f"origin/{branch}"],
        source_repo,
        timeout=120,
    )
    if rc != 0:
        raise RuntimeError(f"Worktree creation failed: {_sanitize_git_output(stderr)}")

    configure_worktree_identity(worktree_path, user_id=user_id)

    try:
        _install_fast_harness_suite(worktree_path)
    except RuntimeError:
        _run(["git", "worktree", "remove", "--force", str(worktree_path)], source_repo, timeout=60)
        raise

    return RepoInfo(name=repo_name, url=url, provider=provider, branch=branch, local_path=worktree_path)


def pull(repo_path: Path, branch: Optional[str] = None, user_id: Optional[str] = None) -> RepoInfo:
    """Pull latest changes in an existing repo."""
    if not (repo_path / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_path}")

    branch = normalize_branch_name(branch)
    if branch:
        _run(["git", "checkout", branch], repo_path)

    current_branch = _get_current_branch(repo_path)
    configure_worktree_identity(repo_path, user_id=user_id)
    rc, stdout, stderr = _fetch_remote_heads(repo_path, user_id=user_id)
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


def checkout(repo_path: Path, branch: str, user_id: Optional[str] = None) -> RepoInfo:
    """Checkout a local or remote branch and fast-forward it when possible."""
    if not (repo_path / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_path}")
    branch = normalize_branch_name(branch)
    if not branch:
        raise RuntimeError("Branch is required")

    configure_worktree_identity(repo_path, user_id=user_id)
    _fetch_remote_heads(repo_path, timeout=60, user_id=user_id)
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


def commit_all(repo_path: Path, message: str, user_id: Optional[str] = None) -> GitActionResult:
    """Stage all changes in a repo and create a commit."""
    if not (repo_path / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_path}")
    message = message.strip()
    if not message:
        raise RuntimeError("Commit message is required")

    configure_worktree_identity(repo_path, user_id=user_id)
    branch = _get_current_branch(repo_path)
    rc, stdout, stderr = _run(["git", "status", "--porcelain"], repo_path, timeout=30)
    if rc != 0:
        raise RuntimeError(f"Git status failed: {_sanitize_git_output(stderr or stdout)}")
    if not stdout:
        return GitActionResult(status="clean", branch=branch)

    rc, stdout, stderr = _run(["git", "add", "-A"], repo_path, timeout=120)
    if rc != 0:
        raise RuntimeError(f"Git add failed: {_sanitize_git_output(stderr or stdout)}")
    rc, stdout, stderr = _run(["git", "commit", "-m", message], repo_path, timeout=120)
    if rc != 0:
        raise RuntimeError(f"Git commit failed: {_sanitize_git_output(stderr or stdout)}")
    return GitActionResult(status="committed", branch=branch, stdout=_sanitize_git_output(stdout))


def commit_message_context(repo_path: Path, max_chars: int = 12000) -> str:
    """Return a compact git change summary suitable for AI commit-message generation."""
    if not (repo_path / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_path}")

    parts: list[str] = []
    for label, cmd in [
        ("status", ["git", "status", "--short"]),
        ("stat", ["git", "diff", "--stat", "HEAD"]),
        ("staged_diff", ["git", "diff", "--cached"]),
        ("unstaged_diff", ["git", "diff"]),
    ]:
        rc, stdout, stderr = _run(cmd, repo_path, timeout=60)
        if rc != 0:
            raise RuntimeError(f"Git {label} failed: {_sanitize_git_output(stderr or stdout)}")
        if stdout:
            parts.append(f"## {label}\n{_sanitize_git_output(stdout)}")

    context = "\n\n".join(parts).strip()
    if not context:
        return ""
    if len(context) > max_chars:
        context = context[:max_chars].rstrip() + "\n\n[diff truncated]"
    return context


def push(repo_path: Path, branch: Optional[str] = None, user_id: Optional[str] = None) -> GitActionResult:
    """Push the current branch to origin using the current user's git credentials."""
    if not (repo_path / ".git").exists():
        raise RuntimeError(f"Not a git repository: {repo_path}")

    configure_worktree_identity(repo_path, user_id=user_id)
    branch = normalize_branch_name(branch) or _get_current_branch(repo_path)
    if not branch or branch == "HEAD":
        raise RuntimeError("Cannot push from detached HEAD")
    remote_url = _get_remote_url(repo_path)
    provider = detect_provider(remote_url)
    auth_url = _build_auth_url(remote_url, provider, user_id=user_id)
    rc, stdout, stderr = _run(["git", "push", auth_url, f"HEAD:refs/heads/{branch}"], repo_path, timeout=120)
    if rc != 0:
        raise RuntimeError(f"Git push failed: {_sanitize_git_output(stderr or stdout)}")
    return GitActionResult(
        status="pushed",
        branch=branch,
        stdout=_sanitize_git_output(stdout),
        stderr=_sanitize_git_output(stderr),
    )


def status(repo_path: Path, user_id: Optional[str] = None) -> GitStatus:
    """Get the working tree status of a repo."""
    if not (repo_path / ".git").exists():
        return GitStatus()

    branch = _get_current_branch(repo_path)

    # Fetch to get ahead/behind
    _fetch_remote_heads(repo_path, timeout=30, user_id=user_id)

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


def branches(repo_path: Path, user_id: Optional[str] = None) -> list[str]:
    """List branches in a repo."""
    if not (repo_path / ".git").exists():
        return []
    _fetch_remote_heads(repo_path, timeout=60, user_id=user_id)
    rc, stdout, _ = _run(["git", "branch", "-a"], repo_path)
    if rc != 0:
        return []
    lines = []
    for line in stdout.split("\n"):
        raw = line.strip()
        if not raw or "HEAD" in raw:
            continue
        normalized = normalize_branch_name(raw)
        if normalized:
            lines.append(normalized)
    return sorted(set(lines))


def _get_remote_url(repo_path: Path) -> str:
    rc, stdout, _ = _run(["git", "remote", "get-url", "origin"], repo_path)
    # Strip embedded tokens from URL for safe display
    url = stdout if rc == 0 else ""
    return _strip_auth_from_url(url)


def _get_current_branch(repo_path: Path) -> str:
    rc, stdout, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    return stdout if rc == 0 else settings.git_default_branch
