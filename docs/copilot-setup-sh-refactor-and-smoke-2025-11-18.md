# Copilot: setup.sh Refactor Summary and Smoke Check (2025-11-18)

## Refactor Summary

### What I changed
- Robustness: Validates tools and location (ensures run at repo root), safe `.env` reads, clearer errors.
- Health waits: Adds a timeouted health-check wait for `postgres` using Docker health status.
- Exec/run helpers: Executes in the running `web` container when available, otherwise uses ephemeral runs.
- Dependency sync: In `init`, runs `uv sync --frozen` (if present) before migrations.
- Dev ergonomics: Adds new commands for status, logs-all, `check`, `lint` (ruff), `typecheck` (basedpyright), and `makemigrations --check --dry-run`.
- Env-aware psql: Uses `DB_USER`/`DB_NAME` from `.env` (with defaults) for `psql`.
- pgAdmin: Starts via profile and displays email/password from `.env`.

### New commands
- Core:
  - `init`: build → start `postgres` → wait → `uv sync` → migrate
  - `up` / `down` / `status`
  - `logs` (use `./setup.sh logs --all` to include `postgres`)
- App:
  - `shell`, `bash`, `manage <args>`
  - `migrate [args]`, `makemigrations`, `makemigrations-check`
  - `createsuperuser`, `test [args]`, `check`, `lint`, `typecheck`
- DB/Tools:
  - `psql`, `pgadmin`

File updated: `setup.sh` (syntax checked: OK)

Quick try-it examples:

```bash
./setup.sh init
./setup.sh up
./setup.sh status
./setup.sh manage showmigrations
./setup.sh makemigrations-check
./setup.sh test -q
./setup.sh logs --all
```

## Quick Smoke Definition

A “quick smoke” is a fast sanity check that the basics work. It’s not exhaustive—just enough to catch obvious breakages before deeper testing.

- Definition: Minimal checks to ensure core services start and critical commands succeed.
- Goal: Quick confidence, not full validation; fail fast if something’s clearly wrong.

For this project, a practical smoke could be:

```bash
# 1) Start Postgres and wait for health (fast feedback)
docker compose up -d postgres
./setup.sh status

# 2) Basic Django checks
./setup.sh check
./setup.sh makemigrations-check

# 3) Lightweight tests (short, quiet)
./setup.sh test -q

# 4) Optionally start web and hit /health (adds a bit more time)
./setup.sh up
curl -sf http://localhost:8000/health
```
