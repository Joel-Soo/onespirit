#!/bin/bash

# setup.sh - Development environment helper for OneSpirit
# - Validates environment and docker tools
# - Starts services and waits for healthchecks
# - Runs Django and tooling commands inside the web container

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
TIMEOUT_DEFAULT=120

# --- Utility Helpers ---

die() { echo "[ERROR] $*" >&2; exit 1; }
info() { echo "[INFO]  $*"; }
warn() { echo "[WARN]  $*"; }

require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

# Ensure we're at repo root
[ -f "docker-compose.yaml" ] || die "Run $SCRIPT_NAME from the repository root (docker-compose.yaml not found)."

# Ensure required tools
require_cmd docker
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required (docker compose)."

compose() { docker compose "$@"; }

# Read a key from .env (without sourcing) with optional default
env_get() {
    local key="$1"; shift || true
    local def="${1:-}"
    local val
    if [ -f .env ]; then
        # shellcheck disable=SC2002
        val=$(cat .env | grep -E "^${key}=" | tail -n1 | cut -d'=' -f2- || true)
        # Trim surrounding quotes if any
        val="${val%\"}"; val="${val#\"}"; val="${val%\'}"; val="${val#\'}"
    fi
    if [ -n "${val:-}" ]; then echo "$val"; else echo "$def"; fi
}

require_envs() {
    local missing=()
    for k in "$@"; do
        local v
        v=$(env_get "$k") || true
        if [ -z "$v" ]; then missing+=("$k"); fi
    done
    if [ ${#missing[@]} -gt 0 ]; then
        warn "Missing variables in .env: ${missing[*]} (defaults may apply via compose)."
    fi
}

# Wait for a service's container health to be 'healthy' with timeout
wait_for_health() {
    local service="$1"; local timeout="${2:-$TIMEOUT_DEFAULT}"; local waited=0
    local cid
    cid=$(compose ps -q "$service")
    [ -n "$cid" ] || die "Service '$service' has no container ID. Is it started?"
    info "Waiting for $service health (timeout ${timeout}s)..."
    while true; do
        local status
        status=$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "unknown")
        if [ "$status" = "healthy" ]; then echo; info "$service is healthy."; break; fi
        sleep 2; waited=$((waited+2))
        echo -n "."
        if [ $waited -ge $timeout ]; then echo; die "Timeout waiting for $service to be healthy (last status: $status)."; fi
    done
}

# Determine if a service container is running
is_running() {
    local service="$1"; local cid
    cid=$(compose ps -q "$service")
    [ -n "$cid" ] || return 1
    docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null | grep -q true
}

# Execute inside running web container, else run ephemeral
web_exec_or_run() {
    local cmd="$*"
    if is_running web; then
        compose exec web bash -lc "$cmd"
    else
        compose run --rm web bash -lc "$cmd"
    fi
}

show_help() {
    cat <<EOF
Usage: ./$SCRIPT_NAME <command> [args]

Manage the OneSpirit Django app and dev services via Docker Compose.

Core commands:
    init                Build images, start postgres, wait for health, migrate.
    up                  Start all services in the background.
    down                Stop all services.
    status              Show service status.
    logs                Follow web logs (use --all for all services).

App commands:
    shell               Open Django shell inside web.
    bash                Open bash in web container (exec if running, else run).
    manage <args>       Run any Django management command via uv (if available).
    migrate [args]      Run migrations.
    makemigrations      Create new migrations based on model changes.
    makemigrations-check  Dry-run + check for model changes needing migrations.
    createsuperuser     Create a Django superuser (interactive).
    test [args]         Run pytest (via uv if available).
    check               Run 'django check' sanity checks.
    lint                Run ruff check.
    typecheck           Run basedpyright.

Database:
    psql                Connect to postgres using DB_* from .env (when available).
    pgadmin             Start pgAdmin (tools profile).

Examples:
    ./$SCRIPT_NAME init
    ./$SCRIPT_NAME up
    ./$SCRIPT_NAME manage showmigrations
    ./$SCRIPT_NAME test -q
EOF
}

# --- Command Implementations ---

cmd_init() {
    info "Validating environment (.env)..."
    require_envs DB_NAME DB_USER DB_PASSWORD

    info "Building Docker images (fresh base, clean layers)..."
    compose build --pull --force-rm

    info "Starting postgres..."
    compose up -d postgres
    wait_for_health postgres "$TIMEOUT_DEFAULT"

    info "Syncing dependencies and migrating database..."
    # Use uv if present, fallback to python
    web_exec_or_run 'command -v uv >/dev/null 2>&1 && uv sync --frozen || true; \
                                     if command -v uv >/dev/null 2>&1; then uv run python manage.py migrate; else python manage.py migrate; fi'

    echo
    info "Initialization complete!"
    echo "Next steps:"
    echo "  1) ./$SCRIPT_NAME createsuperuser"
    echo "  2) ./$SCRIPT_NAME up"
    echo "  3) Visit http://localhost:8000"
}

cmd_up() {
    compose up -d
    echo
    info "Services started!"
    echo "  - Web: http://localhost:8000"
    echo "  - Logs: ./$SCRIPT_NAME logs"
}

cmd_down() { compose down; info "Services stopped."; }

cmd_status() { compose ps; }

cmd_logs() {
    if [ "${1:-}" = "--all" ]; then shift; compose logs -f web postgres "$@"; else compose logs -f web "$@"; fi
}

cmd_shell() {
    web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run python manage.py shell; else python manage.py shell; fi'
}

cmd_bash() {
    if is_running web; then compose exec web bash; else compose run --rm web bash; fi
}

cmd_manage() {
    if [ $# -lt 1 ]; then die "Usage: $SCRIPT_NAME manage <args>"; fi
    local args=("$@")
    web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run python manage.py '"${args[*]}"'; else python manage.py '"${args[*]}"'; fi'
}

cmd_migrate() {
    local args=("$@")
    web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run python manage.py migrate '"${args[*]}"'; else python manage.py migrate '"${args[*]}"'; fi'
}

cmd_makemigrations() {
    local args=("$@")
    web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run python manage.py makemigrations '"${args[*]}"'; else python manage.py makemigrations '"${args[*]}"'; fi'
}

cmd_makemigrations_check() {
    web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run python manage.py makemigrations --check --dry-run; else python manage.py makemigrations --check --dry-run; fi'
}

cmd_createsuperuser() {
    local args=("$@")
    web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run python manage.py createsuperuser '"${args[*]}"'; else python manage.py createsuperuser '"${args[*]}"'; fi'
}

cmd_test() {
    local args=("$@")
    web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run pytest '"${args[*]}"'; else pytest '"${args[*]}"'; fi'
}

cmd_check() { web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run python manage.py check; else python manage.py check; fi'; }

cmd_lint() { web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run ruff check .; else ruff check .; fi'; }

cmd_typecheck() { web_exec_or_run 'if command -v uv >/dev/null 2>&1; then uv run basedpyright; else basedpyright; fi'; }

cmd_psql() {
    local user name
    user=$(env_get DB_USER onespirit_user)
    name=$(env_get DB_NAME onespirit_db)
    compose exec postgres psql -U "$user" -d "$name"
}

cmd_pgadmin() {
    info "Starting pgAdmin..."
    compose --profile tools up -d pgadmin
    echo
    echo "pgAdmin is available at http://localhost:5050"
    local email password
    email=$(env_get PGADMIN_EMAIL admin@onespirit.com)
    password=$(env_get PGADMIN_PASSWORD admin)
    echo "  Email: $email"
    echo "  Password: $password"
}

# --- Main ---

COMMAND="${1:-}"
if [ -z "$COMMAND" ]; then show_help; exit 1; fi
shift || true

case "$COMMAND" in
    init)                cmd_init ;; 
    up)                  cmd_up ;;
    down)                cmd_down ;;
    status)              cmd_status ;;
    logs)                cmd_logs "$@" ;;

    shell)               cmd_shell ;;
    bash)                cmd_bash ;;
    manage)              cmd_manage "$@" ;;
    migrate)             cmd_migrate "$@" ;;
    makemigrations)      cmd_makemigrations "$@" ;;
    makemigrations-check) cmd_makemigrations_check ;;
    createsuperuser)     cmd_createsuperuser "$@" ;;
    test)                cmd_test "$@" ;;
    check)               cmd_check ;;
    lint)                cmd_lint ;;
    typecheck)           cmd_typecheck ;;

    psql)                cmd_psql ;;
    pgadmin)             cmd_pgadmin ;;
    help|-h|--help)      show_help ;;
    *)                   echo "Unknown command: $COMMAND"; echo; show_help; exit 1 ;;
esac
