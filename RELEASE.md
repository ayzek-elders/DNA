# Release Process

This document describes how to release a new version of `dna-core`.

## Overview

The project uses GitHub Actions for automated building, testing, and publishing. When you push a version tag (e.g., `v0.1.0`), the package is automatically:
1. Built using `uv`
2. Published to GitHub Packages
3. Released on GitHub with distribution files attached

## Quick Release

For a quick release, use the version bump script:

```bash
# Bump patch version (0.1.0 -> 0.1.1)
python scripts/bump_version.py patch

# Bump minor version (0.1.0 -> 0.2.0)
python scripts/bump_version.py minor

# Bump major version (0.1.0 -> 1.0.0)
python scripts/bump_version.py major

# Set specific version
python scripts/bump_version.py 0.2.5
```

The script will:
- Update `pyproject.toml`
- Update `dna_core/__init__.py`
- Prompt for confirmation
- Show next steps

## Manual Release Process

### 1. Update Version

Edit the version in **two places**:

**pyproject.toml:**
```toml
[project]
name = "dna-core"
version = "0.2.0"  # Update this
```

**dna_core/__init__.py:**
```python
__version__ = "0.2.0"  # Update this
```

### 2. Update Documentation (Optional)

Update `README.md` or `CHANGELOG.md` if needed:

```markdown
## [0.2.0] - 2025-02-07

### Added
- New feature X
- New node type Y

### Changed
- Improved performance of Z

### Fixed
- Bug in component A
```

### 3. Commit Changes

```bash
git add pyproject.toml dna_core/__init__.py
git commit -m "Bump version to 0.2.0"
```

### 4. Create and Push Tag

```bash
# Create annotated tag
git tag -a v0.2.0 -m "Release version 0.2.0"

# Push commits and tags
git push origin main
git push origin v0.2.0
```

**Important:** The tag must start with `v` (e.g., `v0.2.0`) to trigger the release workflow.

### 5. Monitor GitHub Actions

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Watch the "Build and Publish Package" workflow
4. It will:
   - ✓ Verify version matches between tag and pyproject.toml
   - ✓ Run linter (optional, non-blocking)
   - ✓ Run tests (optional, non-blocking)
   - ✓ Build the package
   - ✓ Publish to GitHub Packages
   - ✓ Create GitHub Release

### 6. Verify Release

Once the workflow completes:

1. **Check GitHub Release:**
   - Go to `https://github.com/YOUR_USERNAME/YOUR_REPO/releases`
   - Verify the new release is created
   - Download files should include `.whl` and `.tar.gz`

2. **Test Installation:**
   ```bash
   # From GitHub Packages
   pip install dna-core==0.2.0 --index-url https://...

   # From GitHub Release (download .whl file first)
   pip install dna_core-0.2.0-py3-none-any.whl

   # From git
   pip install git+https://github.com/YOUR_USERNAME/YOUR_REPO@v0.2.0
   ```

3. **Verify imports:**
   ```python
   import dna_core
   print(dna_core.__version__)  # Should show 0.2.0
   from dna_core import ObserverGraph, HTTPGetRequestNode
   ```

## GitHub Actions Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Actions:**
- Lints code with `ruff`
- Runs tests (if available)
- Builds package
- Verifies imports
- Uploads build artifacts

**Purpose:** Ensure code quality before merging/releasing

### 2. Publish Workflow (`.github/workflows/publish.yml`)

**Triggers:**
- Push of version tags (`v*.*.*`)
- Manual workflow dispatch

**Actions:**
1. **Validation:**
   - Verifies tag version matches `pyproject.toml`
   - Ensures consistent versioning

2. **Building:**
   - Installs dependencies with `uv`
   - Runs linter (non-blocking)
   - Runs tests (non-blocking)
   - Builds wheel and source distribution

3. **Publishing:**
   - Publishes to GitHub Packages
   - Creates GitHub Release
   - Attaches distribution files to release

4. **Summary:**
   - Generates workflow summary
   - Lists distribution files

## Configuring GitHub Secrets

For publishing to GitHub Packages, the workflow uses the built-in `GITHUB_TOKEN` which is automatically provided. No additional configuration needed!

If you want to publish to other package indexes:

### PyPI (Public)

1. Go to Repository Settings → Secrets and variables → Actions
2. Add `PYPI_TOKEN`:
   - Get token from https://pypi.org/manage/account/token/
   - Add as repository secret

3. Update `.github/workflows/publish.yml`:
   ```yaml
   - name: Publish to PyPI
     run: |
       uv publish \
         --token ${{ secrets.PYPI_TOKEN }} \
         --username __token__
   ```

### Private PyPI Server

1. Add secrets:
   - `PRIVATE_PYPI_URL` - Your private PyPI server URL
   - `PRIVATE_PYPI_TOKEN` - Authentication token

2. Update workflow:
   ```yaml
   - name: Publish to Private PyPI
     run: |
       uv publish \
         --publish-url ${{ secrets.PRIVATE_PYPI_URL }} \
         --token ${{ secrets.PRIVATE_PYPI_TOKEN }} \
         --username __token__
   ```

## Installation Instructions for Users

### From GitHub Packages

Users can install your package from GitHub Packages using:

```bash
pip install dna-core --index-url https://pypi.org/simple --extra-index-url https://YOUR_USERNAME:${GITHUB_TOKEN}@github.com/YOUR_USERNAME/YOUR_REPO
```

### From GitHub Releases

1. Go to Releases page
2. Download the `.whl` file
3. Install:
   ```bash
   pip install dna_core-0.2.0-py3-none-any.whl
   ```

### From Git Repository

```bash
# Latest from main branch
pip install git+https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Specific version tag
pip install git+https://github.com/YOUR_USERNAME/YOUR_REPO.git@v0.2.0

# Specific branch
pip install git+https://github.com/YOUR_USERNAME/YOUR_REPO.git@develop
```

## Troubleshooting

### Version Mismatch Error

**Error:** `Version mismatch! pyproject.toml has X.Y.Z but tag is vA.B.C`

**Solution:** Make sure the version in `pyproject.toml` and your git tag match exactly.

### Publishing Failed

**Error:** Publishing to GitHub Packages failed

**Solutions:**
- Ensure repository has Packages enabled
- Check that `GITHUB_TOKEN` has `packages: write` permission
- For private repos, verify package registry settings

### Build Failed

**Error:** Build fails during workflow

**Solutions:**
- Check that `uv.lock` is up to date: `uv lock`
- Verify all dependencies are available
- Review build logs in GitHub Actions

### Tag Already Exists

**Error:** `tag 'v0.1.0' already exists`

**Solution:**
```bash
# Delete local tag
git tag -d v0.1.0

# Delete remote tag
git push --delete origin v0.1.0

# Create new tag
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

## Best Practices

1. **Always test locally before releasing:**
   ```bash
   uv build
   pip install dist/*.whl
   python -c "import dna_core; print(dna_core.__version__)"
   ```

2. **Use semantic versioning:**
   - `MAJOR.MINOR.PATCH`
   - MAJOR: Breaking changes
   - MINOR: New features (backwards compatible)
   - PATCH: Bug fixes

3. **Keep CHANGELOG.md updated** with notable changes

4. **Test in a fresh environment** before tagging

5. **Review the GitHub Actions summary** after each release

6. **Tag releases with annotated tags:**
   ```bash
   git tag -a v0.2.0 -m "Release 0.2.0"
   ```
   Not lightweight tags: ~~`git tag v0.2.0`~~

## Version Numbering Guidelines

- **0.1.0** - Initial development release
- **0.2.0** - Added new features
- **0.x.y** - Pre-1.0 development (API may change)
- **1.0.0** - First stable release
- **1.1.0** - New features (backwards compatible)
- **1.0.1** - Bug fixes only
- **2.0.0** - Breaking changes

## Emergency Rollback

If you need to rollback a release:

1. **Delete the problematic release** on GitHub
2. **Delete the tag:**
   ```bash
   git tag -d v0.2.0
   git push --delete origin v0.2.0
   ```
3. **Fix the issue** in code
4. **Create a new patch release** (e.g., v0.2.1)

## Support

For issues with the release process:
- Check GitHub Actions logs
- Review this document
- Contact the development team
