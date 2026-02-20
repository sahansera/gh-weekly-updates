"""CLI entrypoint for gh-weekly-updates."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.panel import Panel

from gh_weekly_updates.collector import collect_activity
from gh_weekly_updates.config import get_github_token, get_github_username
from gh_weekly_updates.contributions import discover_repos
from gh_weekly_updates.publisher import publish_to_repo
from gh_weekly_updates.summariser import DEFAULT_MODEL, summarise

console = Console()

DEFAULT_CONFIG_PATH = "config.yaml"


def _load_config(path: str | None) -> dict:
    """Load YAML config file. Returns empty dict if not found."""
    config_path = Path(path) if path else Path(DEFAULT_CONFIG_PATH)
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _default_since() -> datetime:
    """Return the previous Monday 00:00 UTC so we always cover at least a full week."""
    now = datetime.now(timezone.utc)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_monday = now.weekday()  # Monday=0
    # Always go back to LAST week's Monday (7 + days_since_monday days back)
    # e.g. Tuesday → 8 days back, Monday → 7 days back
    return today_midnight - timedelta(days=days_since_monday + 7)


def _parse_date(value: str) -> datetime:
    """Parse an ISO-8601 date string into a timezone-aware datetime."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@click.command()
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(),
    help="Path to YAML config file. Default: ./config.yaml",
)
@click.option(
    "--since",
    default=None,
    help="Start date (ISO 8601). Default: Monday of previous week.",
)
@click.option(
    "--until",
    default=None,
    help="End date (ISO 8601). Default: now.",
)
@click.option(
    "--user",
    default=None,
    help="GitHub username. Default: authenticated user.",
)
@click.option(
    "--repos",
    default=None,
    help="Comma-separated list of repos (owner/name). Skips auto-discovery.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Write summary to file instead of stdout.",
)
@click.option(
    "--org",
    default=None,
    help="GitHub org to scope repo discovery to.",
)
@click.option(
    "--push",
    "push_repo",
    default=None,
    help="Push summary to a GitHub repo (owner/name).",
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="GitHub Model to use for summarisation.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable debug logging.",
)
def main(
    config_path: str | None,
    since: str | None,
    until: str | None,
    user: str | None,
    repos: str | None,
    org: str | None,
    push_repo: str | None,
    output: str | None,
    model: str,
    verbose: bool,
) -> None:
    """Discover your weekly GitHub impact and generate a structured summary."""
    # --- Load config ---
    cfg = _load_config(config_path)

    # CLI flags override config file values
    org = org or cfg.get("org")
    model = model if model != DEFAULT_MODEL else cfg.get("model", model)
    push_repo = push_repo or cfg.get("push_repo")

    # Custom prompt: inline in config or from a file
    custom_prompt = cfg.get("prompt")
    if not custom_prompt and cfg.get("prompt_file"):
        prompt_path = Path(cfg["prompt_file"])
        if prompt_path.exists():
            custom_prompt = prompt_path.read_text()

    # Repos: CLI --repos flag (comma-separated) > config file list
    if repos:
        repo_list_override = [r.strip() for r in repos.split(",") if r.strip()]
    elif cfg.get("repos"):
        repo_list_override = cfg["repos"]
    else:
        repo_list_override = None

    # --- Logging ---
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
    log = logging.getLogger("gh_weekly_updates")

    # --- Auth ---
    with console.status("[bold green]Authenticating with GitHub..."):
        token = get_github_token()

    # --- Resolve user ---
    if not user:
        with console.status("[bold green]Resolving GitHub username..."):
            user = get_github_username(token)
    console.print(f"[bold]User:[/bold] {user}")
    if org:
        console.print(f"[bold]Org:[/bold]  {org}")

    # --- Date range ---
    since_dt = _parse_date(since) if since else _default_since()
    until_dt = _parse_date(until) if until else datetime.now(timezone.utc)

    console.print(
        f"[bold]Period:[/bold] {since_dt.strftime('%Y-%m-%d')} → "
        f"{until_dt.strftime('%Y-%m-%d %H:%M')} UTC"
    )

    # --- Resolve repos ---
    if repo_list_override:
        repo_list = repo_list_override
        console.print(f"[bold]Using configured repos:[/bold] {len(repo_list)}")
    else:
        with console.status("[bold green]Discovering repos you contributed to..."):
            repo_list = discover_repos(token, user, since_dt, until_dt, org=org)

    if not repo_list:
        console.print("[yellow]No repos found for this period. Nothing to summarise.[/yellow]")
        sys.exit(0)

    console.print(f"[bold]Repos:[/bold] {len(repo_list)}")
    for r in repo_list:
        console.print(f"  • {r}")

    # --- Collect activity ---
    with console.status("[bold green]Collecting activity across repos..."):
        activity = collect_activity(token, user, repo_list, since_dt, until_dt)

    console.print(
        Panel(
            f"[bold]{activity.total_activities}[/bold] activities collected\n"
            f"  PRs authored:         {len(activity.prs_authored)}\n"
            f"  PRs reviewed:         {len(activity.prs_reviewed)}\n"
            f"  Issues created:       {len(activity.issues_created)}\n"
            f"  Issue comments:       {len(activity.issue_comments)}\n"
            f"  Discussions created:  {len(activity.discussions_created)}\n"
            f"  Discussion comments:  {len(activity.discussion_comments)}",
            title="Activity Summary",
            border_style="green",
        )
    )

    if activity.total_activities == 0:
        console.print("[yellow]No activities found. Nothing to summarise.[/yellow]")
        sys.exit(0)

    # --- Summarise ---
    with console.status("[bold green]Generating impact summary via AI..."):
        summary = summarise(activity, token, model, custom_prompt=custom_prompt)

    # --- Output ---
    if output:
        with open(output, "w") as f:
            f.write(summary)
        console.print(f"\n[bold green]Summary written to {output}[/bold green]")
    else:
        console.print()
        console.print(Markdown(summary))

    # --- Push to repo ---
    if push_repo:
        with console.status(f"[bold green]Pushing to {push_repo}..."):
            publish_to_repo(summary, push_repo, since_dt, until_dt, token=token, username=username)
        console.print(
            f"\n[bold green]Pushed to https://github.com/{push_repo}/tree/main/weekly-updates[/bold green]"
        )


if __name__ == "__main__":
    main()
