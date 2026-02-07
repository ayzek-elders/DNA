# GitHub Actions Workflows

This directory contains automated workflows for the dna-core package.

## Workflows

### 1. CI Workflow (`ci.yml`)

**Purpose:** Continuous Integration - runs on every push and pull request

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`

**Jobs:**
1. **Lint and Test**
   - Runs `ruff` for linting and formatting checks
   - Executes test suite (if available)
   - Verifies package imports
   - Uploads coverage reports

2. **Build**
   - Builds the package
   - Verifies package contents
   - Ensures `main.py` is excluded
   - Uploads build artifacts

**Status:** Non-blocking - failures are warnings, not errors

### 2. Publish Workflow (`publish.yml`)

**Purpose:** Automated package publishing to GitHub Packages and GitHub Releases

**Triggers:**
- Tags matching `v*.*.*` (e.g., `v0.1.0`, `v1.2.3`)
- Manual workflow dispatch from GitHub UI

**Jobs:**
1. **Version Validation**
   - Extracts version from git tag
   - Verifies it matches `pyproject.toml`
   - Fails if versions don't match

2. **Build and Test**
   - Installs dependencies via `uv`
   - Runs linter (optional)
   - Runs tests (optional)
   - Builds wheel and source distributions

3. **Publish**
   - Publishes to GitHub Packages
   - Creates GitHub Release
   - Attaches `.whl` and `.tar.gz` files
   - Generates release notes with installation instructions

**Required Permissions:**
- `contents: write` - for creating releases
- `packages: write` - for publishing packages

## Quick Start

### Release a New Version

1. **Bump version:**
   ```bash
   python scripts/bump_version.py patch  # or minor, major
   ```

2. **Commit and tag:**
   ```bash
   git add pyproject.toml dna_core/__init__.py
   git commit -m "Bump version to 0.2.0"
   git tag -a v0.2.0 -m "Release 0.2.0"
   ```

3. **Push:**
   ```bash
   git push origin main
   git push origin v0.2.0
   ```

4. **Monitor:** Go to Actions tab on GitHub to watch the workflow

### Manual Workflow Trigger

You can also manually trigger the publish workflow:

1. Go to **Actions** tab on GitHub
2. Select **"Build and Publish Package"** workflow
3. Click **"Run workflow"**
4. Enter the version tag (e.g., `v0.2.0`)
5. Click **"Run workflow"**

## Configuration

### GitHub Secrets

The workflows use the built-in `GITHUB_TOKEN` which is automatically provided by GitHub. No additional configuration needed!

For custom package repositories, add these secrets in **Settings → Secrets and variables → Actions**:

- `PYPI_TOKEN` - For publishing to PyPI
- `PRIVATE_PYPI_URL` - For private PyPI servers
- `PRIVATE_PYPI_TOKEN` - Authentication for private PyPI

### Workflow Permissions

Ensure repository settings allow GitHub Actions to create releases:

1. Go to **Settings → Actions → General**
2. Under **Workflow permissions**, select:
   - ✓ Read and write permissions
   - ✓ Allow GitHub Actions to create and approve pull requests

## Customization

### Skip Tests or Linting

Both linting and testing steps are configured as `continue-on-error: true`, meaning they won't block releases even if they fail.

To make them required:

```yaml
- name: Run tests
  continue-on-error: false  # Change this
  run: pytest tests/
```

### Add Pre-release Checks

Add additional validation steps in `publish.yml`:

```yaml
- name: Check dependencies
  run: uv pip check

- name: Security scan
  run: uv run bandit -r dna_core/
```

### Publish to Multiple Registries

Publish to both GitHub Packages and PyPI:

```yaml
- name: Publish to PyPI
  run: uv publish --token ${{ secrets.PYPI_TOKEN }}

- name: Publish to GitHub Packages
  run: uv publish --publish-url https://... --token ${{ secrets.GITHUB_TOKEN }}
```

## Troubleshooting

### Workflow Not Triggering

**Problem:** Pushed a tag but workflow didn't run

**Solutions:**
- Ensure tag matches pattern `v*.*.*` (must start with `v`)
- Check Actions are enabled: Settings → Actions → General
- Verify workflow file syntax: Use GitHub's workflow validator

### Permission Denied

**Problem:** Workflow fails with "permission denied" error

**Solutions:**
- Check workflow permissions: Settings → Actions → General
- Ensure `permissions:` block is set in workflow file
- Verify repository has Packages feature enabled

### Version Mismatch

**Problem:** "Version mismatch" error during workflow

**Solutions:**
- Ensure `pyproject.toml` version matches your git tag
- Use `scripts/bump_version.py` to keep versions in sync
- Double-check both `pyproject.toml` and `dna_core/__init__.py`

### Build Artifacts Not Uploading

**Problem:** Distribution files not attached to release

**Solutions:**
- Check `dist/` directory exists after build
- Verify file patterns in `files:` section
- Review workflow logs for upload errors

## Best Practices

1. **Always test locally before pushing tags:**
   ```bash
   uv build
   pip install dist/*.whl
   python -c "import dna_core; print(dna_core.__version__)"
   ```

2. **Use annotated tags** (not lightweight):
   ```bash
   git tag -a v0.2.0 -m "Release 0.2.0"  # ✓ Good
   git tag v0.2.0                         # ✗ Avoid
   ```

3. **Update CHANGELOG.md** before releasing

4. **Keep version numbers consistent** across:
   - Git tag (`v0.2.0`)
   - `pyproject.toml` (`version = "0.2.0"`)
   - `dna_core/__init__.py` (`__version__ = "0.2.0"`)

5. **Monitor workflow runs** after pushing tags

6. **Test installation** from GitHub Packages after release

## More Information

- [Release Process Documentation](../../RELEASE.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Semantic Versioning](https://semver.org/)
