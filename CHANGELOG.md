# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] — 2026-02-20

### Added

- Initial release
- Auto-discover repos via GitHub GraphQL contributions API
- Collect PRs authored/reviewed, issues created/commented, discussions
- AI-powered summarisation via GitHub Models (OpenAI-compatible)
- Structured output: Wins / Strategic Influence / Challenges
- YAML config file support (`config.yaml`)
- Custom prompt support (inline or via file)
- Push summary to a GitHub repo under `weekly-updates/`
- Rich terminal output with progress indicators
- CLI with `--since`, `--until`, `--org`, `--repos`, `--push`, `--output`, `--model`, `--config`, `--verbose`
