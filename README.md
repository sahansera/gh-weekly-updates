# gh-weekly-updates

> Automatically discover and summarise your weekly GitHub impact using AI.

`gh-weekly-updates` collects your GitHub activity — pull requests authored & reviewed, issues created & commented on, discussions — and generates a structured Markdown summary using [GitHub Models](https://github.com/marketplace/models).

## Features

- **Auto-discover repos** via the GitHub GraphQL Contributions API, or provide an explicit list
- **Collect detailed activity**: PRs, reviews, issues, issue comments, discussions
- **AI-powered summarisation** via GitHub Models (`openai/gpt-4.1` by default)
- **Structured output**: Wins / Challenges / What's Next — grouped by project or theme, with inline links
- **Push to a repo**: automatically commit summaries to a GitHub repo for sharing
- **Fully configurable**: org, repos, model, prompt — via YAML config or CLI flags
- **Custom prompts**: tailor the AI summary to your team's format

## Installation

```bash
pip install gh-weekly-updates
```

### Requirements

- Python 3.11+
- A GitHub personal access token (PAT) **or** the [GitHub CLI](https://cli.github.com/) (`gh`) authenticated
  - Required scopes: `repo`, `read:org`
- Access to [GitHub Models](https://github.com/marketplace/models) for AI summarisation
  - Your GitHub account must have GitHub Models enabled. Visit the [Models marketplace](https://github.com/marketplace/models) to check access.
  - The same PAT / `gh` token is used to authenticate with the Models inference endpoint — no separate API key needed.

## Quick start

```bash
# Authenticate with the GitHub CLI (easiest)
gh auth login

# Run with defaults — covers the past week
gh-weekly-updates

# Or specify a date range
gh-weekly-updates --since 2025-06-01 --until 2025-06-07
```

## Configuration

Create a `config.yaml` (see [config.example.yaml](config.example.yaml)):

```yaml
# GitHub org to scope repo discovery to
org: my-org

# Explicit repo list (skips auto-discovery)
repos:
  - my-org/api-service
  - my-org/web-app

# GitHub Model for summarisation
model: openai/gpt-4.1

# Push summary to a repo under weekly-updates/
push_repo: my-user/my-updates

# Custom system prompt (inline)
prompt: |
  You are an engineering manager writing a concise weekly summary...

# Or load prompt from a file
# prompt_file: my-prompt.txt
```

## CLI reference

```
Usage: gh-weekly-updates [OPTIONS]

Options:
  --config PATH    Path to YAML config file. Default: ./config.yaml
  --since TEXT      Start date (ISO 8601). Default: previous Monday.
  --until TEXT      End date (ISO 8601). Default: now.
  --user TEXT       GitHub username. Default: authenticated user.
  --repos TEXT      Comma-separated list of repos (owner/name).
  --org TEXT        GitHub org to scope repo discovery to.
  --output PATH    Write summary to a file instead of stdout.
  --push TEXT       Push summary to a GitHub repo (owner/name).
  --model TEXT      GitHub Model to use. Default: openai/gpt-4.1.
  --verbose         Enable debug logging.
  --help            Show this message and exit.
```

## Authentication

`gh-weekly-updates` resolves a GitHub token in this order:

1. `GITHUB_TOKEN` environment variable
2. `gh auth token` (GitHub CLI)

For GitHub Enterprise with SSO, ensure the token is authorised for your org.

## Using with GitHub Actions

You can run `gh-weekly-updates` on a schedule in a GitHub Actions workflow:

```yaml
name: Weekly Impact Summary

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9am UTC
  workflow_dispatch:

jobs:
  summarise:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install gh-weekly-updates
        run: pip install gh-weekly-updates

      - name: Generate summary
        env:
          GITHUB_TOKEN: ${{ secrets.GH_PAT }}  # must be named GITHUB_TOKEN
        run: |
          gh-weekly-updates \
            --config config.yaml \
            --push my-user/my-updates
```

> **Note**: The default `GITHUB_TOKEN` provided by Actions has limited scope.
> Use a [Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) stored as a repository secret with `repo` and `read:org` scopes, plus GitHub Models access.

## Development

```bash
git clone https://github.com/sahansera/gh-weekly-updates.git
cd gh-weekly-updates
python -m venv .venv && source .venv/bin/activate
make dev   # install in editable mode with dev deps
make run   # run with defaults
make lint  # ruff check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License

[MIT](LICENSE)
