# git-inspector

A command-line tool that inspects a local git repository and prints
readable summaries of its commit history, branches, and working tree
status.

## Usage

```
python -m git_inspector.cli log [--limit N] [--path PATH] [--author NAME] [--since DATE]
python -m git_inspector.cli branches [--path PATH]
python -m git_inspector.cli status [--path PATH]
python -m git_inspector.cli contributors [--path PATH] [--top N]
python -m git_inspector.cli tags [--path PATH]
python -m git_inspector.cli remotes [--path PATH]
python -m git_inspector.cli filetypes [--path PATH]
python -m git_inspector.cli diffstat [--path PATH] [--limit N]
python -m git_inspector.cli search --query TEXT [--path PATH]
```

## Expected Behaviour

This describes what each command is *supposed* to do. If what you
observe differs from this, that's a bug in the implementation, not in
this description.

- **`log`** — prints the most recent commits, newest first, as a table
  of hash / author / date / message. `--limit N` controls how many are
  shown (default 10). `--author NAME` restricts to commits whose author
  matches `NAME` as a substring; `--since DATE` restricts to commits on
  or after `DATE`. Each invocation is independent — filters from one
  call must never affect a later call.
- **`branches`** — lists every local branch; exactly one row is marked
  as the current (checked-out) branch.
- **`status`** — shows the working tree status as a table of path /
  staged / unstaged. A path can be staged-only, unstaged-only, both, or
  neither (untracked files show neither). If the tree is clean, prints
  a "clean" message instead of an empty table.
- **`contributors`** — lists every commit author, ranked by number of
  commits, **most active first**. `--top N` limits the output to
  exactly the top `N` contributors (default 10) — asking for `--top 5`
  must return 5 rows, not 4.
- **`tags`** — lists every tag with its message, as reported by
  `git tag -n`. The message is the exact text git prints after the
  padded tag-name column, with no leading or trailing padding left on
  it. An annotated tag shows its own annotation message; a lightweight
  tag has no annotation, so git shows the subject of the commit it
  points at.
- **`remotes`** — lists every configured remote with its URL and type.
  The type column is exactly `fetch` or `push` — no surrounding
  punctuation.
- **`filetypes`** — counts tracked files by extension. A file's
  extension is whatever follows its *last* dot (e.g. `archive.tar.gz`
  → `gz`, not `tar.gz`); files with no dot are grouped under `(none)`.
- **`diffstat`** — sums the files-changed / insertions / deletions
  reported by `git` over the last `--limit` commits. Insertions and
  deletions are reported under their own names — an insertions count
  must never appear as deletions or vice versa.
- **`search`** — returns commits whose message contains the given
  `--query` text, matching **case-insensitively** (a query of `"bug"`
  must match a message containing `"Bug"`).

## Installation

Requires Python 3.13 (see `requires-python` in `pyproject.toml`; this
also matches the base image used by the Dockerfile).

```
pip install -r requirements.txt
```

## Running tests

```
pytest
```


