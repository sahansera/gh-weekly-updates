"""Authentication and configuration helpers."""

from __future__ import annotations

import logging
import os
import subprocess
import sys

log = logging.getLogger(__name__)


def get_github_token() -> str:
    """Resolve a GitHub token from the environment or gh CLI.

    Priority:
        1. GITHUB_TOKEN env var
        2. `gh auth token` output
    """
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        log.debug("Using GITHUB_TOKEN from environment")
        return token.strip()

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        token = result.stdout.strip()
        if token:
            log.debug("Using token from gh CLI")
            return token
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print(
        "Error: No GitHub token found.\n"
        "Either set GITHUB_TOKEN or run `gh auth login` first.",
        file=sys.stderr,
    )
    sys.exit(1)


def get_github_username(token: str) -> str:
    """Get the authenticated user's login from the GitHub API."""
    import httpx

    resp = httpx.get(
        "https://api.github.com/user",
        headers=_auth_headers(token),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["login"]


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
