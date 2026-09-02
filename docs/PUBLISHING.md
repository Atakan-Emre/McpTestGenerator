# Publishing QA-MCP

This document describes the release process for the `qa-mcp` Python package and the companion Docker image.

## Release Model

QA-MCP uses a tag-driven release flow.

Pushing a semantic version tag such as `v2.0.0` triggers:

- Docker image build and publish to Docker Hub
- GitHub release creation
- PyPI package build and publish

The release source of truth is the Git tag.

## Required Secrets

Repository Actions secrets must contain:

- `PYPI_API_TOKEN`
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Without these, release workflows will fail.

## Standard Release Procedure

### 1. Update versioned files

```bash
make bump VERSION=2.1.1
```

Use the target rather than a search-and-replace. The old version string also
appears inside dependency pins, and a blanket replace during the 2.1.0 release
silently turned `pydantic>=2.0.0` into `pydantic>=2.1.0`. The script edits one
anchored line per file and fails if an anchor is missing.

It covers:

- `pyproject.toml`
- `src/qa_mcp/__init__.py`
- `Dockerfile`
- `docker-compose.yml` (the `${VERSION:-...}` image defaults)
- `DOCKERHUB.md` (the "Current stable release" row)
- `CHANGELOG.md` (a new heading; the newest entry must match the package version)

`tests/test_ci_config.py::TestVersionConsistency` asserts all of these agree, so
a missed file fails a test rather than shipping a mismatched release.

Example:

```toml
version = "2.0.0"
```

### 2. Verify the package locally

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run --extra dev mypy src
uv run qa-mcp --version
docker build -t qa-mcp:2.0.0 .
docker run --rm qa-mcp:2.0.0 --version
```

### 3. Commit and push `main`

```bash
git add .
git commit -m "chore: prepare 2.0.0 release"
git push origin main
```

### 4. Create and push the release tag

```bash
git tag -a v2.0.0 -m "QA-MCP v2.0.0"
git push origin v2.0.0
```

That tag push is what starts the release automation.

## What the Workflows Do

### Release workflow

Triggered by:

- `push` on tags matching `v*.*.*`

Responsibilities:

- Build and push multi-arch Docker images
- Publish semver Docker tags such as `2.0.0`, `2.0`, `2`, and `latest`
- Create the GitHub release page

### Publish to PyPI workflow

Triggered by:

- `push` on tags matching `v*.*.*`
- `release.published`
- `workflow_dispatch`

Responsibilities:

- Build the Python package
- Upload to PyPI with `twine upload --skip-existing`
- Allow safe re-runs for already-published versions

## Verification Checklist

After pushing the version tag, verify:

- GitHub release exists for the tag
- PyPI shows the new package version
- Docker Hub shows the new version tag
- `latest` on Docker Hub points to the newest stable release
- `pip install qa-mcp==<version>` works
- `docker run --rm atakanemree/qa-mcp:<version> --version` works

Useful endpoints:

- PyPI: https://pypi.org/project/qa-mcp/
- Docker Hub: https://hub.docker.com/r/atakanemree/qa-mcp/tags
- Releases: https://github.com/Atakan-Emre/McpTestGenerator/releases
- Actions: https://github.com/Atakan-Emre/McpTestGenerator/actions

## Recovery Paths

### PyPI publish failed but artifacts are correct

Re-run the `Publish to PyPI` workflow from GitHub Actions.
Because the workflow uses `--skip-existing`, re-running is safe for already-uploaded files.

### Docker publish failed

Re-run the `Release` workflow run for the tag if the failure is transient.
If the tag points to the wrong commit, delete the tag locally and remotely, recreate it, and push again.

### Wrong version was tagged

If the tag has not been consumed externally yet:

```bash
git tag -d v2.0.0
git push origin :refs/tags/v2.0.0
```

Then fix the versioned files, recommit if necessary, recreate the tag, and push again.

If PyPI has already accepted the version, do not reuse the same version number. Increment the package version.

## Manual Fallback: PyPI Only

If GitHub Actions cannot be used, publish manually:

```bash
rm -rf dist build *.egg-info
uv run python -m pip install --upgrade build twine
uv run python -m build
uv run twine check dist/*
uv run twine upload dist/*
```

Then verify:

```bash
pip install --upgrade qa-mcp
qa-mcp --version
```

## Versioning Policy

QA-MCP follows Semantic Versioning:

- `MAJOR`: breaking changes
- `MINOR`: backward-compatible feature additions
- `PATCH`: backward-compatible fixes and documentation corrections
