"""Build a small, reproducible demo repository for trying out git-inspector.

The automated tests build their own throwaway repository (see the
`git_repo` fixture in tests/conftest.py). That fixture is deliberately
minimal -- it has a single author, one file extension and no deletions,
which is all its assertions need.

This script builds a richer version of the same idea, with several
authors, a spread of dates, a variety of file extensions and commits
that both add and remove lines, so that *every* git-inspector command
has something interesting to report.

Every commit uses a fixed author/committer name, email and timestamp,
so the repository -- including its commit hashes -- comes out identical
on every machine. That means the sample output in the assignment
specification should match what you see exactly.

Usage:
    python scripts/make_demo_repo.py [destination]

Defaults to creating ./demo-repo. Re-running deletes and rebuilds it.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REMOTE_URL = "https://example.com/demo/demo-project.git"


def run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, env=env)


def commit(repo: Path, name: str, email: str, date: str, message: str) -> None:
    """Commit staged changes with a fully pinned identity and timestamp."""
    import os

    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME=name,
        GIT_AUTHOR_EMAIL=email,
        GIT_AUTHOR_DATE=date,
        GIT_COMMITTER_NAME=name,
        GIT_COMMITTER_EMAIL=email,
        GIT_COMMITTER_DATE=date,
    )
    run(["git", "commit", "-m", message], cwd=repo, env=env)


def write(repo: Path, relative_path: str, text: str) -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def build(repo: Path) -> None:
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)

    run(["git", "init", "-b", "main"], cwd=repo)
    run(["git", "config", "user.name", "Demo User"], cwd=repo)
    run(["git", "config", "user.email", "demo@example.com"], cwd=repo)

    # 1 -- Ada: project skeleton
    write(repo, "README.md", "# demo-project\n\nA tiny project.\n")
    write(repo, "LICENSE", "MIT License\n")
    run(["git", "add", "README.md", "LICENSE"], cwd=repo)
    commit(
        repo, "Ada Lovelace", "ada@example.com",
        "2024-01-05T09:00:00+00:00", "Add project skeleton",
    )

    # 2 -- Ada: parser module
    write(
        repo, "src/parser.py",
        "def parse(text):\n"
        '    """Parse text into records."""\n'
        "    records = []\n"
        "    for line in text.splitlines():\n"
        "        if line.strip():\n"
        "            records.append(line.strip())\n"
        "    return records\n",
    )
    run(["git", "add", "src/parser.py"], cwd=repo)
    commit(
        repo, "Ada Lovelace", "ada@example.com",
        "2024-01-12T10:30:00+00:00", "Add parser module",
    )

    # 3 -- Grace: notes and data
    write(repo, "notes.txt", "rough notes\nto be tidied up later\n")
    write(repo, "data.json", '{\n  "version": 1\n}\n')
    run(["git", "add", "notes.txt", "data.json"], cwd=repo)
    commit(
        repo, "Grace Hopper", "grace@example.com",
        "2024-01-20T14:15:00+00:00", "Add notes and data",
    )
    run(["git", "tag", "v0.9-beta"], cwd=repo)

    # 4 -- Ada: a fix that removes more than it adds
    write(
        repo, "src/parser.py",
        "def parse(text):\n"
        '    """Parse text into records."""\n'
        "    return [line.strip() for line in text.splitlines() if line.strip()]\n",
    )
    run(["git", "add", "src/parser.py"], cwd=repo)
    commit(
        repo, "Ada Lovelace", "ada@example.com",
        "2024-02-03T11:05:00+00:00", "Fix Bug in parser",
    )

    # 5 -- Alan: archive plus tests
    write(repo, "backup.tar.gz", "placeholder archive contents\n")
    write(
        repo, "tests/test_parser.py",
        "from src.parser import parse\n"
        "\n"
        "def test_parse_skips_blank_lines():\n"
        '    assert parse("a\\n\\nb\\n") == ["a", "b"]\n',
    )
    run(["git", "add", "backup.tar.gz", "tests/test_parser.py"], cwd=repo)
    commit(
        repo, "Alan Turing", "alan@example.com",
        "2024-02-11T16:40:00+00:00", "Add archive and tests",
    )

    # 6 -- Grace: expand the README
    write(
        repo, "README.md",
        "# demo-project\n"
        "\n"
        "A tiny project used to demonstrate git-inspector.\n"
        "\n"
        "## Usage\n"
        "\n"
        "    python -m src.parser\n",
    )
    run(["git", "add", "README.md"], cwd=repo)
    commit(
        repo, "Grace Hopper", "grace@example.com",
        "2024-02-18T08:20:00+00:00", "Update README with usage",
    )

    # 7 -- Ada: delete a file outright
    run(["git", "rm", "-q", "notes.txt"], cwd=repo)
    commit(
        repo, "Ada Lovelace", "ada@example.com",
        "2024-02-25T13:50:00+00:00", "Remove obsolete notes",
    )

    # Annotated tag on the tip, with a pinned timestamp for reproducibility
    import os

    tag_env = dict(os.environ)
    tag_env.update(
        GIT_COMMITTER_NAME="Ada Lovelace",
        GIT_COMMITTER_EMAIL="ada@example.com",
        GIT_COMMITTER_DATE="2024-02-25T14:00:00+00:00",
    )
    run(["git", "tag", "-a", "v1.0", "-m", "First stable release"], cwd=repo, env=tag_env)

    # A second branch, then back to main
    run(["git", "checkout", "-q", "-b", "feature-x"], cwd=repo)
    run(["git", "checkout", "-q", "main"], cwd=repo)

    run(["git", "remote", "add", "origin", REMOTE_URL], cwd=repo)

    # Working-tree state: one staged addition, one unstaged edit, one untracked
    write(repo, "staged_new.txt", "staged content\n")
    run(["git", "add", "staged_new.txt"], cwd=repo)
    write(repo, "README.md", "# demo-project\n\nEdited but not staged.\n")
    write(repo, "scratch.tmp", "scratch\n")


def main() -> int:
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "demo-repo").resolve()
    build(destination)
    print(f"Demo repository created at: {destination}")
    print("Try:  python -m git_inspector.cli log --path", destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
