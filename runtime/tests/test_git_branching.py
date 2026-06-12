from types import SimpleNamespace

import pytest

from src.core import git


def test_clone_fetches_all_branches(monkeypatch, tmp_path):
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append(cmd)
        if cmd[:3] == ["git", "ls-remote", "--symref"]:
            return 0, "ref: refs/heads/main\tHEAD", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    repo = git.clone("https://example.com/app.git", tmp_path)

    assert repo.branch == "main"
    assert ["git", "clone", "--branch", "main", "https://example.com/app.git", "app"] in commands


def test_remote_branches_uses_ls_remote_heads(monkeypatch):
    def fake_run(cmd, cwd, timeout=120):
        assert cmd == ["git", "ls-remote", "--heads", "https://example.com/app.git"]
        return 0, (
            "abc\trefs/heads/master\n"
            "def\trefs/heads/feature/x\n"
            "ghi\trefs/heads/release/v1"
        ), ""

    monkeypatch.setattr(git, "_run", fake_run)

    assert git.remote_branches("https://example.com/app.git") == [
        "feature/x",
        "master",
        "release/v1",
    ]


def test_remote_branches_uses_current_user_codeup_token(monkeypatch):
    def fake_get_user(user_id):
        assert user_id == "alice"
        return {
            "id": "alice",
            "name": "Alice",
            "git": {
                "codeup_user": "alice-codeup",
                "codeup_token": "user token",
            },
        }

    def fake_run(cmd, cwd, timeout=120):
        assert cmd == [
            "git",
            "ls-remote",
            "--heads",
            "https://alice-codeup:user%20token@codeup.aliyun.com/group/app.git",
        ]
        return 0, "abc\trefs/heads/main", ""

    monkeypatch.setattr(git, "settings", SimpleNamespace(
        get_user=fake_get_user,
        git_github_token="",
        git_codeup_user="",
        git_codeup_token="",
        git_ssh_key_path="",
        git_default_branch="main",
    ))
    monkeypatch.setattr(git, "_run", fake_run)

    assert git.remote_branches("https://codeup.aliyun.com/group/app.git", user_id="alice") == ["main"]


def test_create_worktree_uses_source_repo_and_branch(monkeypatch, tmp_path):
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        if cmd[:3] == ["git", "ls-remote", "--symref"]:
            return 0, "ref: refs/heads/master\tHEAD", ""
        if cmd == ["git", "remote", "get-url", "origin"]:
            return 0, "https://example.com/app.git", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    repo = git.create_worktree(
        url="https://example.com/app.git",
        source_dir=tmp_path / ".sources",
        worktree_path=tmp_path / "ws-1" / "app",
        branch="feature/x",
    )

    assert repo.name == "app"
    assert repo.branch == "feature/x"
    assert any(cmd[:2] == ["git", "clone"] for cmd, _cwd in commands)
    assert any(cmd == ["git", "remote", "set-url", "origin", "https://example.com/app.git"] for cmd, _cwd in commands)
    assert any(cmd == ["git", "fetch", "--prune", "https://example.com/app.git", "+refs/heads/*:refs/remotes/origin/*"] for cmd, _cwd in commands)
    assert any(cmd == ["git", "worktree", "add", str(tmp_path / "ws-1" / "app"), "origin/feature/x"] for cmd, _cwd in commands)


def test_create_worktree_normalizes_git_branch_marker(monkeypatch, tmp_path):
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    repo = git.create_worktree(
        url="https://example.com/app.git",
        source_dir=tmp_path / ".sources",
        worktree_path=tmp_path / "ws-1" / "app",
        branch="+ feature/sp11_01",
    )

    assert repo.branch == "feature/sp11_01"
    assert any(
        cmd == ["git", "worktree", "add", str(tmp_path / "ws-1" / "app"), "origin/feature/sp11_01"]
        for cmd, _cwd in commands
    )


def test_create_worktree_fetches_existing_source_with_fresh_codeup_token(monkeypatch, tmp_path):
    source_repo = tmp_path / ".sources" / "app"
    (source_repo / ".git").mkdir(parents=True)
    commands = []

    monkeypatch.setattr(git.settings, "git_codeup_user", "alice")
    monkeypatch.setattr(git.settings, "git_codeup_token", "new token")

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    repo_url = "https://codeup.aliyun.com/group/app.git"
    git.create_worktree(
        url=repo_url,
        source_dir=tmp_path / ".sources",
        worktree_path=tmp_path / "ws-1" / "app",
        branch="feature/x",
    )

    assert (["git", "remote", "set-url", "origin", repo_url], source_repo) in commands
    assert (
        [
            "git",
            "fetch",
            "--prune",
            "https://alice:new%20token@codeup.aliyun.com/group/app.git",
            "+refs/heads/*:refs/remotes/origin/*",
        ],
        source_repo,
    ) in commands


def test_configure_worktree_identity_uses_user_git_config(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    (repo_path / ".git").mkdir(parents=True)
    commands = []

    def fake_get_user(user_id):
        assert user_id == "alice"
        return {
            "id": "alice",
            "name": "Alice",
            "git": {
                "name": "Alice Z",
                "email": "alice@example.com",
                "codeup_user": "alice-codeup",
                "codeup_token": "secret",
            },
        }

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        return 0, "", ""

    monkeypatch.setattr(git, "settings", SimpleNamespace(
        get_user=fake_get_user,
        git_github_token="",
        git_codeup_user="",
        git_codeup_token="",
        git_ssh_key_path="",
        git_default_branch="main",
    ))
    monkeypatch.setattr(git, "_run", fake_run)

    git.configure_worktree_identity(repo_path, user_id="alice")

    assert (["git", "config", "extensions.worktreeConfig", "true"], repo_path) in commands
    assert (["git", "config", "--worktree", "user.name", "Alice Z"], repo_path) in commands
    assert (["git", "config", "--worktree", "user.email", "alice@example.com"], repo_path) in commands
    helper_commands = [
        cmd for cmd, cwd in commands
        if cwd == repo_path and cmd[:4] == ["git", "config", "--worktree", "credential.helper"]
    ]
    assert len(helper_commands) == 1
    assert "host=codeup.aliyun.com" in helper_commands[0][4]
    assert "username='alice-codeup'" in helper_commands[0][4]
    assert "password='secret'" in helper_commands[0][4]


def test_configure_worktree_identity_falls_back_to_global_codeup_token(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    (repo_path / ".git").mkdir(parents=True)
    commands = []

    def fake_get_user(user_id):
        assert user_id == "alice"
        return {
            "id": "alice",
            "name": "Alice",
            "git": {
                "name": "Alice Z",
                "codeup_user": "alice-codeup",
                "codeup_token_env": "MISSING_ALICE_CODEUP_TOKEN",
                "codeup_token": "",
            },
        }

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        return 0, "", ""

    monkeypatch.setattr(git, "settings", SimpleNamespace(
        get_user=fake_get_user,
        git_github_token="",
        git_codeup_user="fallback-user",
        git_codeup_token="global secret",
        git_ssh_key_path="",
        git_default_branch="main",
    ))
    monkeypatch.setattr(git, "_run", fake_run)

    git.configure_worktree_identity(repo_path, user_id="alice")

    helper_commands = [
        cmd for cmd, cwd in commands
        if cwd == repo_path and cmd[:4] == ["git", "config", "--worktree", "credential.helper"]
    ]
    assert len(helper_commands) == 1
    assert "username='alice-codeup'" in helper_commands[0][4]
    assert "password='global secret'" in helper_commands[0][4]


def test_configure_worktree_identity_uses_fallback_email(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    (repo_path / ".git").mkdir(parents=True)
    commands = []

    monkeypatch.setattr(git, "settings", SimpleNamespace(
        get_user=lambda user_id: {"id": user_id, "name": "Alice", "git": {"name": "Alice"}},
        git_github_token="",
        git_codeup_user="",
        git_codeup_token="",
        git_ssh_key_path="",
        git_default_branch="main",
    ))
    monkeypatch.setattr(git, "_run", lambda cmd, cwd, timeout=120: (commands.append((cmd, cwd)) or (0, "", "")))

    git.configure_worktree_identity(repo_path, user_id="alice@example")

    assert (
        ["git", "config", "--worktree", "user.email", "alice-example@fast-harness.local"],
        repo_path,
    ) in commands


def test_commit_all_stages_and_commits_changes(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    (repo_path / ".git").mkdir(parents=True)
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, "feature/x", ""
        if cmd == ["git", "status", "--porcelain"]:
            return 0, " M app.py", ""
        if cmd == ["git", "commit", "-m", "ship changes"]:
            return 0, "[feature/x abc] ship changes", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    result = git.commit_all(repo_path, "ship changes", user_id="alice")

    assert result.status == "committed"
    assert result.branch == "feature/x"
    assert (["git", "add", "-A"], repo_path) in commands
    assert (["git", "commit", "-m", "ship changes"], repo_path) in commands


def test_commit_all_returns_clean_without_commit(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    (repo_path / ".git").mkdir(parents=True)
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append(cmd)
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, "main", ""
        if cmd == ["git", "status", "--porcelain"]:
            return 0, "", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    result = git.commit_all(repo_path, "nothing to do")

    assert result.status == "clean"
    assert ["git", "commit", "-m", "nothing to do"] not in commands


def test_push_uses_origin_with_worktree_credentials(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    (repo_path / ".git").mkdir(parents=True)
    commands = []

    def fake_get_user(user_id):
        return {
            "id": user_id,
            "name": "Alice",
            "git": {
                "codeup_user": "alice-codeup",
                "codeup_token": "secret token",
            },
        }

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        if cmd == ["git", "push", "origin", "HEAD:refs/heads/feature/x"]:
            return 0, "", "pushed"
        return 0, "", ""

    monkeypatch.setattr(git, "settings", SimpleNamespace(
        get_user=fake_get_user,
        git_github_token="",
        git_codeup_user="",
        git_codeup_token="",
        git_ssh_key_path="",
        git_default_branch="main",
    ))
    monkeypatch.setattr(git, "_run", fake_run)

    result = git.push(repo_path, branch="feature/x", user_id="alice")

    assert result.status == "pushed"
    assert result.branch == "feature/x"
    assert (
        ["git", "push", "origin", "HEAD:refs/heads/feature/x"],
        repo_path,
    ) in commands


def test_push_rebases_and_retries_when_remote_is_ahead(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    (repo_path / ".git").mkdir(parents=True)
    commands = []
    push_attempts = 0

    def fake_get_user(user_id):
        return {"id": user_id, "name": "Alice", "git": {}}

    def fake_run(cmd, cwd, timeout=120):
        nonlocal push_attempts
        commands.append((cmd, cwd))
        if cmd == ["git", "push", "origin", "HEAD:refs/heads/feature/x"]:
            push_attempts += 1
            if push_attempts == 1:
                return 1, "", "failed to push some refs\nnon-fast-forward"
            return 0, "pushed", ""
        if cmd == ["git", "fetch", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*"]:
            return 0, "fetched", ""
        if cmd == ["git", "rebase", "--autostash", "origin/feature/x"]:
            return 0, "rebased", ""
        return 0, "", ""

    monkeypatch.setattr(git, "settings", SimpleNamespace(
        get_user=fake_get_user,
        git_github_token="",
        git_codeup_user="",
        git_codeup_token="",
        git_ssh_key_path="",
        git_default_branch="main",
    ))
    monkeypatch.setattr(git, "_run", fake_run)

    result = git.push(repo_path, branch="feature/x", user_id="alice")

    assert result.status == "pushed"
    assert push_attempts == 2
    assert (
        ["git", "rebase", "--autostash", "origin/feature/x"],
        repo_path,
    ) in commands
    assert "Rebased onto remote branch before push." in result.stdout


def test_push_aborts_rebase_when_auto_sync_conflicts(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    (repo_path / ".git").mkdir(parents=True)
    commands = []

    def fake_get_user(user_id):
        return {"id": user_id, "name": "Alice", "git": {}}

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        if cmd == ["git", "push", "origin", "HEAD:refs/heads/feature/x"]:
            return 1, "", "failed to push some refs\nnon-fast-forward"
        if cmd == ["git", "fetch", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*"]:
            return 0, "fetched", ""
        if cmd == ["git", "rebase", "--autostash", "origin/feature/x"]:
            return 1, "", "CONFLICT (content): Merge conflict"
        if cmd == ["git", "rebase", "--abort"]:
            return 0, "", ""
        return 0, "", ""

    monkeypatch.setattr(git, "settings", SimpleNamespace(
        get_user=fake_get_user,
        git_github_token="",
        git_codeup_user="",
        git_codeup_token="",
        git_ssh_key_path="",
        git_default_branch="main",
    ))
    monkeypatch.setattr(git, "_run", fake_run)

    with pytest.raises(RuntimeError, match="automatic rebase conflicted"):
        git.push(repo_path, branch="feature/x", user_id="alice")

    assert (["git", "rebase", "--abort"], repo_path) in commands


def test_create_worktree_installs_fast_harness_suite_after_worktree_add(monkeypatch, tmp_path):
    commands = []
    worktree_path = tmp_path / "ws-1" / "app"

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd, timeout))
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    git.create_worktree(
        url="https://example.com/app.git",
        source_dir=tmp_path / ".sources",
        worktree_path=worktree_path,
        branch="feature/x",
    )

    worktree_add = next(
        i for i, (cmd, _cwd, _timeout) in enumerate(commands)
        if cmd == ["git", "worktree", "add", str(worktree_path), "origin/feature/x"]
    )
    install = next(
        i for i, (cmd, cwd, _timeout) in enumerate(commands)
        if cmd[:2] == ["bash", "-lc"] and cwd == worktree_path
    )
    assert install > worktree_add
    assert "install.sh" in commands[install][0][2]
    assert "--force" in commands[install][0][2]
    assert "--local" in commands[install][0][2]


def test_create_worktree_can_skip_fast_harness_install(monkeypatch, tmp_path):
    commands = []
    worktree_path = tmp_path / "ws-1" / "app"

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd, timeout))
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    git.create_worktree(
        url="https://example.com/app.git",
        source_dir=tmp_path / ".sources",
        worktree_path=worktree_path,
        branch="feature/x",
        install_harness=False,
    )

    assert any(
        cmd == ["git", "worktree", "add", str(worktree_path), "origin/feature/x"]
        for cmd, _cwd, _timeout in commands
    )
    assert not any(cmd[:2] == ["bash", "-lc"] and cwd == worktree_path for cmd, cwd, _timeout in commands)


def test_create_worktree_removes_worktree_when_fast_harness_install_fails(monkeypatch, tmp_path):
    commands = []
    source_repo = tmp_path / ".sources" / "app"
    worktree_path = tmp_path / "ws-1" / "app"

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        if cmd[:2] == ["bash", "-lc"]:
            return 1, "", "install failed"
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    try:
        git.create_worktree(
            url="https://example.com/app.git",
            source_dir=tmp_path / ".sources",
            worktree_path=worktree_path,
            branch="feature/x",
        )
    except RuntimeError as exc:
        assert str(exc) == "fast-harness install failed: install failed"
    else:
        raise AssertionError("Expected RuntimeError")

    assert (["git", "worktree", "remove", "--force", str(worktree_path)], source_repo) in commands


def test_create_worktree_replaces_invalid_source_cache(monkeypatch, tmp_path):
    source_repo = tmp_path / ".sources" / "app"
    source_repo.mkdir(parents=True)
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append((cmd, cwd))
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    repo = git.create_worktree(
        url="https://example.com/app.git",
        source_dir=tmp_path / ".sources",
        worktree_path=tmp_path / "ws-1" / "app",
        branch="feature/x",
    )

    assert repo.branch == "feature/x"
    assert any(cmd == ["git", "clone", "https://example.com/app.git", "app"] for cmd, _cwd in commands)


def test_create_worktree_reports_fetch_failure(monkeypatch, tmp_path):
    source_repo = tmp_path / ".sources" / "app"
    (source_repo / ".git").mkdir(parents=True)

    def fake_run(cmd, cwd, timeout=120):
        if cmd[:2] == ["git", "fetch"]:
            return 128, "", "authentication failed"
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    try:
        git.create_worktree(
            url="https://example.com/app.git",
            source_dir=tmp_path / ".sources",
            worktree_path=tmp_path / "ws-1" / "app",
            branch="feature/x",
        )
    except RuntimeError as exc:
        assert str(exc) == "Source fetch failed: authentication failed"
    else:
        raise AssertionError("Expected RuntimeError")


def test_branches_fetches_remote_branches(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append(cmd)
        if cmd == ["git", "remote", "get-url", "origin"]:
            return 0, "https://example.com/app.git", ""
        if cmd == ["git", "branch", "-a"]:
            return 0, "* main\n  remotes/origin/main\n  remotes/origin/feature/x", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    assert git.branches(repo_path) == ["feature/x", "main"]
    assert ["git", "fetch", "--prune", "https://example.com/app.git", "+refs/heads/*:refs/remotes/origin/*"] in commands


def test_branches_strips_worktree_branch_marker(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    def fake_run(cmd, cwd, timeout=120):
        if cmd == ["git", "remote", "get-url", "origin"]:
            return 0, "https://example.com/app.git", ""
        if cmd == ["git", "branch", "-a"]:
            return 0, (
                "* main\n"
                "+ feature/sp11_01\n"
                "  remotes/origin/HEAD -> origin/main\n"
                "  remotes/origin/feature/sp11_01"
            ), ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    assert git.branches(repo_path) == ["feature/sp11_01", "main"]


def test_checkout_branch_creates_tracking_branch_from_origin(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append(cmd)
        if cmd == ["git", "checkout", "feature/x"]:
            return 1, "", "pathspec did not match"
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, "feature/x", ""
        if cmd == ["git", "remote", "get-url", "origin"]:
            return 0, "https://example.com/app.git", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    repo = git.checkout(repo_path, "feature/x")

    assert repo.branch == "feature/x"
    assert ["git", "checkout", "-B", "feature/x", "origin/feature/x"] in commands


def test_checkout_resets_fast_harness_paths_before_switch_and_reinstalls(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append(cmd)
        if cmd[:2] == ["git", "ls-files"]:
            return 0, ".cursor/commands/implement.md\n.ether/commands/implement-command.md", ""
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, "bugfix/x", ""
        if cmd == ["git", "remote", "get-url", "origin"]:
            return 0, "https://example.com/app.git", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    git.checkout(repo_path, "bugfix/x")

    reset_index = commands.index([
        "git",
        "checkout",
        "--",
        ".cursor/commands/implement.md",
        ".ether/commands/implement-command.md",
    ])
    clean_index = commands.index(["git", "clean", "-fd", "--", *git.FAST_HARNESS_MANAGED_PATHS])
    checkout_index = commands.index(["git", "checkout", "bugfix/x"])
    install_index = next(i for i, cmd in enumerate(commands) if cmd[:2] == ["bash", "-lc"])

    assert reset_index < checkout_index
    assert clean_index < checkout_index
    assert install_index > checkout_index


def test_checkout_branch_falls_back_to_detached_origin_when_branch_is_in_use(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append(cmd)
        if cmd in (
            ["git", "checkout", "master"],
            ["git", "checkout", "-B", "master", "origin/master"],
        ):
            return 1, "", "already checked out"
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, "HEAD", ""
        if cmd == ["git", "remote", "get-url", "origin"]:
            return 0, "https://example.com/app.git", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    repo = git.checkout(repo_path, "master")

    assert repo.branch == "master"
    assert ["git", "checkout", "--detach", "origin/master"] in commands


def test_session_diff_collects_tracked_and_untracked(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()

    def fake_run(cmd, cwd, timeout=120):
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return 0, "feature/x", ""
        if cmd[:3] == ["git", "diff", "--numstat"]:
            return 0, "3\t1\tsrc/app.py", ""
        if cmd[:3] == ["git", "diff", "--name-status"]:
            return 0, "M\tsrc/app.py", ""
        if cmd[:2] == ["git", "diff"] and "--" in cmd and "src/app.py" in cmd:
            return 0, "@@ -1 +1,3 @@\n-old\n+new\n+more\n+lines", ""
        if cmd[:2] == ["git", "ls-files"]:
            return 0, "src/new.py", ""
        if cmd[:3] == ["git", "diff", "--no-index"]:
            return 1, "@@ -0,0 +1,2 @@\n+line a\n+line b", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    result = git.session_diff(tmp_path)

    assert result.branch == "feature/x"
    assert result.clean is False
    by_path = {f.path: f for f in result.files}
    assert set(by_path) == {"src/app.py", "src/new.py"}
    assert by_path["src/app.py"].change_type == "modified"
    assert by_path["src/app.py"].additions == 3
    assert by_path["src/app.py"].deletions == 1
    assert by_path["src/new.py"].change_type == "untracked"
    assert by_path["src/new.py"].additions == 2


def test_session_diff_clean_repo(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()

    def fake_run(cmd, cwd, timeout=120):
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return 0, "main", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    result = git.session_diff(tmp_path)
    assert result.clean is True
    assert result.files == []


def test_session_diff_truncates_large_file(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()
    big = "+" + ("x" * 100)

    def fake_run(cmd, cwd, timeout=120):
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return 0, "main", ""
        if cmd[:3] == ["git", "diff", "--numstat"]:
            return 0, "9\t0\tbig.txt", ""
        if cmd[:3] == ["git", "diff", "--name-status"]:
            return 0, "A\tbig.txt", ""
        if cmd[:2] == ["git", "diff"] and "big.txt" in cmd:
            return 0, "\n".join([big] * 50), ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    result = git.session_diff(tmp_path, max_file_chars=200)
    assert result.files[0].truncated is True
    assert "[diff truncated]" in result.files[0].diff
