#!/bin/bash

# setup-prod.sh - Production deployment script for OneSpirit
# This script manages production services using docker-compose.prod.yaml

set -e # Exit immediately if a command exits with a non-zero status.

COMPOSE_FILE="docker-compose.prod.yaml"
ENV_FILE=".env.prod"

# --- Utility Functions ---

show_help() {
    echo "Usage: ./setup-prod.sh [COMMAND]"
    echo
    echo "Production deployment utility for OneSpirit."
    echo
    echo "Commands:"
    echo "  init          Initializes production environment (first-time setup)."
    echo "  build         Builds production Docker images."
    echo "  up            Starts all production services."
    echo "  down          Stops all production services."
    echo "  restart       Restarts the web application."
    echo "  logs          Shows logs for the web service."
    echo "  shell         Opens a Django shell in production."
    echo "  bash          Opens a bash shell in the web container."
    echo "  migrate       Runs database migrations."
    echo "  createsuperuser Creates a Django superuser."
    echo "  collectstatic Collects static files."
    echo "  backup-db     Creates a database backup."
    echo "  restore-db    Restores database from backup (requires backup file path)."
    echo "  status        Shows status of all services."
    echo "  ssl-renew     Manually triggers SSL certificate renewal."
    echo
}

check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        echo "Error: $ENV_FILE not found!"
        echo "Please copy .env.prod.example to $ENV_FILE and configure it."
        exit 1
    fi
}

load_env_vars() {
    # Load environment variables from .env.prod file
    # This is needed for backup/restore operations to get DB credentials
    check_env_file

    # Export variables from .env file
    set -a  # Automatically export all variables
    source "$ENV_FILE"
    set +a  # Stop automatically exporting

    # Validate required database variables
    if [ -z "$DB_USER" ]; then
        echo "Error: DB_USER not set in $ENV_FILE"
        exit 1
    fi

    if [ -z "$DB_NAME" ]; then
        echo "Error: DB_NAME not set in $ENV_FILE"
        exit 1
    fi

    # Load DB password from secrets file (matches what postgres container uses)
    if [ -f "secrets/db_password.txt" ]; then
        DB_PASSWORD=$(cat secrets/db_password.txt)
    elif [ -z "$DB_PASSWORD" ]; then
        echo "Error: DB password not found in secrets/db_password.txt or $ENV_FILE"
        exit 1
    fi
}

# --- Command Functions ---

wait_for_service_health() {
    # Waits for a service to become healthy using dynamic container lookup
    # Args:
    #   $1 - service name (e.g., postgres, redis)
    #   $2 - timeout in seconds (optional, default: 300)
    local service_name=$1
    local timeout=${2:-300}  # Default 5 minutes
    local elapsed=0

    echo "Waiting for $service_name to be ready..."

    # Get container ID dynamically using docker compose
    local container_id=$(docker compose -f $COMPOSE_FILE ps -q $service_name)

    if [ -z "$container_id" ]; then
        echo "Error: $service_name container not found!"
        echo "Make sure the service is started with 'docker compose up -d $service_name'"
        exit 1
    fi

    # Wait for health check to pass
    until [ "$(docker inspect -f '{{.State.Health.Status}}' $container_id)" == "healthy" ]; do
        if [ $elapsed -ge $timeout ]; then
            echo
            echo "Error: $service_name failed to become healthy within ${timeout}s"
            echo "Check logs with: docker compose -f $COMPOSE_FILE logs $service_name"
            exit 1
        fi

        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    echo
    echo "$service_name is ready."
}

init() {
    echo "Initializing OneSpirit production environment..."

    check_env_file

    echo "Building production Docker images..."
    docker compose -f $COMPOSE_FILE build --no-cache

    echo "Starting database and redis services..."
    docker compose -f $COMPOSE_FILE up -d postgres redis

    # Use dynamic container lookup instead of hardcoded name
    wait_for_service_health postgres

    echo "Running database migrations..."
    docker compose -f $COMPOSE_FILE run --rm web python manage.py migrate

    echo "Collecting static files..."
    docker compose -f $COMPOSE_FILE run --rm web python manage.py collectstatic --noinput

    echo
    echo "Production initialization complete!"
    echo
    echo "Next steps:"
    echo "  1. Run './setup-prod.sh createsuperuser' to create an admin user"
    echo "  2. Run './setup-prod.sh up' to start all services"
    echo "  3. Check './setup-prod.sh status' to verify services are running"
}

backup_db() {
    # Load environment variables from .env.prod
    load_env_vars

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backups/db_backup_${TIMESTAMP}.sql"

    echo "Creating database backup..."
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    mkdir -p backups

    # Perform the backup with password from environment
    docker compose -f $COMPOSE_FILE exec -T \
        -e PGPASSWORD="$DB_PASSWORD" \
        postgres pg_dump \
        -U "$DB_USER" \
        "$DB_NAME" > "$BACKUP_FILE"

    if [ $? -ne 0 ]; then
        echo "Error: Database backup failed!"
        rm -f "$BACKUP_FILE"
        exit 1
    fi

    echo "Backup created: $BACKUP_FILE"

    # Compress the backup
    gzip "$BACKUP_FILE"

    if [ $? -ne 0 ]; then
        echo "Error: Backup compression failed!"
        exit 1
    fi

    echo "Compressed backup: ${BACKUP_FILE}.gz"

    # Show backup size
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
    echo "Backup size: $BACKUP_SIZE"
}

restore_db() {
    # Load environment variables from .env.prod
    load_env_vars

    if [ -z "$1" ]; then
        echo "Error: Please provide the backup file path"
        echo "Usage: ./setup-prod.sh restore-db <backup-file.sql.gz>"
        exit 1
    fi

    BACKUP_FILE=$1

    if [ ! -f "$BACKUP_FILE" ]; then
        echo "Error: Backup file not found: $BACKUP_FILE"
        exit 1
    fi

    # Show backup info
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup file: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
    echo "  Target database: $DB_NAME"
    echo "  User: $DB_USER"
    echo

    echo "WARNING: This will overwrite the current database!"
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled."
        exit 0
    fi

    echo "Restoring database from $BACKUP_FILE..."

    # Restore the database with password from environment
    if [[ $BACKUP_FILE == *.gz ]]; then
        gunzip -c "$BACKUP_FILE" | docker compose -f $COMPOSE_FILE exec -T \
            -e PGPASSWORD="$DB_PASSWORD" \
            postgres psql \
            -U "$DB_USER" \
            "$DB_NAME"
    else
        docker compose -f $COMPOSE_FILE exec -T \
            -e PGPASSWORD="$DB_PASSWORD" \
            postgres psql \
            -U "$DB_USER" \
            "$DB_NAME" < "$BACKUP_FILE"
    fi

    if [ $? -ne 0 ]; then
        echo "Error: Database restore failed!"
        exit 1
    fi

    echo "Database restored successfully."
}

# --- Main Execution Logic ---

COMMAND=$1

if [ -z "$COMMAND" ]; then
    show_help
    exit 1
fi

shift

case $COMMAND in
    init)
        init
        ;;
    build)
        check_env_file
        docker compose -f $COMPOSE_FILE build "$@"
        ;;
    up)
        check_env_file
        docker compose -f $COMPOSE_FILE up -d
        echo
        echo "Production services started!"
        echo "  - Application: https://${VIRTUAL_HOST:-yourdomain.com}"
        echo "  - Run './setup-prod.sh logs' to view logs"
        echo "  - Run './setup-prod.sh status' to check service status"
        ;;
    down)
        docker compose -f $COMPOSE_FILE down
        echo "Production services stopped."
        ;;
    restart)
        docker compose -f $COMPOSE_FILE restart web
        echo "Web application restarted."
        ;;
    logs)
        docker compose -f $COMPOSE_FILE logs -f web "$@"
        ;;
    shell)
        docker compose -f $COMPOSE_FILE exec web python manage.py shell
        ;;
    bash)
        docker compose -f $COMPOSE_FILE exec web bash
        ;;
    migrate)
        docker compose -f $COMPOSE_FILE exec web python manage.py migrate "$@"
        ;;
    createsuperuser)
        docker compose -f $COMPOSE_FILE exec web python manage.py createsuperuser "$@"
        ;;
    collectstatic)
        docker compose -f $COMPOSE_FILE exec web python manage.py collectstatic --noinput "$@"
        ;;
    backup-db)
        backup_db
        ;;
    restore-db)
        restore_db "$@"
        ;;
    status)
        docker compose -f $COMPOSE_FILE ps
        ;;
    ssl-renew)
        docker compose -f $COMPOSE_FILE exec nginx-letsencrypt /app/force_renew
        echo "SSL certificate renewal triggered."
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        echo
        show_help
        exit 1
        ;;
esac
