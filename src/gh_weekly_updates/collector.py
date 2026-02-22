"""Collect detailed activity from GitHub for a set of repos."""

from __future__ import annotations

import logging
import time
from datetime import datetime

import httpx

from gh_weekly_updates.config import auth_headers
from gh_weekly_updates.models import (
    Discussion,
    DiscussionComment,
    Issue,
    IssueComment,
    PullRequest,
    Review,
    WeeklyActivity,
)

log = logging.getLogger(__name__)

SEARCH_URL = "https://api.github.com/search/issues"
GRAPHQL_URL = "https://api.github.com/graphql"
PER_PAGE = 100


def _sleep_for_rate_limit(resp: httpx.Response) -> None:
    """If we're close to the rate limit, sleep until reset."""
    remaining = int(resp.headers.get("x-ratelimit-remaining", "99"))
    if remaining < 5:
        reset_at = int(resp.headers.get("x-ratelimit-reset", "0"))
        wait = max(reset_at - int(time.time()), 1)
        log.warning("Rate limit low (%d remaining), sleeping %ds", remaining, wait)
        time.sleep(wait)


def _search_issues(
    token: str,
    query: str,
    since: datetime,
    until: datetime,
) -> list[dict]:
    """Run a GitHub search/issues query with date range and pagination."""
    date_range = f"{since.strftime('%Y-%m-%d')}..{until.strftime('%Y-%m-%d')}"
    full_query = f"{query} created:{date_range}"
    headers = auth_headers(token)

    results: list[dict] = []
    page = 1
    while True:
        resp = httpx.get(
            SEARCH_URL,
            params={"q": full_query, "per_page": PER_PAGE, "page": page},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        _sleep_for_rate_limit(resp)

        data = resp.json()
        items = data.get("items", [])
        results.extend(items)

        if len(items) < PER_PAGE or len(results) >= data.get("total_count", 0):
            break
        page += 1

    return results


def _search_issues_updated(
    token: str,
    query: str,
    since: datetime,
    until: datetime,
) -> list[dict]:
    """Search with 'updated' instead of 'created' date range."""
    date_range = f"{since.strftime('%Y-%m-%d')}..{until.strftime('%Y-%m-%d')}"
    full_query = f"{query} updated:{date_range}"
    headers = auth_headers(token)

    results: list[dict] = []
    page = 1
    while True:
        resp = httpx.get(
            SEARCH_URL,
            params={"q": full_query, "per_page": PER_PAGE, "page": page},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        _sleep_for_rate_limit(resp)

        data = resp.json()
        items = data.get("items", [])
        results.extend(items)

        if len(items) < PER_PAGE or len(results) >= data.get("total_count", 0):
            break
        page += 1

    return results


def _fetch_pr_details(token: str, repo: str, number: int) -> dict:
    """Fetch full PR details (additions, deletions, etc.)."""
    url = f"https://api.github.com/repos/{repo}/pulls/{number}"
    resp = httpx.get(url, headers=auth_headers(token), timeout=30)
    resp.raise_for_status()
    _sleep_for_rate_limit(resp)
    return resp.json()


def _fetch_reviews_for_pr(token: str, repo: str, pr_number: int) -> list[dict]:
    """Fetch all reviews for a specific PR."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    resp = httpx.get(
        url,
        headers=auth_headers(token),
        params={"per_page": PER_PAGE},
        timeout=30,
    )
    resp.raise_for_status()
    _sleep_for_rate_limit(resp)
    return resp.json()


def _fetch_issue_comments_by_user(
    token: str,
    repo: str,
    username: str,
    since: datetime,
) -> list[dict]:
    """Fetch issue comments by a specific user in a repo since a date."""
    url = f"https://api.github.com/repos/{repo}/issues/comments"
    headers = auth_headers(token)
    results: list[dict] = []
    page = 1

    while True:
        resp = httpx.get(
            url,
            headers=headers,
            params={
                "since": since.isoformat(),
                "per_page": PER_PAGE,
                "page": page,
                "sort": "created",
                "direction": "desc",
            },
            timeout=30,
        )
        resp.raise_for_status()
        _sleep_for_rate_limit(resp)

        items = resp.json()
        # Filter to only this user's comments
        user_comments = [c for c in items if c.get("user", {}).get("login") == username]
        results.extend(user_comments)

        if len(items) < PER_PAGE:
            break
        page += 1

    return results


# ---------------------------------------------------------------------------
# Discussions (GraphQL)
# ---------------------------------------------------------------------------

DISCUSSIONS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    discussions(first: 50, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        url
        createdAt
        body
        category { name }
        author { login }
        comments(first: 50) {
          nodes {
            author { login }
            body
            createdAt
          }
        }
      }
    }
  }
}
"""


def _fetch_discussions(
    token: str,
    repo: str,
    username: str,
    since: datetime,
    until: datetime,
) -> tuple[list[Discussion], list[DiscussionComment]]:
    """Fetch discussions where the user is author or commenter."""
    owner, name = repo.split("/", 1)
    headers = auth_headers(token)
    created: list[Discussion] = []
    commented: list[DiscussionComment] = []
    cursor = None

    for _ in range(5):  # max 5 pages
        variables: dict = {"owner": owner, "name": name}
        if cursor:
            variables["cursor"] = cursor

        resp = httpx.post(
            GRAPHQL_URL,
            json={"query": DISCUSSIONS_QUERY, "variables": variables},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if "errors" in data:
            log.debug("Discussions query error for %s: %s", repo, data["errors"])
            break

        repo_data = data.get("data", {}).get("repository")
        if not repo_data or not repo_data.get("discussions"):
            break

        discussions = repo_data["discussions"]
        for node in discussions.get("nodes", []):
            created_at = datetime.fromisoformat(node["createdAt"].replace("Z", "+00:00"))
            if created_at < since:
                # Discussions are sorted DESC by created_at, so we can stop
                return created, commented
            if created_at > until:
                continue

            author_login = (node.get("author") or {}).get("login", "")

            if author_login == username:
                created.append(
                    Discussion(
                        repo=repo,
                        number=node["number"],
                        title=node["title"],
                        url=node["url"],
                        created_at=created_at,
                        body=node.get("body"),
                        category=(node.get("category") or {}).get("name"),
                    )
                )

            # Check comments
            for comment in (node.get("comments") or {}).get("nodes", []):
                comment_author = (comment.get("author") or {}).get("login", "")
                if comment_author == username:
                    comment_at = datetime.fromisoformat(
                        comment["createdAt"].replace("Z", "+00:00")
                    )
                    if since <= comment_at <= until:
                        commented.append(
                            DiscussionComment(
                                repo=repo,
                                discussion_number=node["number"],
                                discussion_title=node["title"],
                                discussion_url=node["url"],
                                body=comment.get("body", ""),
                                created_at=comment_at,
                            )
                        )

        page_info = discussions.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    return created, commented


# ---------------------------------------------------------------------------
# Main collector
# ---------------------------------------------------------------------------


def collect_activity(
    token: str,
    username: str,
    repos: list[str],
    since: datetime,
    until: datetime,
) -> WeeklyActivity:
    """Collect all GitHub activity for the user across the given repos."""
    activity = WeeklyActivity(
        username=username,
        since=since,
        until=until,
        repos=repos,
    )

    for repo in repos:
        log.info("Collecting activity for %s", repo)

        # --- PRs authored ---
        try:
            pr_items = _search_issues(
                token, f"author:{username} repo:{repo} type:pr", since, until
            )
            for item in pr_items:
                pr_detail = _fetch_pr_details(token, repo, item["number"])
                activity.prs_authored.append(
                    PullRequest(
                        repo=repo,
                        number=item["number"],
                        title=item["title"],
                        url=item["html_url"],
                        state=pr_detail.get("merged_at") and "merged" or item["state"],
                        created_at=item["created_at"],
                        merged_at=pr_detail.get("merged_at"),
                        body=item.get("body"),
                        additions=pr_detail.get("additions", 0),
                        deletions=pr_detail.get("deletions", 0),
                        changed_files=pr_detail.get("changed_files", 0),
                        labels=[l["name"] for l in item.get("labels", [])],
                        review_comments=pr_detail.get("review_comments", 0),
                    )
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 422):
                log.warning("Skipping PRs authored for %s (HTTP %d — token may lack access)", repo, e.response.status_code)
            else:
                log.exception("Error fetching PRs authored for %s", repo)
        except Exception:
            log.exception("Error fetching PRs authored for %s", repo)

        # --- PRs reviewed ---
        try:
            reviewed_items = _search_issues_updated(
                token, f"reviewed-by:{username} repo:{repo} type:pr", since, until
            )
            # Exclude self-authored PRs
            authored_numbers = {pr.number for pr in activity.prs_authored if pr.repo == repo}
            for item in reviewed_items:
                if item["number"] in authored_numbers:
                    continue
                reviews = _fetch_reviews_for_pr(token, repo, item["number"])
                user_reviews = [
                    r
                    for r in reviews
                    if r.get("user", {}).get("login") == username
                    and r.get("state") != "PENDING"
                ]
                for rev in user_reviews:
                    submitted = rev.get("submitted_at")
                    if submitted:
                        submitted_dt = datetime.fromisoformat(
                            submitted.replace("Z", "+00:00")
                        )
                        if since <= submitted_dt <= until:
                            activity.prs_reviewed.append(
                                Review(
                                    repo=repo,
                                    pr_number=item["number"],
                                    pr_title=item["title"],
                                    pr_url=item["html_url"],
                                    state=rev["state"],
                                    submitted_at=submitted_dt,
                                    body=rev.get("body"),
                                )
                            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 422):
                log.warning("Skipping reviews for %s (HTTP %d — token may lack access)", repo, e.response.status_code)
            else:
                log.exception("Error fetching reviews for %s", repo)
        except Exception:
            log.exception("Error fetching reviews for %s", repo)

        # --- Issues created ---
        try:
            issue_items = _search_issues(
                token, f"author:{username} repo:{repo} type:issue", since, until
            )
            for item in issue_items:
                activity.issues_created.append(
                    Issue(
                        repo=repo,
                        number=item["number"],
                        title=item["title"],
                        url=item["html_url"],
                        state=item["state"],
                        created_at=item["created_at"],
                        body=item.get("body"),
                        labels=[l["name"] for l in item.get("labels", [])],
                        comments=item.get("comments", 0),
                    )
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 422):
                log.warning("Skipping issues for %s (HTTP %d — token may lack access)", repo, e.response.status_code)
            else:
                log.exception("Error fetching issues for %s", repo)
        except Exception:
            log.exception("Error fetching issues for %s", repo)

        # --- Issue comments ---
        try:
            comments = _fetch_issue_comments_by_user(token, repo, username, since)
            # Filter to within the until boundary
            for c in comments:
                created_at = datetime.fromisoformat(
                    c["created_at"].replace("Z", "+00:00")
                )
                if created_at > until:
                    continue
                # Get the issue title from the issue_url
                issue_url = c.get("issue_url", "")
                issue_number = int(issue_url.rsplit("/", 1)[-1]) if issue_url else 0
                html_url = c.get("html_url", "")
                # Derive issue HTML URL from comment URL
                issue_html_url = html_url.rsplit("#", 1)[0] if html_url else ""

                activity.issue_comments.append(
                    IssueComment(
                        repo=repo,
                        issue_number=issue_number,
                        issue_title=f"#{issue_number}",  # Will be enriched if needed
                        issue_url=issue_html_url,
                        body=c.get("body", ""),
                        created_at=created_at,
                    )
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 422):
                log.warning("Skipping issue comments for %s (HTTP %d — token may lack access)", repo, e.response.status_code)
            else:
                log.exception("Error fetching issue comments for %s", repo)
        except Exception:
            log.exception("Error fetching issue comments for %s", repo)

        # --- Discussions ---
        try:
            disc_created, disc_commented = _fetch_discussions(
                token, repo, username, since, until
            )
            activity.discussions_created.extend(disc_created)
            activity.discussion_comments.extend(disc_commented)
        except Exception:
            log.exception("Error fetching discussions for %s", repo)

    log.info(
        "Collected %d total activities across %d repos",
        activity.total_activities,
        len(repos),
    )
    return activity
