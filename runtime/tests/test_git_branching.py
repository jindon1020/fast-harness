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
    assert any(cmd == ["git", "worktree", "add", str(tmp_path / "ws-1" / "app"), "origin/feature/x"] for cmd, _cwd in commands)


def test_branches_fetches_remote_branches(monkeypatch, tmp_path):
    repo_path = tmp_path / "app"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    commands = []

    def fake_run(cmd, cwd, timeout=120):
        commands.append(cmd)
        if cmd == ["git", "branch", "-a"]:
            return 0, "* main\n  remotes/origin/main\n  remotes/origin/feature/x", ""
        return 0, "", ""

    monkeypatch.setattr(git, "_run", fake_run)

    assert git.branches(repo_path) == ["feature/x", "main"]
    assert ["git", "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--prune"] in commands


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
