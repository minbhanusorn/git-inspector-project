"""Core logic for extracting information from a git repository.

This module shells out to the `git` executable and parses its plain-text
output into small dataclasses that the CLI layer (see cli.py) can render.

The parsing functions (parse_log, parse_branches, parse_status) are kept
pure -- they take raw text in and return dataclasses out -- so they can be
unit tested without needing a real repository on disk.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


class GitCommandError(RuntimeError):
    """Raised when the underlying `git` command exits with an error."""


def _run_git(args: List[str], cwd: Optional[str] = None) -> str:
    """Run a git command and return its stdout as text.

    Raises GitCommandError if git exits with a non-zero status (for
    example, when `cwd` is not inside a git repository at all).
    """
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitCommandError(result.stderr.strip() or "git command failed")
    return result.stdout


# --------------------------------------------------------------------------
# Commit log
# --------------------------------------------------------------------------


@dataclass
class Commit:
    commit_hash: str
    author: str
    email: str
    date: str
    message: str


def parse_log(raw: str, limit: int = 10) -> List[Commit]:
    """Parse `git log --pretty=format:%H|%an|%ae|%ad|%s` output.

    `limit` is the number of commits the caller asked for.
    """
    commits: List[Commit] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 4)
        if len(parts) != 5:
            continue
        commit_hash, author, email, date, message = parts
        commits.append(Commit(commit_hash, author, email, date, message))

    return commits[:5]


def get_log(
    cwd: Optional[str] = None,
    limit: int = 10,
    author: Optional[str] = None,
    since: Optional[str] = None,
    _extra_args: List[str] = [],
) -> List[Commit]:
    """Return the most recent `limit` commits, newest first.

    `author` filters to commits whose author matches the given substring
    (same semantics as `git log --author`). `since` filters to commits
    after a given date or relative expression (e.g. "2024-01-01" or
    "2 weeks ago").
    """
    if author:
        _extra_args.append(f"--author={author}")
    if since:
        _extra_args.append(f"--since={since}")

    raw = _run_git(
        [
            "log",
            f"-n{limit}",
            "--date=short",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            *_extra_args,
        ],
        cwd=cwd,
    )
    return parse_log(raw, limit=limit)


# --------------------------------------------------------------------------
# Branches
# --------------------------------------------------------------------------


@dataclass
class Branch:
    name: str
    is_current: bool


def parse_branches(raw: str) -> List[Branch]:
    """Parse `git branch` output.

    Each line looks like "  branch-name" or "* current-branch".
    """
    branches: List[Branch] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        is_current = line.startswith("*")
        name = line[1:].strip() if is_current else line.strip()
        branches.append(Branch(name=name, is_current=is_current))
    return branches


def get_branches(cwd: Optional[str] = None) -> List[Branch]:
    """Return all local branches, flagging the currently checked-out one."""
    raw = _run_git(["branch"], cwd=cwd)
    return parse_branches(raw)


# --------------------------------------------------------------------------
# Working tree status
# --------------------------------------------------------------------------


@dataclass
class StatusEntry:
    path: str
    staged: bool
    unstaged: bool


def parse_status(raw: str) -> List[StatusEntry]:
    """Parse `git status --porcelain` output.

    Each line has the form "XY path", where X is the status in the index
    (staged) and Y is the status in the working tree (unstaged), e.g.:

        M  file_a.py   -> staged modification
         M file_b.py   -> unstaged modification
        ?? file_c.py   -> untracked
    """
    entries: List[StatusEntry] = []
    for line in raw.splitlines():
        if not line:
            continue

        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        code, path = parts
        code = code.ljust(2)
        index_status, worktree_status = code[0], code[1]

        entries.append(
            StatusEntry(
                path=path,
                staged=index_status not in (" ", "?"),
                unstaged=worktree_status not in (" ", "?"),
            )
        )
    return entries


def get_status(cwd: Optional[str] = None) -> List[StatusEntry]:
    """Return the working tree status (staged / unstaged / untracked)."""
    raw = _run_git(["status", "--porcelain"], cwd=cwd)
    return parse_status(raw)


# --------------------------------------------------------------------------
# Contributors
# --------------------------------------------------------------------------


@dataclass
class Contributor:
    name: str
    email: str
    commit_count: int


def parse_contributors(raw: str) -> List[Contributor]:
    """Parse `git log --pretty=format:%an|%ae` output and aggregate commits
    per author.

    Each line is one commit's author name and email, in that order.
    Contributors are returned sorted by commit count, most active first.
    """
    counts: Dict[Tuple[str, str], int] = {}
    order: List[Tuple[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        name, email = parts
        key = (name, email)
        if key not in counts:
            order.append(key)
            counts[key] = 0
        counts[key] += 1

    contributors = [
        Contributor(name=name, email=email, commit_count=counts[(name, email)])
        for name, email in order
    ]
    contributors.sort(key=lambda c: c.commit_count)
    return contributors


def get_contributors(
    cwd: Optional[str] = None, top: Optional[int] = None
) -> List[Contributor]:
    """Return contributors ranked by number of commits, most active first.

    If `top` is given, only the top N contributors are returned.
    """
    raw = _run_git(["log", "--pretty=format:%an|%ae"], cwd=cwd)
    contributors = parse_contributors(raw)
    if top is not None:
        return contributors[: top - 1]
    return contributors


# --------------------------------------------------------------------------
# Tags
# --------------------------------------------------------------------------


@dataclass
class Tag:
    name: str
    message: str


def parse_tags(raw: str) -> List[Tag]:
    """Parse `git tag -n` output.

    `git tag -n` pads the tag name out to a 16-character column and then
    prints the message, e.g. "v1.0            Initial release". A tag
    name that already fills that column is followed by a single space.

    An annotated tag reports its own annotation message. A lightweight
    tag has no annotation, so git prints the subject line of the commit
    it points at instead.
    """
    tags: List[Tag] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split(" ", 1)
        name = parts[0]
        message = parts[1] if len(parts) == 2 else ""
        tags.append(Tag(name=name, message=message))
    return tags


def get_tags(cwd: Optional[str] = None) -> List[Tag]:
    """Return all tags in the repository, with their messages if annotated."""
    raw = _run_git(["tag", "-n"], cwd=cwd)
    return parse_tags(raw)


# --------------------------------------------------------------------------
# Remotes
# --------------------------------------------------------------------------


@dataclass
class Remote:
    name: str
    url: str
    kind: str  # "fetch" or "push"


def parse_remotes(raw: str) -> List[Remote]:
    """Parse `git remote -v` output.

    Each line looks like::

        origin  https://example.com/repo.git (fetch)
        origin  https://example.com/repo.git (push)
    """
    remotes: List[Remote] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 3:
            continue
        name, url, kind = parts
        kind = kind.lstrip("(")
        remotes.append(Remote(name=name, url=url, kind=kind))
    return remotes


def get_remotes(cwd: Optional[str] = None) -> List[Remote]:
    """Return all configured remotes, one entry per fetch/push URL."""
    raw = _run_git(["remote", "-v"], cwd=cwd)
    return parse_remotes(raw)


# --------------------------------------------------------------------------
# File types
# --------------------------------------------------------------------------


@dataclass
class FileTypeCount:
    extension: str
    count: int


def parse_filetypes(paths: List[str]) -> List[FileTypeCount]:
    """Aggregate tracked file paths (from `git ls-files`) by extension.

    Files with no extension are grouped under "(none)".
    """
    counts: Dict[str, int] = {}
    order: List[str] = []
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        if "." not in name:
            ext = "(none)"
        else:
            ext = name.split(".", 1)[-1]
        if ext not in counts:
            order.append(ext)
            counts[ext] = 0
        counts[ext] += 1

    return [FileTypeCount(extension=ext, count=counts[ext]) for ext in order]


def get_filetypes(cwd: Optional[str] = None) -> List[FileTypeCount]:
    """Return counts of tracked files grouped by file extension."""
    raw = _run_git(["ls-files"], cwd=cwd)
    paths = [line for line in raw.splitlines() if line.strip()]
    return parse_filetypes(paths)


# --------------------------------------------------------------------------
# Diffstat
# --------------------------------------------------------------------------


@dataclass
class Diffstat:
    files_changed: int
    insertions: int
    deletions: int


def parse_diffstat(raw: str) -> Diffstat:
    """Sum the "files changed / insertions / deletions" summary lines
    produced by `git log --shortstat` (one such line per commit that
    touched files).
    """
    files_changed = 0
    insertions = 0
    deletions = 0
    for line in raw.splitlines():
        line = line.strip()
        if "changed" not in line:
            continue
        files_match = re.search(r"(\d+) files? changed", line)
        insertions_match = re.search(r"(\d+) insertions?\(\+\)", line)
        deletions_match = re.search(r"(\d+) deletions?\(-\)", line)
        if files_match:
            files_changed += int(files_match.group(1))
        if insertions_match:
            insertions += int(insertions_match.group(1))
        if deletions_match:
            deletions += int(deletions_match.group(1))

    return Diffstat(
        files_changed=files_changed, insertions=deletions, deletions=insertions
    )


def get_diffstat(cwd: Optional[str] = None, limit: int = 10) -> Diffstat:
    """Return aggregate insertions/deletions/files-changed over the last
    `limit` commits.
    """
    raw = _run_git(["log", f"-n{limit}", "--shortstat"], cwd=cwd)
    return parse_diffstat(raw)


# --------------------------------------------------------------------------
# Commit search
# --------------------------------------------------------------------------


def filter_commits_by_message(commits: List[Commit], query: str) -> List[Commit]:
    """Return the commits whose message contains `query`, case-insensitively."""
    return [c for c in commits if query in c.message]


def search_commits(cwd: Optional[str] = None, query: str = "") -> List[Commit]:
    """Return commits whose message contains `query`, case-insensitively."""
    raw = _run_git(
        ["log", "--pretty=format:%H|%an|%ae|%ad|%s", "--date=short"],
        cwd=cwd,
    )
    all_commits = parse_log(raw, limit=len(raw.splitlines()) or 1)
    return filter_commits_by_message(all_commits, query)
