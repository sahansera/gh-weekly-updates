"""Tests for config helpers."""

from gh_weekly_updates.config import auth_headers


def test_auth_headers_format():
    headers = auth_headers("ghp_test123")
    assert headers["Authorization"] == "Bearer ghp_test123"
    assert "application/vnd.github" in headers["Accept"]
    assert "X-GitHub-Api-Version" in headers


def test_auth_headers_returns_dict():
    headers = auth_headers("token")
    assert isinstance(headers, dict)
    assert len(headers) == 3
