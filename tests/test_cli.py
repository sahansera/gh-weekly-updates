"""Tests for CLI entry point."""

from click.testing import CliRunner

from gh_weekly_updates.cli import main


def test_cli_help():
    """CLI --help should exit 0 and show usage."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--config" in result.output


def test_cli_requires_auth(monkeypatch):
    """CLI should fail gracefully when no GitHub token is available."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    # Also ensure `gh` CLI won't resolve a token
    monkeypatch.setenv("PATH", "")

    runner = CliRunner()
    result = runner.invoke(main, ["--config", "/dev/null"])
    assert result.exit_code != 0
