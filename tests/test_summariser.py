"""Tests for the summariser module."""

from datetime import datetime, timezone

from gh_weekly_updates.models import WeeklyActivity
from gh_weekly_updates.summariser import SYSTEM_PROMPT


def test_system_prompt_has_required_sections():
    assert "Wins" in SYSTEM_PROMPT
    assert "Challenges" in SYSTEM_PROMPT
    assert "What's Next" in SYSTEM_PROMPT
    assert "Activity Summary" in SYSTEM_PROMPT


def test_system_prompt_no_internal_references():
    """Prompt should not contain internal org or career-level references."""
    assert "Strategic Influence" not in SYSTEM_PROMPT
    assert "engineering manager" not in SYSTEM_PROMPT.lower()
    assert "career level" not in SYSTEM_PROMPT.lower()


def test_empty_activity_returns_no_activity_message():
    from gh_weekly_updates.summariser import summarise

    activity = WeeklyActivity(
        username="testuser",
        since=datetime(2026, 2, 9, tzinfo=timezone.utc),
        until=datetime(2026, 2, 16, tzinfo=timezone.utc),
    )
    # Should return a static message without calling the API
    result = summarise(activity, token="fake-token")
    assert "No GitHub activity found" in result
    assert "testuser" in result
