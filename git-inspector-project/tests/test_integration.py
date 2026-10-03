"""Integration tests that run git_ops against a real temporary repository
(see the `git_repo` fixture in conftest.py).
"""
from git_inspector import git_ops


def test_get_log_against_real_repo(git_repo):
    commits = git_ops.get_log(cwd=str(git_repo), limit=3)
    assert len(commits) == 3
    messages = [c.message for c in commits]
    assert messages == ["Add file_3", "Add file_2", "Add file_1"]


def test_get_branches_against_real_repo(git_repo):
    branches = git_ops.get_branches(cwd=str(git_repo))
    names = {b.name for b in branches}
    assert names == {"main", "feature-x"}

    current = [b for b in branches if b.is_current]
    assert len(current) == 1
    assert current[0].name == "main"


def test_get_status_against_real_repo(git_repo):
    entries = git_ops.get_status(cwd=str(git_repo))
    by_path = {e.path: e for e in entries}

    assert by_path["staged_new.txt"].staged is True
    assert by_path["staged_new.txt"].unstaged is False

    assert by_path["file_1.txt"].staged is False
    assert by_path["file_1.txt"].unstaged is True


def test_get_log_author_filter_does_not_leak_between_calls(git_repo):
    first = git_ops.get_log(cwd=str(git_repo), limit=10, author="Test Student")
    assert len(first) > 0

    second = git_ops.get_log(cwd=str(git_repo), limit=10, author="Nonexistent Author XYZ")
    assert second == []


def test_get_contributors_against_real_repo(git_repo):
    contributors = git_ops.get_contributors(cwd=str(git_repo))
    assert len(contributors) == 1
    assert contributors[0].name == "Test Student"
    assert contributors[0].commit_count == 3


def test_get_contributors_top_respects_requested_count(git_repo):
    contributors = git_ops.get_contributors(cwd=str(git_repo), top=1)
    assert len(contributors) == 1


def test_get_tags_against_real_repo(git_repo):
    tags = git_ops.get_tags(cwd=str(git_repo))
    by_name = {t.name: t for t in tags}

    # An annotated tag reports its own annotation message.
    assert by_name["v1.0"].message == "First release"

    # A lightweight tag has no annotation of its own, so `git tag -n`
    # falls back to the subject line of the commit it points at -- here,
    # the last commit made by the fixture.
    assert by_name["v0.1-lightweight"].message == "Add file_3"


def test_get_remotes_against_real_repo(git_repo):
    remotes = git_ops.get_remotes(cwd=str(git_repo))
    names = {r.name for r in remotes}
    assert names == {"origin"}
    kinds = {r.kind for r in remotes}
    assert kinds == {"fetch", "push"}


def test_get_filetypes_against_real_repo(git_repo):
    counts = git_ops.get_filetypes(cwd=str(git_repo))
    by_ext = {c.extension: c.count for c in counts}
    assert by_ext["txt"] == 4


def test_get_diffstat_against_real_repo(git_repo):
    stat = git_ops.get_diffstat(cwd=str(git_repo), limit=3)
    assert stat.files_changed == 3
    assert stat.insertions == 3
    assert stat.deletions == 0


def test_search_commits_against_real_repo(git_repo):
    matches = git_ops.search_commits(cwd=str(git_repo), query="add file_2")
    messages = [c.message for c in matches]
    assert messages == ["Add file_2"]
