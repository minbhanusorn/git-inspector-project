"""Command-line interface for git-inspector.

Run with:  python -m git_inspector.cli <command>
"""
import click
from rich.console import Console
from rich.table import Table

from . import git_ops

console = Console()


@click.group()
def cli():
    """git-inspector: extract readable information from a git repository."""


@cli.command()
@click.option(
    "--limit", "-n", default=10, show_default=True,
    help="Number of commits to show.",
)
@click.option(
    "--path", "-C", "repo_path", default=".",
    help="Path to the git repository.",
)
@click.option(
    "--author", default=None,
    help="Only show commits by this author (substring match).",
)
@click.option(
    "--since", default=None,
    help="Only show commits after this date (e.g. 2024-01-01 or '2 weeks ago').",
)
def log(limit, repo_path, author, since):
    """Show recent commit history."""
    try:
        commits = git_ops.get_log(cwd=repo_path, limit=limit, author=author, since=since)
    except git_ops.GitCommandError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    table = Table(title="Commit Log")
    table.add_column("Hash", style="cyan", no_wrap=True)
    table.add_column("Author")
    table.add_column("Date")
    table.add_column("Message")
    for c in commits:
        table.add_row(c.commit_hash[:8], c.author, c.date, c.message)
    console.print(table)


@cli.command()
@click.option(
    "--path", "-C", "repo_path", default=".",
    help="Path to the git repository.",
)
def branches(repo_path):
    """List local branches."""
    try:
        branch_list = git_ops.get_branches(cwd=repo_path)
    except git_ops.GitCommandError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    table = Table(title="Branches")
    table.add_column("Branch")
    table.add_column("Current", justify="center")
    for b in branch_list:
        marker = "[green]\u2714[/green]" if b.is_current else ""
        table.add_row(b.name, marker)
    console.print(table)


@cli.command()
@click.option(
    "--path", "-C", "repo_path", default=".",
    help="Path to the git repository.",
)
def status(repo_path):
    """Show the working tree status."""
    try:
        entries = git_ops.get_status(cwd=repo_path)
    except git_ops.GitCommandError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    if not entries:
        console.print("[green]Working tree clean.[/green]")
        return

    table = Table(title="Working Tree Status")
    table.add_column("Path")
    table.add_column("Staged", justify="center")
    table.add_column("Unstaged", justify="center")
    for e in entries:
        table.add_row(
            e.path,
            "\u25cf" if e.staged else "",
            "\u25cf" if e.unstaged else "",
        )
    console.print(table)


@cli.command()
@click.option(
    "--path", "-C", "repo_path", default=".",
    help="Path to the git repository.",
)
@click.option(
    "--top", "-t", default=10, show_default=True,
    help="Number of top contributors to show.",
)
def contributors(repo_path, top):
    """Show contributors ranked by commit count."""
    try:
        contributor_list = git_ops.get_contributors(cwd=repo_path, top=top)
    except git_ops.GitCommandError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    table = Table(title="Contributors")
    table.add_column("Name")
    table.add_column("Email")
    table.add_column("Commits", justify="right")
    for c in contributor_list:
        table.add_row(c.name, c.email, str(c.commit_count))
    console.print(table)


@cli.command()
@click.option(
    "--path", "-C", "repo_path", default=".",
    help="Path to the git repository.",
)
def tags(repo_path):
    """List tags and their annotation messages."""
    try:
        tag_list = git_ops.get_tags(cwd=repo_path)
    except git_ops.GitCommandError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    if not tag_list:
        console.print("[yellow]No tags found.[/yellow]")
        return

    table = Table(title="Tags")
    table.add_column("Tag")
    table.add_column("Message")
    for t in tag_list:
        table.add_row(t.name, t.message)
    console.print(table)


@cli.command()
@click.option(
    "--path", "-C", "repo_path", default=".",
    help="Path to the git repository.",
)
def remotes(repo_path):
    """List configured remotes."""
    try:
        remote_list = git_ops.get_remotes(cwd=repo_path)
    except git_ops.GitCommandError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    if not remote_list:
        console.print("[yellow]No remotes configured.[/yellow]")
        return

    table = Table(title="Remotes")
    table.add_column("Name")
    table.add_column("URL")
    table.add_column("Type")
    for r in remote_list:
        table.add_row(r.name, r.url, r.kind)
    console.print(table)


@cli.command()
@click.option(
    "--path", "-C", "repo_path", default=".",
    help="Path to the git repository.",
)
def filetypes(repo_path):
    """Show a breakdown of tracked files by extension."""
    try:
        counts = git_ops.get_filetypes(cwd=repo_path)
    except git_ops.GitCommandError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    table = Table(title="File Types")
    table.add_column("Extension")
    table.add_column("Count", justify="right")
    for ft in sorted(counts, key=lambda c: c.count, reverse=True):
        table.add_row(ft.extension, str(ft.count))
    console.print(table)


@cli.command()
@click.option(
    "--path", "-C", "repo_path", default=".",
    help="Path to the git repository.",
)
@click.option(
    "--limit", "-n", default=10, show_default=True,
    help="Number of recent commits to include.",
)
def diffstat(repo_path, limit):
    """Show aggregate insertions/deletions over recent commits."""
    try:
        stat = git_ops.get_diffstat(cwd=repo_path, limit=limit)
    except git_ops.GitCommandError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    console.print(
        f"[bold]{stat.files_changed}[/bold] files changed, "
        f"[green]+{stat.insertions}[/green] insertions, "
        f"[red]-{stat.deletions}[/red] deletions"
    )


@cli.command()
@click.option(
    "--path", "-C", "repo_path", default=".",
    help="Path to the git repository.",
)
@click.option(
    "--query", "-q", required=True,
    help="Text to search for in commit messages (case-insensitive).",
)
def search(repo_path, query):
    """Search commit messages for a keyword."""
    try:
        matches = git_ops.search_commits(cwd=repo_path, query=query)
    except git_ops.GitCommandError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise SystemExit(1)

    if not matches:
        console.print("[yellow]No matching commits.[/yellow]")
        return

    table = Table(title=f"Commits matching '{query}'")
    table.add_column("Hash", style="cyan", no_wrap=True)
    table.add_column("Author")
    table.add_column("Date")
    table.add_column("Message")
    for c in matches:
        table.add_row(c.commit_hash[:8], c.author, c.date, c.message)
    console.print(table)


if __name__ == "__main__":
    cli()
