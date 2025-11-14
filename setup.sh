#!/bin/bash

# setup.sh - A simple script for setting up a development environment for OneSpirit
# This script runs on the HOST machine and "bounces" commands into the
# correct Docker container using 'docker compose'.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Utility Functions ---

show_help() {
    echo "Usage: ./setup.sh [COMMAND]"
    echo
    echo "A simple utility that manages the OneSpirit Django application and its services for development."
    echo
    echo "Commands:"
    echo "  init          Builds Docker images and initializes the database."
    echo "  up            Starts all services in the background."
    echo "  down          Stops all services."
    echo "  shell         Opens a Django shell in the 'web' container."
    echo "  bash          Opens a bash shell in the 'web' container."
    echo "  test          Runs the pytest test suite inside the 'web' container."
    echo "  psql          Connects to the PostgreSQL database."
    echo "  logs          Follows the logs for the 'web' service."
    echo "  migrate       Runs database migrations."
    echo "  makemigrations Creates new migrations based on model changes."
    echo "  createsuperuser Creates a Django superuser (interactive)."
    echo "  pgadmin       Starts pgAdmin for database management."
    echo "  manage        Runs any Django management command (e.g., ./setup.sh manage collectstatic)."
    echo
}

# --- Command Functions ---

# Builds images and initializes the database
init() {
    echo "Building Docker images..."
    docker compose build --pull --force-rm

    echo "Starting PostgreSQL service..."
    docker compose up -d postgres

    echo "Waiting for database to be ready..."
    # This uses the healthcheck defined in the docker-compose.yaml file.
    until [ "$(docker inspect -f {{.State.Health.Status}} $(docker compose ps -q postgres))" == "healthy" ]; do
        sleep 2
        echo -n "."
    done
    echo
    echo "Database is ready."

    echo "Running database migrations..."
    docker compose run --rm web python manage.py migrate

    echo
    echo "Initialization complete!"
    echo
    echo "Next steps:"
    echo "  1. Run './setup.sh createsuperuser' to create an admin user"
    echo "  2. Run './setup.sh up' to start the application"
    echo "  3. Visit http://localhost:8000 in your browser"
}

# --- Main Execution Logic ---

COMMAND=$1

if [ -z "$COMMAND" ]; then
    show_help
    exit 1
fi

# Shift to allow passing arguments to commands (e.g., ./setup.sh logs -f)
shift

case $COMMAND in
init)
    init
    ;;
up)
    docker compose up -d
    echo
    echo "Services started!"
    echo "  - Web application: http://localhost:8000"
    echo "  - Run './setup.sh logs' to view application logs"
    ;;
down)
    docker compose down
    echo "Services stopped."
    ;;
shell)
    docker compose run --rm web python manage.py shell
    ;;
bash)
    docker compose run --rm web bash
    ;;
test)
    docker compose run --rm web pytest "$@"
    ;;
psql)
    docker compose exec postgres psql --username=onespirit_user --dbname=onespirit_db
    ;;
logs)
    docker compose logs -f web "$@"
    ;;
migrate)
    docker compose run --rm web python manage.py migrate "$@"
    ;;
makemigrations)
    docker compose run --rm web python manage.py makemigrations "$@"
    ;;
createsuperuser)
    docker compose run --rm web python manage.py createsuperuser "$@"
    ;;
pgadmin)
    echo "Starting pgAdmin..."
    docker compose --profile tools up -d pgadmin
    echo
    echo "pgAdmin is now available at http://localhost:5050"
    echo "  Email: admin@onespirit.com (or check your .env file)"
    echo "  Password: admin (or check your .env file)"
    ;;
manage)
    docker compose run --rm web python manage.py "$@"
    ;;
*)
    echo "Error: Unknown command '$COMMAND'"
    echo
    show_help
    exit 1
    ;;
esac
