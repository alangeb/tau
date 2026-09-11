---
category: operations
description: "Version bumping, changelog generation, release notes, git tags — semantic versioning, release checklist (also load: git, documentation, spec)"
keywords: version bump, changelog, release notes, git tag, semantic versioning, release checklist, version number, release process
name: release_management
---

# Release Management

## When
"release" | "version bump" | "changelog" | "release notes" | "git tag" | "semantic version" | "v1.2.3"

## Version Scheme
Semantic versioning: `MAJOR.MINOR.PATCH`
- MAJOR: breaking changes
- MINOR: new features, backward compatible
- PATCH: bug fixes

## Release Checklist
- [ ] All tests pass (`bash sanity.sh`)
- [ ] Changelog updated (`CHANGELOG.md`)
- [ ] Version bumped (all version files)
- [ ] Git tag created (`git tag -a v1.2.3 -m "Release v1.2.3"`)
- [ ] Push tag (`git push origin v1.2.3`)

## Changelog Format
```markdown
## [v1.2.3] - 2024-01-15
### Added
- New feature
### Fixed
- Bug fix
### Changed
- Breaking change (MAJOR bump)
```

## Helper
`python3 skills/release_management/release_check.py` — verify release readiness

## Related Skills
- `git` — Tag and push
- `documentation` — Update docs
- `spec` — Design docs
- `tau_testsuite` — Verify tests
- `tauskillmaintenance` — Skill quality audit and maintenance
