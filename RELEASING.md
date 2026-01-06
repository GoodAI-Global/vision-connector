# Releasing

This document describes the release process for vision-connector.

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

## Release Checklist

### Before Release

1. **Ensure all tests pass**
   ```bash
   make test
   ```

2. **Run linters**
   ```bash
   make lint
   ```

3. **Update CHANGELOG.md**
   - Move items from "Unreleased" to new version section
   - Add release date
   - Summarize key changes

4. **Update version number**
   - Edit `pyproject.toml`: `version = "X.Y.Z"`
   - Edit `src/vision_connector/__init__.py`: `__version__ = "X.Y.Z"`

5. **Commit version bump**
   ```bash
   git add -A
   git commit -m "Release vX.Y.Z"
   ```

### Creating the Release

1. **Create and push tag**
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

2. **Create GitHub Release**
   - Go to GitHub Releases
   - Click "Create a new release"
   - Select the tag
   - Copy relevant CHANGELOG section to release notes
   - Publish release

3. **Build and upload to PyPI** (if applicable)
   ```bash
   make build
   twine upload dist/*
   ```

### After Release

1. **Verify installation**
   ```bash
   pip install vision-connector==X.Y.Z
   ```

2. **Announce release** (if applicable)
   - Update documentation
   - Post to relevant channels

## Emergency Hotfix Process

For critical bugs in production:

1. Create hotfix branch from release tag
   ```bash
   git checkout -b hotfix/X.Y.Z+1 vX.Y.Z
   ```

2. Apply minimal fix

3. Follow normal release process with patch version bump

## Version History

See [CHANGELOG.md](CHANGELOG.md) for full version history.
