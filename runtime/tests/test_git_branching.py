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
