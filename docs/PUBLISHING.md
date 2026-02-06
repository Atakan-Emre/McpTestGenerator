# Publishing QA-MCP to PyPI

This guide explains how to publish the `qa-mcp` package to PyPI (Python Package Index).

## 📋 Prerequisites

### 1. PyPI Account Setup

1. **Create PyPI account**: https://pypi.org/account/register/
2. **Create Test PyPI account**: https://test.pypi.org/account/register/
3. **Enable 2FA** (highly recommended for security)

### 2. API Tokens

1. **PyPI API Token**:
   - Go to: https://pypi.org/manage/account/token/
   - Create new token with scope: "Entire account" or specific to `qa-mcp`
   - **Save the token** - you won't see it again!

2. **Test PyPI API Token**:
   - Go to: https://test.pypi.org/manage/account/token/
   - Create new token
   - Save the token

### 3. GitHub Secrets

Add the tokens to your GitHub repository secrets:

1. Go to: `Settings` → `Secrets and variables` → `Actions`
2. Add two secrets:
   - `PYPI_API_TOKEN` - Your production PyPI token
   - `TEST_PYPI_API_TOKEN` - Your Test PyPI token

## 🧪 Testing Release (Test PyPI)

Before publishing to production PyPI, test with Test PyPI:

### Manual Test

```bash
# 1. Build the package
python -m pip install --upgrade build twine
python -m build

# 2. Check the built package
twine check dist/*

# 3. Upload to Test PyPI
twine upload --repository testpypi dist/*
# Enter __token__ as username
# Paste your TEST_PYPI_API_TOKEN as password

# 4. Test installation
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ qa-mcp

# 5. Test it works
qa-mcp --help
```

### Automated Test (GitHub Actions)

```bash
# Trigger manual workflow
# Go to: Actions → "Publish to PyPI" → "Run workflow"
# This will publish to Test PyPI
```

## 🚀 Production Release

### Option 1: Automated Release (Recommended)

When you create a GitHub release, the package is automatically published:

1. **Update version** in `pyproject.toml`
   ```toml
   version = "1.0.1"  # or whatever the next version is
   ```

2. **Update CHANGELOG.md**
   ```markdown
   ## [1.0.1] - 2025-02-06
   
   ### Added
   - New feature...
   
   ### Fixed
   - Bug fix...
   ```

3. **Commit and push**
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: bump version to 1.0.1"
   git push origin main
   ```

4. **Create GitHub Release**
   - Go to: https://github.com/Atakan-Emre/McpTestGenerator/releases
   - Click "Create a new release"
   - Click "Choose a tag" → type `v1.0.1` → "Create new tag on publish"
   - Release title: `v1.0.1`
   - Use the template from `.github/RELEASE_TEMPLATE.md`
   - Click "Publish release"

5. **Wait for workflow**
   - Go to: Actions → "Publish to PyPI"
   - Watch the workflow run
   - If successful, package is now on PyPI!

6. **Verify**
   ```bash
   pip install --upgrade qa-mcp
   qa-mcp --help
   ```

### Option 2: Manual Release

```bash
# 1. Clean previous builds
rm -rf dist/ build/ *.egg-info

# 2. Build
python -m build

# 3. Check
twine check dist/*

# 4. Upload to PyPI
twine upload dist/*
# Enter __token__ as username
# Paste your PYPI_API_TOKEN as password

# 5. Verify
pip install --upgrade qa-mcp
qa-mcp --help
```

## 📝 Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x.x): Breaking changes
- **MINOR** (x.1.x): New features, backward-compatible
- **PATCH** (x.x.1): Bug fixes, backward-compatible

Examples:
- `1.0.0` → `1.0.1` - Bug fix
- `1.0.1` → `1.1.0` - New feature
- `1.1.0` → `2.0.0` - Breaking change

## 🔍 Verification Checklist

After publishing, verify:

- [ ] Package appears on PyPI: https://pypi.org/project/qa-mcp/
- [ ] README renders correctly on PyPI
- [ ] Installation works: `pip install qa-mcp`
- [ ] Command works: `qa-mcp --help`
- [ ] Docker image updated: `docker pull atakanemree/qa-mcp:latest`
- [ ] Badges work on README

## ⚠️ Troubleshooting

### "File already exists"

PyPI doesn't allow re-uploading the same version. Solutions:
1. Increment version number
2. Use `--skip-existing` flag (for re-uploading other files in same release)

### "Invalid distribution"

Check:
- `pyproject.toml` syntax is valid
- All required fields are present
- Version format is correct

### "Authentication failed"

- Verify token is correct
- Use `__token__` as username (not your PyPI username)
- Check token hasn't expired
- Verify token has correct permissions

## 📚 Resources

- PyPI: https://pypi.org/project/qa-mcp/
- Test PyPI: https://test.pypi.org/project/qa-mcp/
- Python Packaging Guide: https://packaging.python.org/
- Twine Documentation: https://twine.readthedocs.io/

## 🎯 Quick Reference

```bash
# Development build and test
python -m build
twine check dist/*

# Test PyPI
twine upload --repository testpypi dist/*

# Production PyPI
twine upload dist/*

# Install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ qa-mcp

# Install from PyPI
pip install qa-mcp
```
