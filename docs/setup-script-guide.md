# Setup Script Guide

## Overview

A setup.sh script for setting up the development environment for the OneSpirit project.


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

