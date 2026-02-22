"""Tests for data models."""

from datetime import datetime, timezone

from gh_weekly_updates.models import (
    Issue,
    PullRequest,
    Review,
    WeeklyActivity,
)


def _make_activity(**overrides) -> WeeklyActivity:
    defaults = {
        "username": "testuser",
        "since": datetime(2026, 2, 9, tzinfo=timezone.utc),
        "until": datetime(2026, 2, 16, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return WeeklyActivity(**defaults)


def test_empty_activity_total():
    activity = _make_activity()
    assert activity.total_activities == 0


def test_total_activities_counts_all_types():
    activity = _make_activity(
        prs_authored=[
            PullRequest(
                repo="org/repo",
                number=1,
                title="feat: add thing",
                url="https://github.com/org/repo/pull/1",
                state="open",
                created_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
            ),
        ],
        prs_reviewed=[
            Review(
                repo="org/repo",
                pr_number=2,
                pr_title="fix: bug",
                pr_url="https://github.com/org/repo/pull/2",
                state="APPROVED",
                submitted_at=datetime(2026, 2, 11, tzinfo=timezone.utc),
            ),
        ],
        issues_created=[
            Issue(
                repo="org/repo",
                number=10,
                title="Bug report",
                url="https://github.com/org/repo/issues/10",
                state="open",
                created_at=datetime(2026, 2, 12, tzinfo=timezone.utc),
            ),
        ],
    )
    assert activity.total_activities == 3


def test_to_prompt_context_contains_username():
    activity = _make_activity()
    context = activity.to_prompt_context()
    assert "testuser" in context
    assert "2026-02-09" in context
    assert "2026-02-16" in context


def test_to_prompt_context_includes_pr_details():
    pr = PullRequest(
        repo="org/repo",
        number=42,
        title="feat: awesome feature",
        url="https://github.com/org/repo/pull/42",
        state="closed",
        created_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
        merged_at=datetime(2026, 2, 11, tzinfo=timezone.utc),
        additions=100,
        deletions=20,
        changed_files=5,
    )
    activity = _make_activity(prs_authored=[pr])
    context = activity.to_prompt_context()
    assert "org/repo#42" in context
    assert "awesome feature" in context
    assert "MERGED" in context
    assert "+100/-20" in context


def test_empty_activity_prompt_context():
    activity = _make_activity()
    context = activity.to_prompt_context()
    assert "Pull Requests Authored" not in context
    assert "Issues Created" not in context
