"""Discover repos the user contributed to during a time window via GraphQL."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from gh_weekly_updates.config import auth_headers

log = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.github.com/graphql"

CONTRIBUTIONS_QUERY = """
query($user: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $user) {
    contributionsCollection(from: $from, to: $to) {
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
        contributions { totalCount }
      }
      issueContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
        contributions { totalCount }
      }
      pullRequestContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
        contributions { totalCount }
      }
      pullRequestReviewContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner }
        contributions { totalCount }
      }
    }
  }
}
"""


def discover_repos(
    token: str,
    username: str,
    since: datetime,
    until: datetime,
    org: str | None = None,
) -> list[str]:
    """Return a deduplicated, sorted list of repo nameWithOwner strings the user
    contributed to in the given window.
    """
    variables = {
        "user": username,
        "from": since.isoformat(),
        "to": until.isoformat(),
    }

    log.info("Discovering repos for %s (%s → %s)", username, since.date(), until.date())

    resp = httpx.post(
        GRAPHQL_URL,
        json={"query": CONTRIBUTIONS_QUERY, "variables": variables},
        headers=auth_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        log.error("GraphQL errors: %s", data["errors"])
        raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")

    collection = data["data"]["user"]["contributionsCollection"]

    repos: set[str] = set()
    for key in (
        "commitContributionsByRepository",
        "issueContributionsByRepository",
        "pullRequestContributionsByRepository",
        "pullRequestReviewContributionsByRepository",
    ):
        for entry in collection.get(key, []):
            repos.add(entry["repository"]["nameWithOwner"])

    if org:
        repos = {r for r in repos if r.split("/")[0].lower() == org.lower()}
        log.info("Filtered to org '%s'", org)

    sorted_repos = sorted(repos)
    log.info("Discovered %d repos: %s", len(sorted_repos), sorted_repos)
    return sorted_repos
