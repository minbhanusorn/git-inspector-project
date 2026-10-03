import subprocess
from pathlib import Path

import pytest


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a small, throwaway git repository for integration tests.

    Layout produced:
      - repo initialised with a "main" branch
      - 3 commits on main
      - an annotated tag "v1.0" and a lightweight tag "v0.1-lightweight"
      - a fake "origin" remote (never fetched from, just configured)
      - a second branch "feature-x" checked out at the end
      - one staged file and one unstaged modification, so status has
        something interesting to report
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    _run(["git", "init", "-b", "main"], cwd=repo)
    _run(["git", "config", "user.email", "student@example.com"], cwd=repo)
    _run(["git", "config", "user.name", "Test Student"], cwd=repo)

    for i in range(1, 4):
        (repo / f"file_{i}.txt").write_text(f"content {i}\n")
        _run(["git", "add", f"file_{i}.txt"], cwd=repo)
        _run(["git", "commit", "-m", f"Add file_{i}"], cwd=repo)

    _run(["git", "tag", "-a", "v1.0", "-m", "First release"], cwd=repo)
    _run(["git", "tag", "v0.1-lightweight"], cwd=repo)
    _run(
        ["git", "remote", "add", "origin", "https://example.com/example/repo.git"],
        cwd=repo,
    )

    _run(["git", "checkout", "-b", "feature-x"], cwd=repo)
    _run(["git", "checkout", "main"], cwd=repo)

    # one staged addition
    (repo / "staged_new.txt").write_text("staged\n")
    _run(["git", "add", "staged_new.txt"], cwd=repo)

    # one unstaged modification to an existing tracked file
    (repo / "file_1.txt").write_text("modified content\n")

    return repo
