# DigitalOcean Production Deployment Guide

This guide outlines the steps to deploy OneSpirit to a DigitalOcean Droplet using the production setup scripts.

## 1. Infrastructure Setup

### Create Droplet
1. Log in to DigitalOcean.
2. Click **Create** -> **Droplets**.
3. **Region**: Choose a region close to your users.
4. **Image**: Choose **Marketplace** -> **Docker** (comes with Docker & Compose pre-installed) OR standard **Ubuntu 24.04 LTS**.
5. **Size**: Minimum **Basic / Regular / 2GB RAM / 1 CPU** recommended.
   - *Note: 1GB RAM is the absolute minimum but may require swap space.*
6. **Authentication**: Add your SSH Key.
7. **Hostname**: Give it a meaningful name (e.g., `onespirit-prod`).
8. Click **Create Droplet**.

### DNS Configuration
1. Go to your domain registrar or DigitalOcean Networking.
2. Create an **A Record** pointing `@` (root) to your Droplet's IP address.
3. Create a **CNAME Record** pointing `www` to `@`.

### Firewall (Recommended)
1. In DigitalOcean, go to **Networking** -> **Firewalls**.
2. Create a firewall allowing:
   - SSH (TCP 22)
   - HTTP (TCP 80)
   - HTTPS (TCP 443)
3. Apply it to your Droplet.

## 2. Server Preparation

SSH into your droplet:
```bash
ssh root@your_droplet_ip
```

If you didn't choose the Docker Marketplace image, install Docker manually:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

## 3. Application Deployment

### Clone Repository
```bash
git clone https://github.com/joels789/onespirit.git
cd onespirit
```

### Configure Environment
1. Copy the production environment template:
   ```bash
   cp .env.prod.example .env.prod
   ```

2. Edit the configuration:
   ```bash
   nano .env.prod
   ```
   - Update `VIRTUAL_HOST` and `LETSENCRYPT_HOST` with your domain.
   - Update `LETSENCRYPT_EMAIL` with your email (for SSL renewal).
   - Update `ALLOWED_HOSTS`.
   - Configure Email settings (SMTP).
   - *Note: You do NOT need to set DB_PASSWORD or REDIS_PASSWORD in this file.*

### Initialize Secrets
Run the secrets management script to securely generate passwords:
```bash
./manage-secrets.sh init
```
- Follow the interactive prompts.
- It will automatically generate secure values for:
  - `secrets/db_password.txt`
  - `secrets/django_secret_key.txt`
  - `secrets/redis_password.txt`
- You can optionally set `email_password` here if using SMTP.

## 4. Build and Launch

### Initialize Production
Run the setup script to build images and initialize the database:
```bash
./setup-prod.sh init
```
This automated script will:
- Build the Docker images (using multi-stage build).
- Start Postgres and Redis containers.
- Wait for services to be healthy.
- Run database migrations.
- Collect static files.

### Create Admin User
Create your initial superuser account:
```bash
./setup-prod.sh createsuperuser
```

### Start Services
Launch the full stack in detached mode:
```bash
./setup-prod.sh up
```

## 5. Verification

1. **Browser**: Visit `https://yourdomain.com`. SSL should be active.
2. **Health Check**: Visit `https://yourdomain.com/health/` to verify DB and Cache connectivity.
3. **Logs**: Check application logs if needed:
   ```bash
   ./setup-prod.sh logs
   ```

## 6. Maintenance & Updates

### Deploying Updates
To deploy new code changes:
```bash
git pull
./setup-prod.sh build
./setup-prod.sh up
```

### Database Backups
Create a compressed backup (saved to `backups/`):
```bash
./setup-prod.sh backup-db
```

### Restore Database
Restore from a specific backup file:
```bash
./setup-prod.sh restore-db backups/db_backup_YYYYMMDD_HHMMSS.sql.gz
```
