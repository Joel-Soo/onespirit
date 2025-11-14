# Setup Script Guide

## Overview

A setup.sh script for setting up the development environment for the OneSpirit project.

## Prerequisites

Before using the setup script, ensure you have:

1. **Docker and Docker Compose** installed on your system
2. **Environment file** - Copy `.env.example` to `.env` and configure your settings:
   ```bash
   cp .env.example .env
   # Edit .env with your preferred values
   ```
3. **Git** installed (for version control)

**Note**: The `.env` file is required as all services now use `env_file` directive in docker-compose.yaml for consistent configuration management.

## Recent Improvements

This setup script has been enhanced with several best practices:

- **Enhanced Error Handling**: Uses `set -euo pipefail` to catch errors early and prevent silent failures
- **Environment Variable Consistency**: All services load configuration from `.env` file via `env_file` directive
- **Reproducible Builds**: Docker images use `uv.lock` for deterministic dependency installation
- **Optimized Logging**: Python containers configured with `PYTHONUNBUFFERED=1` for real-time log output
- **Smaller Images**: Python containers configured with `PYTHONDONTWRITEBYTECODE=1` to prevent .pyc files

## Usage:

```bash
# Initial setup
./setup.sh init

# Create admin user
./setup.sh createsuperuser

# Start services
./setup.sh up

# View logs
./setup.sh logs

# Access database
./setup.sh psql

# Start pgAdmin
./setup.sh pgadmin
```

## Available Commands

- `init` - Builds Docker images and initializes the database
- `up` - Starts all services in the background
- `down` - Stops all services
- `shell` - Opens a Django shell in the web container
- `bash` - Opens a bash shell in the web container
- `test` - Runs the pytest test suite inside the web container
- `psql` - Connects to the PostgreSQL database
- `logs` - Follows the logs for the web service
- `migrate` - Runs database migrations
- `makemigrations` - Creates new migrations based on model changes
- `createsuperuser` - Creates a Django superuser (interactive)
- `pgadmin` - Starts pgAdmin for database management
- `manage` - Runs any Django management command (e.g., `./setup.sh manage collectstatic`)

## Environment Configuration

The setup uses a centralized `.env` file for all configuration. Key variables include:

- **Database Configuration**: `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- **Django Settings**: `SECRET_KEY`, `DJANGO_PORT`
- **pgAdmin Settings**: `PGADMIN_EMAIL`, `PGADMIN_PASSWORD`, `PGADMIN_PORT`

**Docker-specific overrides**:
- `DB_HOST` is automatically set to `postgres` in docker-compose.yaml (Docker network hostname)
- The `DB_HOST=localhost` value in `.env` is for local development outside Docker

## Troubleshooting

### Script fails with "unbound variable" error
- **Cause**: Enhanced error handling now catches undefined variables
- **Solution**: Ensure all required environment variables are set in `.env`

### "Database is not ready" during init
- **Cause**: PostgreSQL healthcheck waiting for database to be ready
- **Solution**: This is normal. The script waits until the database is healthy before proceeding

### Logs not appearing in real-time
- **Cause**: Python output buffering
- **Solution**: Already fixed with `PYTHONUNBUFFERED=1` in Dockerfiles. Rebuild images with `docker compose build`

### Build fails with "lock file out of sync"
- **Cause**: `uv.lock` doesn't match `pyproject.toml`
- **Solution**: Run `uv lock` locally to update the lock file, then commit changes

### Services can't find environment variables
- **Cause**: Missing `.env` file
- **Solution**: Copy `.env.example` to `.env`: `cp .env.example .env`

### Permission errors with volumes
- **Cause**: Docker volume permissions (especially on Linux)
- **Solution**: Check file ownership, may need to adjust permissions or use Docker's user mapping

## Additional Resources

For detailed information about the implementation:
- Shell best practices: `docs/shell-best-practices-implementation.md`
- Environment variables: `docs/env-variable-consistency-implementation.md`
- Reproducible builds: `docs/uv-lock-and-python-env-implementation.md`

