# uv.lock and Python Environment Variables Implementation

**Date**: 2025-11-14
**Related**: rovo-recommendations-assessment.md (Items 4 & 5, Lines 26-32, 59-60)

## Changes Made

### 1. Dockerfile - Development Environment

#### Added Python Environment Variables (lines 4-6):
```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
```

#### Updated Dependency Installation (lines 17-21):
- **Before**: `COPY pyproject.toml .` + `RUN uv pip install --system .`
- **After**: `COPY pyproject.toml uv.lock ./` + `RUN uv sync --frozen`

### 2. Dockerfile.prod - Production Environment

#### Added Python Environment Variables in Both Stages:
- **Builder stage** (lines 4-6)
- **Production stage** (lines 29-31)

#### Updated Dependency Installation (lines 20-24):
- **Before**: `COPY pyproject.toml .` + `RUN uv pip install --system .`
- **After**: `COPY pyproject.toml uv.lock ./` + `RUN uv sync --frozen`

## Benefits

### Python Environment Variables

**PYTHONDONTWRITEBYTECODE=1**:
- Prevents Python from writing `.pyc` files to disk
- Reduces image size by avoiding bytecode cache
- Improves container startup time by skipping bytecode compilation
- Simplifies debugging (source code changes reflected immediately)

**PYTHONUNBUFFERED=1**:
- Forces Python output to be unbuffered
- Ensures logs appear in real-time in Docker logs
- Critical for debugging and monitoring containerized applications
- Prevents log loss if container crashes

### uv.lock for Reproducible Builds

**Using `uv sync --frozen`**:
- **Reproducibility**: Ensures exact same dependency versions across all environments
- **Consistency**: Dev, staging, and production use identical dependencies
- **Security**: Lock file prevents supply chain attacks via dependency substitution
- **CI/CD**: Builds are deterministic and cacheable
- **Fail-Fast**: `--frozen` flag errors if lock file is out of sync with pyproject.toml

**Before vs After**:
- **Before**: `uv pip install --system .` - Resolves dependencies at build time (non-deterministic)
- **After**: `uv sync --frozen` - Uses exact versions from uv.lock (deterministic)

## How It Works

1. **Local Development**:
   - Developer updates dependencies: `uv add package-name`
   - uv automatically updates both pyproject.toml and uv.lock
   - Commit both files to git

2. **Docker Build**:
   - Dockerfile copies both pyproject.toml and uv.lock
   - `uv sync --frozen` reads uv.lock and installs exact versions
   - If lock file is out of sync, build fails (prevents drift)

3. **Dependency Updates**:
   - Run `uv lock` to update lock file with latest compatible versions
   - Review changes in uv.lock before committing
   - All environments get updated dependencies on next build

## Migration Notes

- The uv.lock file was already in the repository but not being used
- No changes required to existing workflows
- Docker builds will now use locked dependencies automatically
- To update dependencies: `uv lock` or `uv add/remove package-name`

## Testing

To verify the changes work correctly:

```bash
# Rebuild the development image
docker compose build web

# Verify the build uses uv.lock
docker compose build web 2>&1 | grep "uv sync"

# Start the services
./setup.sh up

# Check that logs appear in real-time (PYTHONUNBUFFERED=1)
./setup.sh logs

# Verify no .pyc files are created (PYTHONDONTWRITEBYTECODE=1)
docker compose exec web find /app -name "*.pyc"
```

## Troubleshooting

**Build fails with "lock file out of sync"**:
- Run `uv lock` locally to update the lock file
- Commit the updated uv.lock file

**Dependencies not updating**:
- Ensure both pyproject.toml and uv.lock are copied to the image
- Check that you're using `uv sync --frozen` not `uv pip install`

**Logs not appearing in real-time**:
- Verify PYTHONUNBUFFERED=1 is set in the Dockerfile
- Check that you're viewing logs with `docker compose logs -f`
