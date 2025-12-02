# Copilot: Dockerfile Troubleshooting (2025-11-19)

## Error: ModuleNotFoundError: No module named 'django'

The error means Django isn't installed in the container, even though `uv sync --frozen` should have installed it.

### Check What's Installed

```bash
````markdown
# Copilot: Dockerfile Troubleshooting (2025-11-19)

## Error: ModuleNotFoundError: No module named 'django'

The error means Django isn't installed in the container, even though `uv sync --frozen` should have installed it.

### Check What's Installed

```bash
# Enter the running container
docker exec -it onespirit_web /bin/bash

# Check if Django is installed
python -c "import django; print(django.__version__)"

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Check uv.lock has Django
grep -i "name = \"django\"" uv.lock

# Check if uv sync actually ran in the image
docker logs onespirit_web | head -100
```

### Most Likely Cause

The `uv sync --frozen` step in the Dockerfile ran **before** the dependencies were copied, or `uv.lock` is missing/corrupted.

### Verify Dockerfile Order

```bash
head -25 Dockerfile
```

The correct order should be:
1. `COPY pyproject.toml uv.lock ./`
2. `RUN uv sync --frozen`
3. `COPY . .`

If dependencies are copied **after** the sync, they won't be installed.

### Debugging Steps

1. Check `docker logs onespirit_web` output — look for errors during `uv sync`.
2. Verify `uv.lock` exists in the repo root:
   ```bash
   ls -lah uv.lock
   ```
3. Verify Dockerfile COPY order and that `uv sync --frozen` runs before app code is copied.
4. Rebuild the image with verbose output:
   ```bash
   docker compose build --no-cache --progress=plain web
   ```
5. If still failing, check if `uv` is properly installed in the image:
   ```bash
   docker exec -it onespirit_web which uv
   docker exec -it onespirit_web uv --version
   ```

### Quick Fix (If uv.lock is Missing)

Generate a fresh lock file locally:

```bash
uv lock --upgrade
git add uv.lock
```

Then rebuild:

```bash
docker compose build --no-cache web
```

````

## Keep Web Container Running (Dev)

- Root cause: The dev `web` service runs `bash` as PID 1 (see `docker-compose.yaml` → `web` → `command: bash`). When that process ends (e.g., you exit the shell), the container stops.

- Best practice (dev): Run a long-lived service as PID 1 and exec into it as needed.
  - Change `command` to the Django server so it stays alive:
    - In `docker-compose.yaml`, replace `command: bash` with `command: python manage.py runserver 0.0.0.0:8000`.
  - Start detached, then get a shell when needed:
    ```zsh
    docker compose up -d web
    docker compose exec web bash
    docker compose logs -f web
    ```
    Exiting the shell won’t stop the container because `runserver` remains PID 1.

- Simple keep-alive (if you don’t want Django yet):
  - Use a do-nothing long runner instead of `bash`:
    - `command: ["bash","-lc","sleep infinity"]`
    - or `command: ["tail","-f","/dev/null"]`
  - This keeps the container up; you can still `docker compose exec web bash` to work inside it.

- Interactive flags (optional): If you insist on `bash` as the main process, adding these improves UX but doesn’t change the exit behavior when that `bash` ends:
  - In `web`: `stdin_open: true` and `tty: true`.

- Production note: In prod (`docker-compose.prod.yaml` + `Dockerfile.prod`) the image `CMD` runs `gunicorn ...`, which is a proper long-lived process, so the container remains running.

## .dockerignore Not Being Respected Investigation

### Issue Found: Volume Mount Overriding .dockerignore

The `.dockerignore` file **is being respected during the Docker image build**, but the issue is that the **volume mount in `docker-compose.yaml` is overriding the built image contents at runtime**.

In `docker-compose.yaml`, line 39:
```yaml
volumes:
  - .:/app
```

This bind mount maps the **entire current directory** (including all files that `.dockerignore` was supposed to exclude) directly into the container at `/app`, completely overriding whatever was built into the image.

### The Problem:

1. **.dockerignore works during build** - It excludes files from being copied into the image layers
2. **Volume mount happens at runtime** - The bind mount `.:/app` mounts the host directory directly, bypassing the image layers entirely
3. **Result**: All the files you wanted to exclude (`.venv`, `__pycache__`, `.git`, etc.) are visible in the running container because they're being mounted from the host

### Why This Setup Exists:

This is actually **intentional for development**:
- The volume mount enables **hot-reloading** - code changes on the host are immediately reflected in the container
- It allows developers to edit files locally and see changes without rebuilding the image
- The devcontainer uses this pattern to provide a seamless development experience

### Solutions:

**Option 1: Accept it (Recommended for Dev)**
This is normal for development environments. The `.dockerignore` still helps by:
- Reducing build time and image size
- Keeping the base image clean
- Working correctly in production where you wouldn't use volume mounts

**Option 2: Use more selective volume mounts**
Instead of mounting everything, mount only what you need:
```yaml
volumes:
  - ./accounts:/app/accounts
  - ./clubs:/app/clubs
  - ./people:/app/people
  # ... mount only source directories
```

**Option 3: Use .dockerignore-aware sync tools**
Use tools like `docker-sync` or configure VS Code remote to sync only certain files.

**Option 4: Don't use volume mounts in dev**
Remove the volume mount, but you'll need to rebuild the image for every code change (not practical for development).

### Verification:

The devcontainer.json confirms this is intentional - it references the docker-compose.yaml service "web" which has the volume mount, specifically to support the development workflow.

**Bottom line**: The `.dockerignore` **is** being respected during the build phase. The "issue" you're seeing is the expected behavior of the development volume mount overriding the built image contents at runtime. This is standard practice for Docker-based development environments.

````

---

> why didn't pgadmin service start

The pgadmin service didn't start because it has `profiles: - tools` on lines 64-65. In Docker Compose, services with profiles only start when you explicitly enable that profile.

To start pgadmin, you need to use:

```bash
docker compose --profile tools up -d pgadmin
```

Or to start all services including those in the tools profile:

```bash
docker compose --profile tools up -d
```

The profile system is designed to keep optional services (like pgadmin) from running by default, so they don't consume resources unless you specifically need them.