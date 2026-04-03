# Publishing QA-MCP

This document describes the release process for the `qa-mcp` Python package and the companion Docker image.

## Release Model

QA-MCP uses a tag-driven release flow.

Pushing a semantic version tag such as `v1.0.3` triggers:

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

At minimum, align the version across:

- `pyproject.toml`
- `src/qa_mcp/__init__.py`
- `Dockerfile`
- `docker-compose.yml` if image defaults are version-pinned
- `CHANGELOG.md`
- any release-oriented documentation that explicitly mentions the current stable version

Example:

```toml
version = "1.0.3"
```

### 2. Verify the package locally

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run --extra dev mypy src
uv run qa-mcp --version
docker build -t qa-mcp:1.0.3 .
docker run --rm qa-mcp:1.0.3 --version
```

### 3. Commit and push `main`

```bash
git add .
git commit -m "chore: prepare 1.0.3 release"
git push origin main
```

### 4. Create and push the release tag

```bash
git tag -a v1.0.3 -m "QA-MCP v1.0.3"
git push origin v1.0.3
```

That tag push is what starts the release automation.

## What the Workflows Do

### Release workflow

Triggered by:

- `push` on tags matching `v*.*.*`

Responsibilities:

- Build and push multi-arch Docker images
- Publish semver Docker tags such as `1.0.3`, `1.0`, `1`, and `latest`
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
git tag -d v1.0.3
git push origin :refs/tags/v1.0.3
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
