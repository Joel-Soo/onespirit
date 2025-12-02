# Production Setup Audit Report - November 20, 2025

## Overview

This audit reviews the production deployment configuration for the OneSpirit Django application, including:
- `setup-prod.sh` - Production deployment management script
- `Dockerfile.prod` - Multi-stage production container build
- `docker-compose.prod.yaml` - Production services orchestration
- `manage-secrets.sh` - Docker secrets management utility
- `.env.prod.example` - Production environment template
- `onespirit_project/settings/prod.py` - Django production settings

## ✅ **Excellent Practices Implemented**

### 1. **Security**
- ✅ Docker secrets for sensitive data (DB password, Django secret key, email password)
- ✅ Non-root user in Dockerfile (`onespirit` user)
- ✅ Secure cookie settings (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
- ✅ HSTS headers with preload (31536000 seconds / 1 year)
- ✅ SSL/TLS enforcement with automatic Let's Encrypt certificates
- ✅ Docker socket proxy with restricted permissions (excellent security pattern!)
- ✅ `read_only: true` on docker-socket-proxy
- ✅ File permissions validation in `manage-secrets.sh` (enforces 600)
- ✅ `.gitignore` properly excludes secrets and sensitive files
- ✅ `SECURE_CONTENT_TYPE_NOSNIFF` and `X_FRAME_OPTIONS` properly set
- ✅ `SECURE_PROXY_SSL_HEADER` configured for nginx reverse proxy
- ✅ `CSRF_TRUSTED_ORIGINS` derived from ALLOWED_HOSTS

### 2. **Container Best Practices**
- ✅ Multi-stage build reducing image size (builder + production stages)
- ✅ Health checks on all critical services (postgres, redis, web, nginx)
- ✅ Proper `.dockerignore` excluding ~680MB of unnecessary files
- ✅ Using Alpine images for smaller footprint (postgres:16-alpine, redis:7-alpine)
- ✅ Resource limits on all services (CPU and memory with limits + reservations)
- ✅ Restart policies (`unless-stopped` for services, `always` for infrastructure)
- ✅ Using `uv` for fast, reproducible dependency installation with locked dependencies
- ✅ `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1` properly set
- ✅ Separate networks for service isolation

### 3. **Database Management**
- ✅ Database backup/restore functionality with timestamp-based naming
- ✅ Compressed backups (.sql.gz) for storage efficiency
- ✅ Health check for PostgreSQL (`pg_isready`)
- ✅ Proper wait mechanism for service readiness with dynamic container lookup
- ✅ Named volumes for data persistence
- ✅ PostgreSQL 16 (latest stable)
- ✅ Backup size reporting

### 4. **Operational Excellence**
- ✅ Comprehensive setup script with clear, well-documented commands
- ✅ Centralized logging configuration with rotation (10MB files, 5 backups)
- ✅ Proper static file collection workflow
- ✅ Excellent secrets management script with interactive setup
- ✅ Network isolation with custom bridge network
- ✅ Service status checking capability
- ✅ Support for manual SSL certificate renewal
- ✅ Interactive confirmation for destructive operations (restore-db)
- ✅ Gunicorn configured with proper workers, threads, and timeouts
- ✅ Separate access and error logs for Gunicorn

### 5. **Development Experience**
- ✅ Clear command structure (`init`, `up`, `down`, `restart`, etc.)
- ✅ Helpful error messages and next steps guidance
- ✅ Environment variable validation
- ✅ Docker Compose file validation
- ✅ Secret generation helpers (Django secret key, passwords, hex)

## ⚠️ **Issues & Recommendations**

### **CRITICAL Issues** 🔴

#### 1. **Missing Health Endpoint**
**Location**: `Dockerfile.prod:68`

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD sh -c 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/ ...
```

**Problem**: The health check references `/health/` endpoint, but it doesn't exist in your Django URLs.

**Impact**: Container health checks will fail or fall back to checking root URL, which may not accurately represent application health.

**Solution**: Create a simple health check view:

```python
# In onespirit_project/urls.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """
    Health check endpoint for Docker/Kubernetes health monitoring.
    Checks database connectivity and returns appropriate status.
    """
    try:
        # Check database connectivity
        connection.ensure_connection()
        return JsonResponse({
            "status": "healthy",
            "database": "connected"
        })
    except Exception as e:
        return JsonResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status=503)

urlpatterns = [
    path('health/', health_check, name='health_check'),
    # ... other patterns
]
```

**Alternative**: If you prefer not to add a health endpoint, update the Dockerfile healthcheck to only check root:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1
```

#### 2. **Missing MEDIA_ROOT/MEDIA_URL Configuration**
**Location**: `onespirit_project/settings/base.py` and `settings/prod.py`

**Problem**: Production settings don't configure media file handling, but docker-compose mounts `/app/media` volume and nginx mounts it read-only.

**Impact**: User-uploaded files won't work properly. Django won't know where to store/serve media files.

**Solution**: Add to `settings/base.py`:

```python
# Media files (user uploads)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

And in `settings/prod.py`:

```python
# Override for production to use absolute path matching docker volume
MEDIA_ROOT = Path('/app/media')
```

Also ensure your `urls.py` serves media in development:

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... your patterns
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

#### 3. **Nginx Configuration Directory Missing**
**Location**: `docker-compose.prod.yaml:70`

```yaml
volumes:
  - ./config/nginx:/etc/nginx/conf.d:ro
```

**Problem**: The directory `config/nginx/` doesn't exist in the repository.

**Impact**: Docker Compose will create an empty directory, but the mount will succeed silently. Custom nginx configurations won't be possible, and there's confusion about intent.

**Solution**: Either:

**Option A - Create the directory with example config**:
```bash
mkdir -p config/nginx
cat > config/nginx/custom.conf <<EOF
# Custom nginx configuration for OneSpirit
# Example: Increase client body size for file uploads
client_max_body_size 100M;

# Example: Add custom headers
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
EOF
```

**Option B - Remove the mount** if custom configuration isn't needed:
```yaml
# Remove this line from nginx-proxy volumes:
# - ./config/nginx:/etc/nginx/conf.d:ro
```

nginx-proxy automatically generates configuration based on environment variables.

#### 4. **PostgreSQL Backup Password Handling**
**Location**: `setup-prod.sh:161`

```bash
docker compose -f $COMPOSE_FILE exec -T postgres pg_dump \
    -U "$DB_USER" \
    "$DB_NAME" > "$BACKUP_FILE"
```

**Problem**: `pg_dump` needs database password, but it's not provided. This may prompt for password interactively (breaking automation) or fail if password is required.

**Impact**: Automated backups may fail or require manual intervention.

**Solution**: Pass password via environment variable:

```bash
# In backup_db function, after loading env vars
docker compose -f $COMPOSE_FILE exec -T \
    -e PGPASSWORD="$DB_PASSWORD" \
    postgres pg_dump \
    -U "$DB_USER" \
    "$DB_NAME" > "$BACKUP_FILE"
```

Note: Since PostgreSQL in docker-compose uses `POSTGRES_PASSWORD_FILE`, you need to also load the password:

```bash
# After load_env_vars call, add:
if [ -z "$DB_PASSWORD" ]; then
    # Try to read from secrets file if DB_PASSWORD not in .env
    if [ -f "secrets/db_password.txt" ]; then
        DB_PASSWORD=$(cat secrets/db_password.txt)
    else
        echo "Error: Cannot find DB_PASSWORD"
        exit 1
    fi
fi
```

### **HIGH Priority Issues** 🟠

#### 5. **No Redis Password Protection**
**Location**: `docker-compose.prod.yaml:156`

```yaml
command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

**Problem**: Redis has no authentication enabled, allowing anyone with network access to read/write cache data.

**Impact**: Security vulnerability if network isolation fails or containers are compromised.

**Recommendation**: Add password protection:

1. Add to `.env.prod.example`:
```bash
REDIS_PASSWORD=CHANGE-THIS-TO-A-SECURE-REDIS-PASSWORD
```

2. Update docker-compose.prod.yaml:
```yaml
redis:
  environment:
    - REDIS_PASSWORD_FILE=/run/secrets/redis_password
  secrets:
    - redis_password
  command: >
    sh -c 'redis-server 
    --appendonly yes 
    --maxmemory 256mb 
    --maxmemory-policy allkeys-lru 
    --requirepass $$(cat /run/secrets/redis_password)'
```

3. Update web service REDIS_URL:
```yaml
- REDIS_URL=redis://:$${REDIS_PASSWORD}@redis:6379/1
```

4. Add to secrets in manage-secrets.sh:
```bash
REQUIRED_SECRETS=("db_password" "django_secret_key" "redis_password")
```

#### 6. **Gunicorn Worker Configuration**
**Location**: `Dockerfile.prod:75`

```dockerfile
CMD ["gunicorn", "--workers", "4", "--threads", "2", ...]
```

**Problem**: Static worker count (4) doesn't scale with available CPUs. Production servers with different CPU counts will be under or over-utilized.

**Impact**: Performance issues - too few workers on powerful servers, too many on small servers.

**Recommendation**: Make configurable via environment variable with formula:

```dockerfile
CMD sh -c 'WORKERS=${GUNICORN_WORKERS:-$((2 * $(nproc) + 1))}; \
           THREADS=${GUNICORN_THREADS:-2}; \
           exec gunicorn \
           --workers $WORKERS \
           --threads $THREADS \
           --timeout 60 \
           --bind 0.0.0.0:8000 \
           --access-logfile /app/logs/gunicorn-access.log \
           --error-logfile /app/logs/gunicorn-error.log \
           --log-level info \
           onespirit_project.wsgi:application'
```

Add to `.env.prod.example`:
```bash
# Gunicorn worker configuration (default: 2*CPU+1)
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
```

#### 7. **Email Password Inconsistency**
**Location**: `.env.prod.example:35` vs `docker-compose.prod.yaml:200`

**Problem**: Example file uses `EMAIL_HOST_PASSWORD` but docker-compose expects `EMAIL_PASSWORD_FILE`.

**Impact**: Confusion during setup, potential misconfiguration.

**Solution**: Update `.env.prod.example`:
```bash
# Email Configuration (Update with your SMTP settings)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
# Note: Password is stored in secrets/email_password.txt, not in this file
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
SERVER_EMAIL=server@yourdomain.com
```

Add comment in `manage-secrets.sh` explaining email password is optional.

#### 8. **Backup/Restore DB_PASSWORD Handling**
**Location**: `setup-prod.sh:141-223`

**Problem**: The `load_env_vars` function loads from `.env.prod`, but the actual password used by PostgreSQL comes from Docker secrets file. There's a mismatch.

**Impact**: Backup/restore operations may use wrong password or fail.

**Solution**: Consolidate password loading:

```bash
load_env_vars() {
    check_env_file
    
    set -a
    source "$ENV_FILE"
    set +a
    
    # Validate required variables
    if [ -z "$DB_USER" ] || [ -z "$DB_NAME" ]; then
        echo "Error: DB_USER and DB_NAME must be set in $ENV_FILE"
        exit 1
    fi
    
    # Load actual password from secrets file (matches what postgres container uses)
    if [ -f "secrets/db_password.txt" ]; then
        DB_PASSWORD=$(cat secrets/db_password.txt)
    elif [ -z "$DB_PASSWORD" ]; then
        echo "Error: DB password not found in secrets/db_password.txt or $ENV_FILE"
        exit 1
    fi
}
```

### **MEDIUM Priority Issues** 🟡

#### 9. **collectstatic in Dockerfile**
**Location**: `Dockerfile.prod:59`

```dockerfile
RUN python manage.py collectstatic --noinput || true
```

**Problem**: 
- Silently fails with `|| true` without indication of what went wrong
- Static files collected at build time may not match deployment-time configuration
- Build fails if SECRET_KEY or database settings aren't available

**Impact**: Unpredictable static file collection, potential build failures.

**Recommendation**: Remove from Dockerfile and rely solely on deployment script:

```dockerfile
# Remove this line entirely:
# RUN python manage.py collectstatic --noinput || true
```

The `setup-prod.sh init` command already runs collectstatic properly.

#### 10. **No Log Rotation Configuration**
**Location**: `docker-compose.prod.yaml:217`, `Dockerfile.prod:70-71`

```yaml
- ./logs:/app/logs
```

**Problem**: Application and Gunicorn logs will grow indefinitely. While Django has RotatingFileHandler (10MB x 5), Gunicorn logs don't rotate and the host mount means logs accumulate.

**Impact**: Disk space exhaustion over time.

**Recommendation**: Add logrotate configuration:

```bash
# Create on host system
sudo tee /etc/logrotate.d/onespirit <<EOF
/path/to/onespirit/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 onespirit onespirit
    sharedscripts
    postrotate
        docker compose -f /path/to/onespirit/docker-compose.prod.yaml exec web kill -USR1 \$(cat /app/gunicorn.pid 2>/dev/null) 2>/dev/null || true
    endscript
}
EOF
```

Or use Docker logging drivers:

```yaml
web:
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

#### 11. **Missing Docker Compose File Version Check**
**Location**: `setup-prod.sh`

**Problem**: Script uses `docker compose` (v2 syntax) but doesn't verify it's available.

**Impact**: May fail on systems with only docker-compose (v1).

**Recommendation**: Add version check:

```bash
check_docker_compose() {
    if ! command -v docker &> /dev/null; then
        echo "Error: docker command not found"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        echo "Error: docker compose (v2) not found"
        echo "Please install Docker Compose v2: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# Call in init and other critical commands
```

#### 12. **No Backup Retention Policy**
**Location**: `setup-prod.sh:backup_db`

**Problem**: Backups accumulate indefinitely in `backups/` directory.

**Impact**: Disk space consumption, difficulty finding relevant backups.

**Recommendation**: Add retention policy:

```bash
backup_db() {
    # ... existing backup code ...
    
    echo "Backup size: $BACKUP_SIZE"
    
    # Cleanup old backups (keep last 30 days)
    find backups/ -name "db_backup_*.sql.gz" -mtime +30 -delete
    
    echo "Cleaned up backups older than 30 days"
    echo "Current backups:"
    ls -lh backups/ | grep "db_backup_"
}
```

#### 13. **Secrets File Permissions on Creation**
**Location**: `manage-secrets.sh:69`

```bash
create_secret_file() {
    local secret_name=$1
    local secret_value=$2
    local file_path="${SECRETS_DIR}/${secret_name}.txt"

    echo -n "$secret_value" > "$file_path"
    chmod 600 "$file_path"
}
```

**Problem**: File is created with default permissions before being changed to 600, creating a brief window of exposure.

**Impact**: Low risk but not ideal for security-sensitive operations.

**Recommendation**: Use umask:

```bash
create_secret_file() {
    local secret_name=$1
    local secret_value=$2
    local file_path="${SECRETS_DIR}/${secret_name}.txt"
    
    # Set umask to create file with 600 permissions from start
    (umask 077 && echo -n "$secret_value" > "$file_path")
    print_success "Created ${file_path}"
}
```

#### 14. **PostgreSQL Configuration Not Optimized**
**Location**: `docker-compose.prod.yaml:115`

**Problem**: Using default PostgreSQL configuration, which may not be optimal for production workloads.

**Impact**: Suboptimal database performance.

**Recommendation**: Add custom postgresql.conf or environment variables:

```yaml
postgres:
  environment:
    # ... existing vars ...
    - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
  command: >
    postgres
    -c shared_buffers=256MB
    -c effective_cache_size=1GB
    -c maintenance_work_mem=64MB
    -c checkpoint_completion_target=0.9
    -c wal_buffers=16MB
    -c default_statistics_target=100
    -c random_page_cost=1.1
    -c effective_io_concurrency=200
    -c work_mem=4MB
    -c min_wal_size=1GB
    -c max_wal_size=4GB
    -c max_connections=100
```

Or mount a custom config file.

### **LOW Priority Issues** 🟢

#### 15. **WSGI Module Environment Variable Redundancy**
**Location**: `onespirit_project/wsgi.py:14`

```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onespirit_project.settings.prod')
```

**Note**: This is set in both wsgi.py and docker-compose environment. While not harmful, it's redundant.

**Recommendation**: Either:
- Keep in wsgi.py for fallback (current approach is fine)
- Or rely solely on docker-compose environment variable

Current approach is actually the best practice for defense in depth.

#### 16. **Container Names Prevent Multiple Instances**
**Location**: Various in `docker-compose.prod.yaml`

```yaml
container_name: onespirit_web_prod
```

**Problem**: Fixed container names prevent running multiple instances (e.g., blue-green deployments, testing).

**Impact**: Limited deployment flexibility.

**Recommendation**: If you need multiple instances, remove `container_name` and use:
```bash
docker compose -p onespirit_v1 -f docker-compose.prod.yaml up
docker compose -p onespirit_v2 -f docker-compose.prod.yaml up
```

However, for single-instance deployments, current approach is fine and makes management easier.

#### 17. **No Sentry Integration (Commented)**
**Location**: `.env.prod.example:45`

```bash
# Sentry Configuration (Optional - for error tracking)
# SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

**Impact**: No automated error tracking in production.

**Recommendation**: Implement Sentry integration:

1. Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing ...
    "sentry-sdk[django]>=2.0.0",
]
```

2. Add to `settings/prod.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_dsn = os.getenv('SENTRY_DSN')
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% of transactions
        send_default_pii=False,
        environment='production',
    )
```

#### 18. **No Database Connection Pooling**
**Problem**: Django creates new database connections for each request without pooling.

**Impact**: Increased latency and database load.

**Recommendation**: Add pgBouncer service:

```yaml
pgbouncer:
  image: pgbouncer/pgbouncer:latest
  restart: unless-stopped
  networks:
    - onespirit_network
  environment:
    - DATABASES_HOST=postgres
    - DATABASES_PORT=5432
    - DATABASES_USER=${DB_USER}
    - DATABASES_PASSWORD_FILE=/run/secrets/db_password
    - DATABASES_DBNAME=${DB_NAME}
    - PGBOUNCER_POOL_MODE=transaction
    - PGBOUNCER_MAX_CLIENT_CONN=100
    - PGBOUNCER_DEFAULT_POOL_SIZE=25
  secrets:
    - db_password
  depends_on:
    postgres:
      condition: service_healthy
```

Update web service to connect to pgbouncer instead of postgres directly.

#### 19. **Missing Nginx Custom Configuration Examples**
**Problem**: No documentation or examples of what to put in `config/nginx/`.

**Recommendation**: Create `config/nginx/README.md`:

```markdown
# Custom Nginx Configuration

This directory contains custom nginx configuration files that will be
included in the nginx-proxy container.

## Common Configurations

### Rate Limiting
Create `rate-limit.conf`:
```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
```

### Client Upload Size
Create `client-size.conf`:
```nginx
client_max_body_size 100M;
client_body_buffer_size 128k;
```

### Security Headers (if not set by Django)
Create `security-headers.conf`:
```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```
```

#### 20. **No Health Check Monitoring**
**Problem**: Health checks are defined but not monitored/alerted.

**Recommendation**: Add monitoring service:

```yaml
# In docker-compose.prod.yaml
uptime-kuma:
  image: louislam/uptime-kuma:1
  restart: unless-stopped
  networks:
    - onespirit_network
  volumes:
    - uptime-kuma:/app/data
  ports:
    - "3001:3001"
```

Or integrate with external monitoring (Datadog, New Relic, etc.).

## 📋 **Missing Best Practices**

### 1. **Automated Backup Scheduling**
**Current**: Manual backup via `./setup-prod.sh backup-db`

**Recommendation**: Add cron job or systemd timer:

```bash
# /etc/cron.d/onespirit-backup
0 2 * * * onespirit cd /path/to/onespirit && ./setup-prod.sh backup-db >> /var/log/onespirit-backup.log 2>&1
```

Or add a backup service in docker-compose with cron:

```yaml
backup:
  image: postgres:16-alpine
  restart: unless-stopped
  networks:
    - onespirit_network
  environment:
    - PGHOST=postgres
    - PGUSER=${DB_USER}
    - PGDATABASE=${DB_NAME}
    - PGPASSWORD_FILE=/run/secrets/db_password
  secrets:
    - db_password
  volumes:
    - ./backups:/backups
    - ./scripts/backup.sh:/backup.sh:ro
  command: sh -c 'while true; do sleep 86400; /backup.sh; done'
```

### 2. **Backup Verification**
**Current**: Backups created but never tested

**Recommendation**: Add restore test to CI/CD:

```bash
# Test backup integrity
test_backup() {
    BACKUP_FILE=$1
    echo "Testing backup restoration..."
    
    # Create test database
    docker compose -f $COMPOSE_FILE exec postgres \
        psql -U postgres -c "CREATE DATABASE test_restore;"
    
    # Restore to test database
    gunzip -c "$BACKUP_FILE" | docker compose -f $COMPOSE_FILE exec -T postgres \
        psql -U postgres test_restore
    
    if [ $? -eq 0 ]; then
        echo "Backup restoration successful!"
        # Cleanup
        docker compose -f $COMPOSE_FILE exec postgres \
            psql -U postgres -c "DROP DATABASE test_restore;"
        return 0
    else
        echo "Backup restoration failed!"
        return 1
    fi
}
```

### 3. **SSL Certificate Expiry Monitoring**
**Current**: Manual renewal trigger available

**Recommendation**: Add monitoring and automated alerts:

```bash
# Add to cron
0 0 * * * docker compose -f /path/to/docker-compose.prod.yaml exec nginx-proxy \
  find /etc/nginx/certs -name "*.crt" -mtime +60 -exec echo "SSL cert expiring soon: {}" \; | \
  mail -s "OneSpirit SSL Certificate Alert" admin@example.com
```

### 4. **Secrets Rotation Schedule**
**Current**: Manual rotation supported via `manage-secrets.sh rotate`

**Recommendation**: Document rotation policy:

```markdown
# Security Policy

## Secrets Rotation Schedule

- **Django SECRET_KEY**: Rotate every 90 days
- **Database Password**: Rotate every 180 days
- **Redis Password**: Rotate every 180 days
- **Email Password**: Rotate when email account password changes

## Rotation Procedure

1. Run `./manage-secrets.sh rotate <secret_name>`
2. Update any external references (monitoring, CI/CD)
3. Restart services: `./setup-prod.sh restart`
4. Verify functionality
5. Document rotation in change log
```

### 5. **Performance Monitoring**
**Missing**: Application performance metrics

**Recommendation**: Add APM integration:

```yaml
# Prometheus for metrics
prometheus:
  image: prom/prometheus:latest
  restart: unless-stopped
  networks:
    - onespirit_network
  volumes:
    - ./config/prometheus:/etc/prometheus
    - prometheus-data:/prometheus
  ports:
    - "9090:9090"
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'

# Grafana for visualization
grafana:
  image: grafana/grafana:latest
  restart: unless-stopped
  networks:
    - onespirit_network
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
  volumes:
    - grafana-data:/var/lib/grafana
  ports:
    - "3000:3000"
```

### 6. **Disaster Recovery Documentation**
**Missing**: Documented DR procedures

**Recommendation**: Create `docs/disaster-recovery.md`:

```markdown
# Disaster Recovery Plan

## Recovery Time Objective (RTO)
- Target: 4 hours

## Recovery Point Objective (RPO)
- Target: 24 hours (daily backups)

## Backup Locations
- Primary: Server local disk (`./backups/`)
- Secondary: S3/Cloud Storage (recommended)

## Recovery Procedures

### Database Failure
1. Check backup availability
2. Provision new database container
3. Restore from latest backup
4. Verify data integrity
5. Update connection strings if needed

### Complete Server Failure
1. Provision new server
2. Install Docker and dependencies
3. Clone repository
4. Restore `.env.prod` from secure backup
5. Restore secrets from secure backup
6. Restore database from backup
7. Run `./setup-prod.sh init`
8. Update DNS if IP changed
```

### 7. **Blue-Green Deployment Support**
**Missing**: Zero-downtime deployment strategy

**Recommendation**: Implement deployment pipeline:

```bash
# deploy-bluegreen.sh
#!/bin/bash
set -e

CURRENT_COLOR=$(docker compose ps | grep web | grep Up | cut -d_ -f2)
NEW_COLOR=$([ "$CURRENT_COLOR" = "blue" ] && echo "green" || echo "blue")

echo "Current: $CURRENT_COLOR, Deploying: $NEW_COLOR"

# Deploy new version
docker compose -p onespirit_$NEW_COLOR up -d --build web

# Health check
for i in {1..30}; do
  if curl -f http://localhost:8001/health/ > /dev/null 2>&1; then
    echo "New version healthy!"
    break
  fi
  sleep 2
done

# Switch traffic (update nginx upstream)
# ... nginx configuration update ...

# Stop old version
docker compose -p onespirit_$CURRENT_COLOR stop web
```

### 8. **Configuration Drift Detection**
**Missing**: Tracking of production configuration changes

**Recommendation**: Version control all configuration and use tools like:
- `docker-compose config` to validate
- Configuration management (Ansible, Terraform)
- Git-based infrastructure as code

## 🎯 **Priority-Based Action Items**

### 🔴 Must Fix Before Production (Critical)
1. **Create `/health/` endpoint** - Required for health checks
2. **Add MEDIA_URL and MEDIA_ROOT** - Required for file uploads
3. **Resolve config/nginx directory** - Create or remove mount
4. **Fix database backup password** - Required for automated backups

### 🟠 Should Fix for Production Hardening (High Priority)
5. **Add Redis authentication** - Security best practice
6. **Make Gunicorn workers configurable** - Performance optimization
7. **Fix email password inconsistency** - Clarity and usability
8. **Update backup/restore password handling** - Operational reliability

### 🟡 Recommended Improvements (Medium Priority)
9. **Remove collectstatic from Dockerfile** - Build reliability
10. **Implement log rotation** - Prevent disk exhaustion
11. **Add Docker Compose version check** - Compatibility
12. **Implement backup retention policy** - Disk management
13. **Improve secret file permissions** - Security hardening
14. **Optimize PostgreSQL configuration** - Performance

### 🟢 Nice to Have (Low Priority)
15. **Add Sentry integration** - Error tracking
16. **Implement database connection pooling** - Performance
17. **Create nginx config examples** - Documentation
18. **Add health check monitoring** - Observability
19. **Automated backup scheduling** - Operational excellence
20. **Backup verification testing** - DR preparedness

## 📊 **Overall Assessment**

### Score: **8.5/10** ⭐

Your production setup is **very well designed** and demonstrates excellent understanding of:
- Container security best practices
- Secrets management
- Service orchestration
- Operational tooling
- Infrastructure as code

### Strengths
1. **Security**: Docker secrets, non-root users, HSTS, SSL automation
2. **Reliability**: Health checks, restart policies, resource limits
3. **Operations**: Comprehensive management scripts, backup/restore
4. **Documentation**: Good inline comments and clear structure
5. **Modern Stack**: Latest PostgreSQL, Redis, Python, using `uv` for deps

### Key Gaps
1. **Missing health endpoint** (critical but 5-minute fix)
2. **Media configuration** (critical but 2-minute fix)
3. **Redis authentication** (important security hardening)
4. **Some operational polish** (log rotation, automated backups, monitoring)

### Production Readiness
**Status**: Nearly production-ready ✅

With the 4 critical issues addressed (estimated 30 minutes of work), this setup would be:
- ✅ Secure for production use
- ✅ Reliable with health checks and restart policies
- ✅ Maintainable with excellent tooling
- ✅ Scalable with proper resource management

The high and medium priority items are enhancements that can be added iteratively post-launch.

## 📚 **References & Best Practices Applied**

1. **Django Deployment Checklist**: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
2. **Docker Security Best Practices**: https://docs.docker.com/develop/security-best-practices/
3. **Docker Compose Production**: https://docs.docker.com/compose/production/
4. **Gunicorn Production**: https://docs.gunicorn.org/en/stable/deploy.html
5. **PostgreSQL Security**: https://www.postgresql.org/docs/current/auth-password.html
6. **Nginx Reverse Proxy**: https://github.com/nginx-proxy/nginx-proxy
7. **Let's Encrypt Docker**: https://github.com/nginx-proxy/acme-companion

## 🔄 **Next Steps**

1. **Immediate**: Fix the 4 critical issues
2. **Week 1**: Implement high-priority security improvements (Redis auth)
3. **Week 2**: Add operational tooling (log rotation, backup automation)
4. **Month 1**: Implement monitoring and alerting
5. **Ongoing**: Regular security updates and dependency management

## 📝 **Audit Metadata**

- **Date**: November 20, 2025
- **Auditor**: GitHub Copilot
- **Scope**: Production deployment configuration
- **Branch**: joel-soo/005-dev-script-refactor
- **Files Reviewed**:
  - setup-prod.sh (303 lines)
  - Dockerfile.prod (75 lines)
  - docker-compose.prod.yaml (251 lines)
  - manage-secrets.sh (402 lines)
  - .env.prod.example (47 lines)
  - onespirit_project/settings/prod.py (161 lines)
  - .dockerignore (203 lines)
  - .gitignore (50+ lines)

---

**Conclusion**: Excellent work! This is a well-architected production setup that follows industry best practices. With minor fixes to the critical issues, this will be a robust, secure, and maintainable production deployment. 🚀
