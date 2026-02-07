#!/usr/bin/env python3
"""
Version bumping script for dna-core package.

Usage:
    python scripts/bump_version.py patch   # 0.1.0 -> 0.1.1
    python scripts/bump_version.py minor   # 0.1.0 -> 0.2.0
    python scripts/bump_version.py major   # 0.1.0 -> 1.0.0
    python scripts/bump_version.py 0.2.5   # Set specific version
"""

import re
import sys
from pathlib import Path


def get_current_version(pyproject_path: Path) -> str:
    """Extract current version from pyproject.toml."""
    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse semantic version string into (major, minor, patch)."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    return tuple(map(int, parts))


def bump_version(current: str, bump_type: str) -> str:
    """Bump version based on type (major, minor, patch) or set specific version."""
    if re.match(r"^\d+\.\d+\.\d+$", bump_type):
        return bump_type

    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(
            f"Invalid bump type: {bump_type}. Use 'major', 'minor', 'patch', or a specific version like '1.2.3'"
        )


def update_pyproject_version(pyproject_path: Path, new_version: str) -> None:
    """Update version in pyproject.toml."""
    content = pyproject_path.read_text(encoding="utf-8")
    new_content = re.sub(
        r'^version = "[^"]+"',
        f'version = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    pyproject_path.write_text(new_content, encoding="utf-8")
    print(f"✓ Updated pyproject.toml: version = \"{new_version}\"")


def update_init_version(init_path: Path, new_version: str) -> None:
    """Update __version__ in __init__.py."""
    if not init_path.exists():
        print(f"⚠ {init_path} not found, skipping")
        return

    content = init_path.read_text(encoding="utf-8")
    new_content = re.sub(
        r'^__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    init_path.write_text(new_content, encoding="utf-8")
    print(f"✓ Updated {init_path.name}: __version__ = \"{new_version}\"")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py [major|minor|patch|X.Y.Z]")
        print("\nExamples:")
        print("  python scripts/bump_version.py patch   # 0.1.0 -> 0.1.1")
        print("  python scripts/bump_version.py minor   # 0.1.0 -> 0.2.0")
        print("  python scripts/bump_version.py major   # 0.1.0 -> 1.0.0")
        print("  python scripts/bump_version.py 0.2.5   # Set to 0.2.5")
        sys.exit(1)

    bump_type = sys.argv[1]

    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    pyproject_path = project_root / "pyproject.toml"
    init_path = project_root / "dna_core" / "__init__.py"

    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")
        sys.exit(1)

    # Get current version
    current_version = get_current_version(pyproject_path)
    print(f"Current version: {current_version}")

    # Calculate new version
    try:
        new_version = bump_version(current_version, bump_type)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"New version: {new_version}")

    # Confirm with user
    response = input("\nProceed with version bump? [y/N]: ")
    if response.lower() != "y":
        print("Aborted.")
        sys.exit(0)

    # Update files
    update_pyproject_version(pyproject_path, new_version)
    update_init_version(init_path, new_version)

    print("\n✓ Version bump complete!")
    print("\nNext steps:")
    print("  1. Review changes: git diff")
    print("  2. Commit changes: git add -u && git commit -m 'Bump version to {}'".format(new_version))
    print("  3. Create tag: git tag v{}".format(new_version))
    print("  4. Push changes: git push && git push --tags")
    print("\nThe GitHub Action will automatically build and publish the package.")


if __name__ == "__main__":
    main()
