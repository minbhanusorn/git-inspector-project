"""Unit tests for git_inspector.git_ops parsing functions.

These tests use hand-built strings that mimic real `git` output, so they
run instantly and don't need an actual repository on disk. See
test_integration.py for tests against a real temporary repo.
"""
from git_inspector import git_ops


def test_parse_log_returns_all_requested_commits():
    raw = "\n".join(
        f"hash{i}|Author {i}|author{i}@example.com|2024-01-0{i}|Commit {i}"
        for i in range(1, 8)
    )
    commits = git_ops.parse_log(raw, limit=7)
    assert len(commits) == 7


def test_parse_log_respects_a_small_limit():
    raw = "\n".join(
        f"hash{i}|Author {i}|author{i}@example.com|2024-01-0{i}|Commit {i}"
        for i in range(1, 4)
    )
    commits = git_ops.parse_log(raw, limit=3)
    assert len(commits) == 3
    assert commits[0].commit_hash == "hash1"
    assert commits[0].message == "Commit 1"


def test_parse_log_handles_pipe_in_commit_message():
    raw = "abc123|Ada|ada@example.com|2024-01-01|Fix a|b edge case"
    commits = git_ops.parse_log(raw, limit=1)
    assert len(commits) == 1
    assert commits[0].message == "Fix a|b edge case"


def test_parse_branches_flags_current_branch():
    raw = "  feature-x\n* main\n  bugfix\n"
    branches = git_ops.parse_branches(raw)

    current = [b for b in branches if b.is_current]
    assert len(current) == 1
    assert current[0].name == "main"

    names = {b.name for b in branches}
    assert names == {"feature-x", "main", "bugfix"}


def test_parse_status_distinguishes_staged_and_unstaged():
    raw = "M  staged_file.py\n M unstaged_file.py\n?? untracked.py\n"
    entries = git_ops.parse_status(raw)
    by_path = {e.path: e for e in entries}

    assert by_path["staged_file.py"].staged is True
    assert by_path["staged_file.py"].unstaged is False

    assert by_path["unstaged_file.py"].staged is False
    assert by_path["unstaged_file.py"].unstaged is True

    assert by_path["untracked.py"].staged is False
    assert by_path["untracked.py"].unstaged is False


def test_parse_status_handles_staged_and_unstaged_together():
    # "MM" means staged AND further modified in the working tree
    raw = "MM both.py\n"
    entries = git_ops.parse_status(raw)
    assert entries[0].staged is True
    assert entries[0].unstaged is True


def test_parse_contributors_orders_by_commit_count_desc():
    raw = "\n".join(
        [
            "Alice|alice@example.com",
            "Bob|bob@example.com",
            "Alice|alice@example.com",
            "Alice|alice@example.com",
            "Bob|bob@example.com",
        ]
    )
    contributors = git_ops.parse_contributors(raw)
    assert [c.name for c in contributors] == ["Alice", "Bob"]
    assert contributors[0].commit_count == 3
    assert contributors[1].commit_count == 2


def test_parse_tags_extracts_message_without_padding():
    # `git tag -n` pads the tag name out to a 16-character column before
    # printing the message. A name that already fills (or overflows) that
    # column is followed by a single space instead.
    raw = (
        "v1.0            Initial stable release\n"
        "v0.1-lightweight Add file_3\n"
    )
    tags = git_ops.parse_tags(raw)
    by_name = {t.name: t for t in tags}
    assert by_name["v1.0"].message == "Initial stable release"
    assert by_name["v0.1-lightweight"].message == "Add file_3"


def test_parse_remotes_extracts_clean_kind():
    raw = (
        "origin\thttps://example.com/repo.git (fetch)\n"
        "origin\thttps://example.com/repo.git (push)\n"
    )
    remotes = git_ops.parse_remotes(raw)
    kinds = {r.kind for r in remotes}
    assert kinds == {"fetch", "push"}


def test_parse_filetypes_handles_multi_dot_filenames():
    paths = ["src/main.py", "archive.tar.gz", "README", "notes.txt"]
    counts = git_ops.parse_filetypes(paths)
    by_ext = {c.extension: c.count for c in counts}
    assert by_ext["py"] == 1
    assert by_ext["gz"] == 1
    assert by_ext["(none)"] == 1
    assert by_ext["txt"] == 1


def test_parse_diffstat_sums_insertions_and_deletions():
    raw = (
        "1 file changed, 10 insertions(+), 2 deletions(-)\n"
        "\n"
        "2 files changed, 3 insertions(+), 7 deletions(-)\n"
    )
    stat = git_ops.parse_diffstat(raw)
    assert stat.files_changed == 3
    assert stat.insertions == 13
    assert stat.deletions == 9


def test_filter_commits_by_message_is_case_insensitive():
    commits = [
        git_ops.Commit("h1", "A", "a@x.com", "2024-01-01", "Fix Bug in parser"),
        git_ops.Commit("h2", "B", "b@x.com", "2024-01-02", "Add new feature"),
    ]
    matches = git_ops.filter_commits_by_message(commits, "bug")
    assert len(matches) == 1
    assert matches[0].commit_hash == "h1"
