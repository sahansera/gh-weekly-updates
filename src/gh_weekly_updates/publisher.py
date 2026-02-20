"""Publish weekly impact summaries to a GitHub repository."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)


def publish_to_repo(
    summary: str,
    push_repo: str,
    since: datetime,
    until: datetime,
) -> None:
    """Clone the target repo, write the summary under weekly-updates/, commit, and push.

    Args:
        summary: The markdown summary content.
        push_repo: Repo in "owner/name" format (e.g. "user/my-updates").
        since: Start date of the summary period.
        until: End date of the summary period.
    """
    filename = f"impact-{since.strftime('%Y-%m-%d')}-to-{until.strftime('%Y-%m-%d')}.md"
    target_dir = "weekly-updates"

    with tempfile.TemporaryDirectory(prefix="gh-weekly-updates-") as tmpdir:
        repo_url = f"https://github.com/{push_repo}.git"
        repo_path = Path(tmpdir) / "repo"

        log.info("Cloning %s", push_repo)
        _run_git(["clone", "--depth", "1", repo_url, str(repo_path)])

        # Ensure weekly-updates/ exists
        dest_dir = repo_path / target_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Write the summary
        dest_file = dest_dir / filename
        dest_file.write_text(summary)
        log.info("Wrote %s/%s", target_dir, filename)

        # Git add, commit, push
        _run_git(["add", f"{target_dir}/{filename}"], cwd=repo_path)

        commit_msg = (
            f"weekly-updates: {since.strftime('%Y-%m-%d')} → {until.strftime('%Y-%m-%d')}"
        )
        _run_git(["commit", "-m", commit_msg], cwd=repo_path)
        _run_git(["push"], cwd=repo_path)

        log.info("Pushed to %s", push_repo)


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command, using gh for auth."""
    env_cmd = ["git"] + args
    result = subprocess.run(
        env_cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=60,
    )
    if result.returncode != 0:
        log.error("git %s failed: %s", " ".join(args), result.stderr.strip())
        raise RuntimeError(f"git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()
