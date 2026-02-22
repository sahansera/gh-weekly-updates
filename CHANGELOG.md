# Changelog

All notable changes to this project will be documented in this file.

## [0.1.3] — 2026-02-22

### Changed

- Bump version for PyPI release incorporating all fixes since v0.1.0

## [0.1.2] — 2026-02-22

### Fixed

- Fix `NameError: name 'username' is not defined` when using `push_repo` config option — the `publish_to_repo()` call now correctly references the `user` variable

## [0.1.1] — 2026-02-20

### Fixed

- Embed token in clone URL for CI auth
- Cleaner HTTP 422 warnings when token lacks access to a repo
- Add `contents:read` permission for checkout

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

[0.1.3]: https://github.com/sahansera/gh-weekly-updates/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/sahansera/gh-weekly-updates/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/sahansera/gh-weekly-updates/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/sahansera/gh-weekly-updates/releases/tag/v0.1.0
